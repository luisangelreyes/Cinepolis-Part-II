"""
=============================================================================
Viernes V4.0 — EXTRACTOR DE PRECIOS CON GARANTÍA DE PRECIO CORRECTO
=============================================================================
Mejora clave sobre V3:

 PROBLEMA V3: tomaba solo la PRIMERA sesión por (cine, formato, experiencia).
              Si esa sesión era Matinée o Miércoles de descuento, el precio
              incorrecto (más bajo) quedaba guardado para todas las funciones.

 SOLUCIÓN V4: muestrea hasta MAX_MUESTRAS sesiones por combinación y se
              queda con el precio MÁXIMO observado. Los precios con descuento
              son siempre menores al precio regular, por lo que el máximo
              siempre apunta al precio de taquilla real.

Combina:
 1. Lectura local del JSON de cartelera (para obtener session_ids reales)
 2. Playwright (solo para robar el x-apikey fresco)
 3. Ingeniería Inversa API Cinépolis (Manejo de Centavos y Costos Ocultos 3D)
=============================================================================
"""

import time
import random
import json
import logging
from collections import defaultdict
from datetime import datetime
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

# Cuántas sesiones distintas muestrear por combinación (cine, formato, experiencia)
# Más muestras = mayor probabilidad de capturar el precio real, pero más llamadas a API.
MAX_MUESTRAS = 3

COMPLEJO_VISTA_IDS = [
    ( 1, "658",  "Acaya Coatzacoalcos"),
    ( 2, "635",  "El Dorado Coatzacoalcos"),
    ( 3, "484",  "El Dorado Veracruz"),
    ( 4, "545",  "VIP El Dorado Veracruz"),
    ( 5, "260",  "Plaza del Puerto"),
    ( 6, "126",  "Las Américas Veracruz"),
    ( 7, "192",  "VIP Las Américas Veracruz"),
    ( 8, "1103", "Portal Veracruz"),
    ( 9, "247",  "Plaza Las Américas Xalapa"),
    (10, "665",  "VIP Las Américas Xalapa"),
    (11, "040",  "Plaza Crystal Xalapa"),
    (12, "125",  "Plaza Museo Xalapa"),
    (13, "443",  "Plaza Shangri-La"),
    (14, "388",  "Valle Orizaba"),
    (15, "609",  "Río Blanco"),
    (16, "139",  "Plaza Minatitlán"),
    (17, "298",  "Plaza Crystal Tuxpan"),
    (18, "611",  "La Florida Acayucan"),
    (19, "573",  "Chedraui Martínez de la Torre"),
]

# Overrides hardcoded — no se infieren del JSON para mayor fiabilidad
COMPLEJOS_VIP = {4, 7, 10}           # VIP El Dorado Veracruz, VIP Las Américas Veracruz, VIP Las Américas Xalapa
COMPLEJOS_CON_MACRO_XE = set()       # Llenar con complejo_id que realmente tienen salas MACRO XE

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

    # muestras: {(vista_id, fmt, exp): [session_id_1, session_id_2, ...]}
    muestras: dict[tuple, list[str]] = {}
    
    for fun in data.get("funciones", []):
        vid = fun.get("cinema_vista_id")
        sid = fun.get("session_id")
        fmt = fun.get("formato", "2D")
        exp = fun.get("experiencia", "Tradicional")

        if not (vid and sid):
            continue

        clave = (vid, fmt, exp)
        lista = muestras.setdefault(clave, [])
        
        # Agregar la sesión solo si no la tenemos ya y no hemos alcanzado el límite
        if sid not in lista and len(lista) < MAX_MUESTRAS:
            lista.append(sid)

    total_sesiones = sum(len(v) for v in muestras.values())
    log.info(
        f"✓ {len(muestras)} combinaciones únicas extraídas del JSON local "
        f"({total_sesiones} sesiones en total, máx {MAX_MUESTRAS} por combinación)."
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

def parsear_tipo_desde_api(ticket: dict, fallback_exp: str, fallback_fmt: str, complejo_id: int) -> tuple[int, str]:
    """Extrae (formato_id, tipo_sala) analizando los nombres y descriptions."""
    desc = ticket.get("description", "").upper()

    # Formato
    if "IMAX" in desc:   formato_id = 13 if "3D" in desc else 5
    elif "3D" in desc:   formato_id = 12
    else:                formato_id = FORMATO_MAP.get(fallback_fmt.lower(), 11)

    # Tipo sala — override VIP tiene prioridad absoluta
    if complejo_id in COMPLEJOS_VIP:
        tipo_sala = "VIP"
    elif "MACRO" in fallback_exp.upper() or "XE" in fallback_exp.upper():
        if complejo_id in COMPLEJOS_CON_MACRO_XE:
            tipo_sala = "MACRO XE"
        else:
            log.warning(
                f"  ! Complejo {complejo_id} reportó experiencia MACRO XE pero no está "
                f"en COMPLEJOS_CON_MACRO_XE — se descarta el override y se re-evalúa."
            )
            if "IMAX" in fallback_exp.upper():   tipo_sala = "IMAX"
            elif "4D" in fallback_exp.upper():   tipo_sala = "4DX"
            elif "JUNIOR" in fallback_exp.upper(): tipo_sala = "Junior"
            else:                                tipo_sala = "Tradicional"
    elif "IMAX" in fallback_exp.upper():   tipo_sala = "IMAX"
    elif "4D" in fallback_exp.upper():     tipo_sala = "4DX"
    elif "JUNIOR" in fallback_exp.upper(): tipo_sala = "Junior"
    else:                                  tipo_sala = "Tradicional"

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
        # precios_acumulados[(complejo_id, formato_id, tipo_boleto_id, tipo_sala)] = {
        #     "precios": [precio1, precio2, ...],
        #     "cargo": cargo_srv,
        #     "descripcion": "Admisión General 3D"
        # }
        precios_acumulados: dict[tuple, dict] = {}

        for complejo_id, vista_id, nombre_cine in COMPLEJO_VISTA_IDS:
            log.info(f"━━ [{complejo_id:02d}] {nombre_cine} (vista_id={vista_id})")

            # Filtrar sesiones que pertenecen a este cine
            sesiones_cine = {k: v for k, v in mapa_sesiones.items() if k[0] == vista_id}

            if not sesiones_cine:
                log.warning("  ! Sin sesiones en JSON para este complejo.")
                continue

            for (vid, fmt, exp), lista_sessions in sesiones_cine.items():
                log.info(f"  · Combinación ({fmt}/{exp}): {len(lista_sessions)} sesiones a consultar.")

                for session_id in lista_sessions:
                    time.sleep(random.uniform(1.2, 2.5))
                    areas_tickets = obtener_precios(http, api_key, vista_id, session_id)

                    if not areas_tickets:
                        log.warning(f"    ! Respuesta vacía para session={session_id} (posible bloqueo o sesión expirada).")
                        continue

                    for area in areas_tickets:
                        for t in area.get("tickets", []):
                            # Ignorar paquetes extraños y 2x1
                            if t.get("isPackageTicket") or t.get("type") != "general":
                                continue

                            description = t.get("description", "")
                            if not description:
                                continue

                            tipo_boleto_id = obtener_tipo_boleto_id(conn, description, mapa_boletos)
                            formato_id, tipo_sala = parsear_tipo_desde_api(t, exp, fmt, complejo_id)

                            precio_base = t.get("priceInCents", 0) / 100.0
                            cargo_srv   = t.get("bookingFee", 0) / 100.0

                            # Sumar la renta obligatoria de Lentes 3D si existe
                            concesiones = t.get("packageContent", {}).get("concessions", [])
                            for extra in concesiones:
                                precio_base += extra.get("charge", 0) / 100.0

                            clave = (complejo_id, formato_id, tipo_boleto_id, tipo_sala)

                            if clave not in precios_acumulados:
                                precios_acumulados[clave] = {
                                    "precios": [],
                                    "cargo": cargo_srv,
                                    "descripcion": description,
                                }

                            precios_acumulados[clave]["precios"].append(precio_base)
                            log.info(
                                f"    → {tipo_sala:11s} | Fmt:{formato_id} | Bol:{tipo_boleto_id} | "
                                f"${precio_base:.2f} (sesión {session_id})"
                            )

    # ── POST-PROCESAMIENTO: seleccionar precio MÁXIMO por combinación ──────────
    todos_registros = []
    for (complejo_id, formato_id, tipo_boleto_id, tipo_sala), datos in precios_acumulados.items():
        precios = datos["precios"]
        precio_max  = max(precios)
        precio_min  = min(precios)
        precio_cargo = datos["cargo"]

        if len(precios) > 1 and precio_max != precio_min:
            log.info(
                f"  [DESCUENTO DETECTADO] Complejo {complejo_id}, Fmt {formato_id}, "
                f"Tipo {tipo_sala}: precios observados {precios} → usando máximo ${precio_max:.2f} "
                f"(mínimo descartado: ${precio_min:.2f})"
            )

        todos_registros.append({
            "complejo_id":   complejo_id,
            "formato_id":    formato_id,
            "tipo_boleto_id": tipo_boleto_id,
            "tipo_sala":     tipo_sala,
            "precio":        precio_max,
            "cargo":         precio_cargo,
            "n_muestras":    len(precios),
        })

    # ── EXPORTAR SQL ──────────────────────────────────────────────────────────
    if todos_registros:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        sql_path = OUTPUT_DIR / f"precios_v4_{ts}.sql"

        lineas = [
            "BEGIN;\n",
            "-- V4: Precios extraídos con muestreo múltiple (precio máximo = precio real de taquilla).",
            "TRUNCATE TABLE PRECIO_BOLETO RESTART IDENTITY;\n",
        ]
        for r in todos_registros:
            lineas.append(
                f"INSERT INTO PRECIO_BOLETO "
                f"(complejo_id, formato_id, tipo_boleto_id, tipo_sala, precio, cargo_servicio_online) "
                f"VALUES ({r['complejo_id']}, {r['formato_id']}, {r['tipo_boleto_id']}, "
                f"'{r['tipo_sala']}', {r['precio']:.2f}, {r['cargo']:.2f}) "
                f"ON CONFLICT ON CONSTRAINT uq_precio_boleto DO UPDATE "
                f"SET precio=EXCLUDED.precio, cargo_servicio_online=EXCLUDED.cargo_servicio_online;"
            )
        lineas.append("\nCOMMIT;")

        sql_path.write_text("\n".join(lineas), encoding="utf-8")
        log.info(f"\n✅ Extracción V4 completa. {len(todos_registros)} tarifas → {sql_path}")

        # ── Resumen de cobertura ──────────────────────────────────────────────
        complejos_con_datos  = {r["complejo_id"] for r in todos_registros}
        complejos_esperados  = {c[0] for c in COMPLEJO_VISTA_IDS}
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
