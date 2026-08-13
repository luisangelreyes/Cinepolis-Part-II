"""
=============================================================================
Viernes V4.1 — EXTRACTOR DE PRECIOS (PRECIOS UNIFORMES)
=============================================================================
Los precios de Cinépolis Veracruz NO varían por horario ni día de semana,
por lo que no hay que preocuparse por matinées ni descuentos.

 V4.1: Toma UNA sola sesión representativa por combinación (cine, formato,
       experiencia). Si no hay sesiones futuras disponibles (ej. película
       que solo tiene funciones próximas a comenzar), se hace un segundo
       intento tomando cualquier sesión del JSON sin restricción de tiempo.

Combina:
 1. Lectura local del JSON de cartelera (para obtener session_ids reales)
 2. Playwright (solo para robar el x-apikey fresco)
 3. Ingeniería Inversa API Cinépolis (Manejo de Centavos y Costos Ocultos 3D)
============================================================================="""

import time
import random
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import create_engine, text

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("Faltan dependencias. Ejecuta: pip install curl_cffi playwright")
    exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────
URL_TICKET = "https://api-g.cinepolis.com/v1/ticket/graphql"
API_KEY_BACKUP = "lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo"

# UNA sola sesión por combinación es suficiente (precios uniformes en la zona).
MAX_MUESTRAS = 1

# MAPEO CORRECTO: slug (BD) → cinema_vista_id (API Cinépolis) → nombre
# Usamos slugs para consultar el complejo_id dinámicamente desde la BD.
COMPLEJO_VISTA_SLUGS = [
    ("cinepolis-la-florida-acayucan", "611",  "La Florida Acayucan"),
    ("cinepolis-vip-el-dorado-veracruz", "545",  "VIP El Dorado Veracruz"),
    ("cinepolis-las-americas-veracruz", "126",  "Las Américas Veracruz"),
    ("cinepolis-vip-las-americas-veracruz", "192",  "VIP Las Américas Veracruz"),
    ("cinepolis-el-dorado-coatzacoalcos", "635",  "El Dorado Coatzacoalcos"),
    ("cinepolis-acaya-coatzacoalcos", "658",  "Acaya Coatzacoalcos"),
    ("cinepolis-plaza-shangri-la-cordoba", "443",  "Plaza Shangri-La Córdoba"),
    ("cinepolis-plaza-museo-xalapa", "125",  "Plaza Museo Xalapa"),
    ("cinepolis-plaza-crystal-xalapa", "040",  "Plaza Crystal Xalapa"),
    ("cinepolis-vip-las-americas-xalapa", "665",  "VIP Las Américas Xalapa"),
    ("cinepolis-plaza-las-americas-xalapa", "247",  "Plaza Las Américas Xalapa"),
    ("cinepolis-chedraui-martinez-de-la-torre", "573",  "Chedraui Martínez de la Torre"),
    ("cinepolis-plaza-minatitlan", "139",  "Plaza Minatitlán"),
    ("cinepolis-plaza-valle-orizaba", "388",  "Plaza Valle Orizaba"),
    ("cinepolis-rio-blanco-orizaba", "609",  "Río Blanco Orizaba"),
    ("cinepolis-plaza-crystal-tuxpan", "298",  "Plaza Crystal Tuxpan"),
    ("cinepolis-portal-veracruz", "1103", "Portal Veracruz"),
    ("cinepolis-plaza-del-puerto-veracruz", "260",  "Plaza del Puerto Veracruz"),
    ("cinepolis-el-dorado-veracruz", "484",  "El Dorado Veracruz"),
]

# Overrides hardcoded — basados en vista_id (que no cambia)
COMPLEJOS_VIP = {"545", "192", "665"}
COMPLEJOS_CON_MACRO_XE = {"126", "658", "247", "388"}

# Experiencias del JSON de Cinépolis que deben ignorarse por ser eventos únicos
# (no tienen tarifa estándar en la cartelera regular)
EXPERIENCIAS_IGNORAR = {"SP"}  # SP = Sala Privada / Evento Especial

FORMATO_MAP = {
    "2d":       11,
    "3d":       12,
    "imax":     5,
    "imax 3d":  13,
}

OUTPUT_DIR = Path("output_precios")
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / "friday_v4.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: EXTRAER MÚLTIPLES SESIONES DEL JSON LOCAL
# ─────────────────────────────────────────────────────────────────────────────
def cargar_sesiones_desde_json() -> dict:
    """Extrae hasta MAX_MUESTRAS session_ids por cada combinación de
    (vista_id, formato, experiencia) para poder consultar múltiples precios
    y quedarse con el máximo (precio real de taquilla).
    
    V3 tomaba solo la primera sesión → podía ser Matinée/descuento.
    V4 toma N sesiones → el precio máximo es el precio regular.
    """
    archivo_json = "cartelera_veracruz_completa.json"
    if not Path(archivo_json).exists():
        log.error(f"❌ No se encontró el archivo {archivo_json}. Viernes V4 lo necesita.")
        return {}

    try:
        with open(archivo_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log.error(f"Error leyendo JSON: {e}")
        return {}

    ahora = datetime.now()
    sesiones_totales = 0
    sesiones_descartadas = 0

    funciones_raw = data.get("funciones", [])

    # Primera pasada: solo sesiones que aún no han comenzado
    # muestras: {(vista_id, fmt, exp): [session_id, ...]}
    muestras: dict[tuple, list[str]] = {}
    # Guardamos todas las funciones por clave como fallback
    todas_funciones: dict[tuple, list[str]] = {}

    for fun in funciones_raw:
        vid = fun.get("cinema_vista_id")
        sid = fun.get("session_id")
        fmt = fun.get("formato", "2D")
        exp = fun.get("experiencia", "Tradicional")
        dt_str = fun.get("datetime", "")

        if not (vid and sid):
            continue

        sesiones_totales += 1
        # Clave ahora incluye tipo_sala del JSON de cartelera para evitar el bug
        # de complejos VIP con salas mixtas (Tradicional + VIP en mismo complejo).
        tipo_sala_json = fun.get("tipo_sala", "")  # campo del JSON de Matilde
        clave = (vid, fmt, exp, tipo_sala_json)

        # Fallback: guardar TODAS las sesiones sin restricción de tiempo
        todas_funciones.setdefault(clave, [])
        if sid not in todas_funciones[clave] and len(todas_funciones[clave]) < MAX_MUESTRAS:
            todas_funciones[clave].append(sid)

        # Primera pasada: solo sesiones futuras (no empezadas todavía)
        if dt_str:
            try:
                dt_fun = datetime.fromisoformat(dt_str.replace("Z", ""))
                if dt_fun < ahora:
                    sesiones_descartadas += 1
                    continue  # Sesión ya empezó → ignorar en primera pasada
            except ValueError:
                pass  # Fecha mal formateada → incluir de todas formas

        lista = muestras.setdefault(clave, [])
        if sid not in lista and len(lista) < MAX_MUESTRAS:
            lista.append(sid)

    # Segunda pasada (fallback): para combinaciones sin sesiones futuras,
    # usar la primera sesión disponible sin restricción de tiempo.
    # Esto sucede cuando el script corre tarde y las funciones de hoy ya empezaron.
    sin_sesiones_futuras = 0
    for clave, todas in todas_funciones.items():
        if clave not in muestras or not muestras[clave]:
            if todas:
                muestras[clave] = [todas[0]]  # Tomar la primera disponible
                sin_sesiones_futuras += 1
                log.debug(f"  ↩ Fallback para {clave}: usando sesión próxima {todas[0]}")

    total_validas = sum(len(v) for v in muestras.values())
    log.info(
        f"✓ {len(muestras)} combinaciones únicas | {total_validas} sesiones "
        f"de {sesiones_totales} totales ({sesiones_descartadas} ya iniciadas descartadas, "
        f"{sin_sesiones_futuras} usaron fallback de sesión próxima)."
    )

    if not muestras:
        log.error(
            "NINGUNA sesion futura en el JSON. "
            "El JSON de cartelera esta desactualizado. "
            "Ejecuta Matilde V6 primero para regenerarlo con funciones futuras."
        )

    return muestras


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2: ROBAR LA API KEY CON PLAYWRIGHT
# ─────────────────────────────────────────────────────────────────────────────
def capturar_apikey_playwright() -> str:
    from playwright.sync_api import sync_playwright
    api_key = API_KEY_BACKUP

    def on_request(request):
        nonlocal api_key
        if "graphql" in request.url:
            for h in ("x-apikey", "x-api-key"):
                if h in request.headers:
                    api_key = request.headers[h]

    log.info("Abriendo Playwright para capturar x-apikey fresca...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
            page = ctx.new_page()
            page.on("request", on_request)
            page.goto("https://www.cinepolis.com", timeout=30000)
            page.wait_for_timeout(3000)
            browser.close()
    except Exception as e:
        log.warning(f"Error Playwright: {e}")

    log.info(f"✓ API Key obtenida: {api_key[:15]}...")
    return api_key

# ─────────────────────────────────────────────────────────────────────────────
# PASO 3: CONSULTAR PRECIOS A LA API DE CINÉPOLIS
# ─────────────────────────────────────────────────────────────────────────────
QUERY_TICKETS = """
query Tickets($countryId: String!, $sessionId: String!, $cinemaVistaId: String!) {
  tickets(countryId: $countryId, cinemaVistaId: $cinemaVistaId, sessionId: $sessionId) {
    areaCategoryCode
    tickets {
      id
      ticketTypeCode
      description
      priceInCents
      bookingFee
      type
      isPackageTicket
      packageContent {
        concessions { charge displayName }
      }
    }
  }
}
"""

def parsear_tipo_desde_api(ticket: dict, fallback_exp: str, fallback_fmt: str, vista_id: str, tipo_sala_bd: str = "") -> tuple[int, str]:
    """Extrae (formato_id, tipo_sala) analizando los nombres y descriptions.

    Si se proporciona `tipo_sala_bd` (leído del JSON de cartelera que ya tiene el
    tipo de sala correcto de la BD), se usa directamente para tipo_sala en lugar
    de intentar inferirlo desde el vista_id o la experiencia.

    Mapeo de experiencias del JSON de Cinépolis:
      'Tradicional' → Tradicional
      'XE'          → MACRO XE  (solo en complejos de la whitelist)
      '4DX'         → 4DX
      'SJ'          → Junior    (Sala Junior — código interno de Cinépolis)
      'IMAX'        → IMAX
      'SP'          → ignorar   (Sala Privada / Evento Especial — sin tarifa estándar)
    """
    desc = ticket.get("description", "").upper()

    # Formato — se detecta por la descripción del boleto que devuelve la API
    if "IMAX" in desc:   formato_id = 13 if "3D" in desc else 5
    elif "3D" in desc:   formato_id = 12
    else:                formato_id = FORMATO_MAP.get(fallback_fmt.lower(), 11)

    # Si el JSON de cartelera ya tiene el tipo_sala correcto, usarlo directamente.
    # Esto evita el bug donde complejos VIP con salas mixtas se clasificaban mal.
    if tipo_sala_bd:
        return formato_id, tipo_sala_bd

    # Fallback: inferir tipo_sala desde vista_id y experiencia (comportamiento legacy)
    exp_upper = fallback_exp.upper()
    if "VIP" in exp_upper or "VIP" in desc:
        tipo_sala = "VIP"
    elif exp_upper in ("XE", "MACRO XE") or "MACRO" in exp_upper:
        if vista_id in COMPLEJOS_CON_MACRO_XE:
            tipo_sala = "MACRO XE"
        else:
            log.warning(
                f"  ! Complejo {vista_id} reporto experiencia XE/MACRO XE pero no esta "
                f"en COMPLEJOS_CON_MACRO_XE — degradando a Tradicional."
            )
            tipo_sala = "Tradicional"
    elif exp_upper == "4DX" or "4D" in exp_upper:   tipo_sala = "4DX"
    elif exp_upper == "SJ" or "JUNIOR" in exp_upper: tipo_sala = "Junior"
    elif "IMAX" in exp_upper:                        tipo_sala = "IMAX"
    elif vista_id in COMPLEJOS_VIP:                  tipo_sala = "VIP"  # Fallback final para cines 100% VIP
    else:                                            tipo_sala = "Tradicional"

    return formato_id, tipo_sala

def obtener_precios(http, api_key: str, vista_id: str, session_id: str, retry: int = 0) -> list[dict]:
    payload = {
        "query": QUERY_TICKETS,
        "variables": {"countryId": "MX", "cinemaVistaId": vista_id, "sessionId": session_id}
    }
    headers = {"x-apikey": api_key, "Content-Type": "application/json", "Origin": "https://www.cinepolis.com"}

    try:
        resp = http.post(URL_TICKET, json=payload, headers=headers, timeout=15)
        if resp.status_code == 429:
            wait = (2 ** retry) * 3
            log.warning(f"    Rate-limited (429). Esperando {wait}s...")
            time.sleep(wait)
            if retry < 3: return obtener_precios(http, api_key, vista_id, session_id, retry+1)
            return []

        if resp.status_code != 200: return []

        data = resp.json()
        if data.get("errors") or data.get("data") is None:
            log.warning(f"  [!] Error GraphQL: {data.get('errors')}")
            return []

        return (data.get("data") or {}).get("tickets") or []
    except Exception as e:
        log.error(f"Error HTTP en session {session_id}: {e}")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def obtener_tipo_boleto_id(conn, description: str, mapa_boletos: dict) -> int:
    """Busca el ID del tipo de boleto en el mapa, o lo inserta si es nuevo."""
    nombre = description.strip()
    key = nombre.lower()

    if key in mapa_boletos:
        return mapa_boletos[key]

    log.info(f"  [+] Nuevo tipo de boleto detectado: '{nombre}'. Registrando...")
    query = text("""
        INSERT INTO TIPO_BOLETO (nombre, descripcion, es_promocional, precio_fijo)
        VALUES (:nombre, :nombre, true, null)
        ON CONFLICT ON CONSTRAINT uq_tipo_boleto_nombre DO UPDATE SET nombre=EXCLUDED.nombre
        RETURNING tipo_boleto_id;
    """)
    nuevo_id = conn.execute(query, {"nombre": nombre}).scalar()

    if nuevo_id is None:
        query_sel = text("SELECT tipo_boleto_id FROM TIPO_BOLETO WHERE nombre = :nombre")
        nuevo_id = conn.execute(query_sel, {"nombre": nombre}).scalar()

    mapa_boletos[key] = nuevo_id
    return nuevo_id

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    log.info("Iniciando Viernes V4 — Muestreo Múltiple para Precio Correcto...")
    log.info(f"Configuración: MAX_MUESTRAS={MAX_MUESTRAS} sesiones por combinación.")

    mapa_sesiones = cargar_sesiones_desde_json()
    if not mapa_sesiones: return

    api_key = capturar_apikey_playwright()
    http = cffi_requests.Session(impersonate="chrome120")

    engine = create_engine('postgresql://postgres:1234@localhost:5432/secret_wars')

    with engine.begin() as conn:
        res = conn.execute(text("SELECT tipo_boleto_id, nombre FROM TIPO_BOLETO")).fetchall()
        mapa_boletos = {row.nombre.lower().strip(): row.tipo_boleto_id for row in res}

        # Estructura para acumular precios:
        # precios_acumulados[(complejo_id, formato_id, tipo_boleto_id, tipo_sala, area_code)] = {
        #     "precios": [precio1, precio2, ...],
        #     "cargo": cargo_srv,
        #     "descripcion": "Admisión General 3D",
        #     "area_category_code": "0000000001"
        # }
        precios_acumulados: dict[tuple, dict] = {}

        # Mapear los slugs a los IDs reales de la BD
        slug_to_id = {}
        res_complejos = conn.execute(text("SELECT slug, complejo_id FROM COMPLEJO")).fetchall()
        for c in res_complejos:
            slug_to_id[c.slug] = c.complejo_id

        for slug, vista_id, nombre_cine in COMPLEJO_VISTA_SLUGS:
            complejo_id = slug_to_id.get(slug)
            if not complejo_id:
                log.warning(f"  ! Complejo '{slug}' no encontrado en BD. Omitiendo.")
                continue

            log.info(f"━━ [{complejo_id:02d}] {nombre_cine} (vista_id={vista_id})")

            # Filtrar sesiones que pertenecen a este cine, excluyendo experiencias ignoradas (SP, etc.)
            sesiones_cine = {
                k: v for k, v in mapa_sesiones.items()
                if k[0] == vista_id and k[2].upper() not in EXPERIENCIAS_IGNORAR
            }

            if not sesiones_cine:
                log.warning("  ! Sin sesiones en JSON para este complejo.")
                continue

            for (vid, fmt, exp, tipo_sala_json), lista_sessions in sesiones_cine.items():
                log.info(f"  · Combinacion ({fmt}/{exp}/{tipo_sala_json or 'desconocido'}): {len(lista_sessions)} sesiones.")

                for session_id in lista_sessions:
                    time.sleep(random.uniform(1.2, 2.5))
                    areas_tickets = obtener_precios(http, api_key, vista_id, session_id)

                    if not areas_tickets:
                        log.warning(f"    ! Respuesta vacía para session={session_id} (posible bloqueo o sesión expirada).")
                        continue

                    for area in areas_tickets:
                        area_code = area.get("areaCategoryCode") or ""  # ← capturar código de área

                        for t in area.get("tickets", []):
                            # Ignorar paquetes extraños y 2x1
                            if t.get("isPackageTicket") or t.get("type") != "general":
                                continue

                            description = t.get("description", "")
                            if not description:
                                continue

                            tipo_boleto_id = obtener_tipo_boleto_id(conn, description, mapa_boletos)
                            formato_id, tipo_sala = parsear_tipo_desde_api(
                                t, exp, fmt, vista_id, tipo_sala_bd=tipo_sala_json
                            )

                            precio_base = t.get("priceInCents", 0) / 100.0
                            cargo_srv   = t.get("bookingFee", 0) / 100.0

                            # Sumar la renta obligatoria de Lentes 3D si existe
                            concesiones = t.get("packageContent", {}).get("concessions", [])
                            for extra in concesiones:
                                precio_base += extra.get("charge", 0) / 100.0

                            # La clave ahora incluye area_code para distinguir
                            # asientos de distinto precio dentro de la misma sala
                            clave = (complejo_id, formato_id, tipo_boleto_id, tipo_sala, area_code)

                            if clave not in precios_acumulados:
                                precios_acumulados[clave] = {
                                    "precios": [],
                                    "cargo": cargo_srv,
                                    "descripcion": description,
                                    "area_category_code": area_code,  # ← guardar en el registro
                                }

                            precios_acumulados[clave]["precios"].append(precio_base)
                            log.info(
                                f"    → {tipo_sala:11s} | Fmt:{formato_id} | Bol:{tipo_boleto_id} | "
                                f"Area:{area_code} | ${precio_base:.2f} (sesión {session_id})"
                            )

    # ── POST-PROCESAMIENTO: usar el precio de la única muestra ──────────────────
    todos_registros = []
    for (complejo_id, formato_id, tipo_boleto_id, tipo_sala, area_code), datos in precios_acumulados.items():
        precios = datos["precios"]
        precio_final = precios[0]  # Siempre hay solo 1 muestra (MAX_MUESTRAS=1)
        precio_cargo = datos["cargo"]

        todos_registros.append({
            "complejo_id":        complejo_id,
            "formato_id":         formato_id,
            "tipo_boleto_id":     tipo_boleto_id,
            "tipo_sala":          tipo_sala,
            "area_category_code": area_code,
            "precio":             precio_final,
            "cargo":              precio_cargo,
            "n_muestras":         len(precios),
        })

    # ── EXPORTAR SQL ──────────────────────────────────────────────────────────
    if todos_registros:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        sql_path = OUTPUT_DIR / f"precios_v4_{ts}.sql"

        lineas = [
            "BEGIN;\n",
            "-- V4: Precios extraídos con muestreo múltiple (precio máximo = precio real de taquilla).",
            "-- V4.1: Incluye area_category_code para vincular precio a área física de la sala.",
            "TRUNCATE TABLE PRECIO_BOLETO RESTART IDENTITY;\n",
        ]
        for r in todos_registros:
            area_code = r.get("area_category_code") or ""
            area_sql  = f"'{area_code}'" if area_code else "NULL"
            lineas.append(
                f"INSERT INTO PRECIO_BOLETO "
                f"(complejo_id, formato_id, tipo_boleto_id, tipo_sala, area_category_code, precio, cargo_servicio_online) "
                f"VALUES ({r['complejo_id']}, {r['formato_id']}, {r['tipo_boleto_id']}, "
                f"'{r['tipo_sala']}', {area_sql}, {r['precio']:.2f}, {r['cargo']:.2f}) "
                f"ON CONFLICT ON CONSTRAINT uq_precio_boleto DO UPDATE "
                f"SET precio=EXCLUDED.precio, cargo_servicio_online=EXCLUDED.cargo_servicio_online;"
            )
        lineas.append("\nCOMMIT;")

        sql_path.write_text("\n".join(lineas), encoding="utf-8")
        log.info(f"\n✅ Extracción V4 completa. {len(todos_registros)} tarifas → {sql_path}")

        # ── Resumen de cobertura ──────────────────────────────────────────────
        complejos_con_datos  = {r["complejo_id"] for r in todos_registros}
        complejos_esperados  = set(slug_to_id.values())
        faltantes = sorted(complejos_esperados - complejos_con_datos)
        descuentos_detectados = [
            r for r in todos_registros if r["n_muestras"] > 1
        ]

        log.info(f"📊 Cobertura: {len(complejos_con_datos)}/{len(complejos_esperados)} complejos con al menos una tarifa.")
        log.info(f"🔍 Combinaciones con variación de precios detectada (posibles descuentos evitados): {len(descuentos_detectados)}")

        if faltantes:
            log.warning(f"⚠️  Complejos SIN ninguna tarifa extraída: {faltantes} — revisar antes de considerar la corrida completa.")
    else:
        log.error("❌ No se generó ningún registro. Revisa el JSON local, la apikey y la conectividad.")

if __name__ == "__main__":
    main()
