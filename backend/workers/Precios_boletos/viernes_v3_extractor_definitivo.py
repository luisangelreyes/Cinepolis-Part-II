"""
=============================================================================
Viernes V3.0 — EXTRACTOR DE PRECIOS DEFINITIVO
=============================================================================
Combina:
 1. Lectura local del JSON de cartelera (para obtener session_ids reales)
 2. Playwright (solo para robar el x-apikey fresco)
 3. Ingeniería Inversa API Cinépolis (Manejo de Centavos y Costos Ocultos 3D)
=============================================================================
"""

import time
import random
import csv
import json
import argparse
import logging
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

# ─────────────────────────────────────────────────────────────────────────────
# CORRECCIÓN #1 y #3: Overrides hardcoded, NO se infieren del JSON.
# Ajusta estos sets con los complejo_id reales que correspondan en tu Vision.
# ─────────────────────────────────────────────────────────────────────────────
COMPLEJOS_VIP = {4, 7, 10}          # VIP El Dorado Veracruz, VIP Las Américas Veracruz, VIP Las Américas Xalapa
COMPLEJOS_CON_MACRO_XE = set()      # TODO: llenar con los complejo_id que realmente tienen salas MACRO XE (validar contra tabla SALA)

# TICKETTYPE_MAP eliminado para extracción dinámica

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
        logging.FileHandler(OUTPUT_DIR / "friday_v3.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: EXTRAER SESIONES DEL JSON LOCAL
# ─────────────────────────────────────────────────────────────────────────────
def cargar_sesiones_desde_json() -> dict:
    """Extrae un session_id por cada combinación de vista_id + formato + experiencia."""
    archivo_json = "cartelera_veracruz_completa.json"
    if not Path(archivo_json).exists():
        log.error(f"❌ No se encontró el archivo {archivo_json}. Viernes. lo necesita.")
        return {}

    try:
        with open(archivo_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log.error(f"Error leyendo JSON: {e}")
        return {}

    muestras = {}
    for fun in data.get("funciones", []):
        vid = fun.get("cinema_vista_id")
        sid = fun.get("session_id")
        fmt = fun.get("formato", "2D")
        exp = fun.get("experiencia", "Tradicional")
        
        if vid and sid:
            clave = (vid, fmt, exp)
            if clave not in muestras:
                muestras[clave] = sid
                
    log.info(f"✓ {len(muestras)} sesiones extraídas del JSON local.")
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
    """Extrae (formato_id, tipo_sala) analizando los nombres y descriptions.

    CORRECCIÓN #1: el tipo_sala para complejos VIP se fuerza por complejo_id,
    sin depender de que el JSON local etiquete bien 'experiencia'. Esto evita
    que un VIP quede guardado como 'Tradicional' silenciosamente.
    CORRECCIÓN #3: 'MACRO XE' solo se acepta si el complejo está en la
    whitelist COMPLEJOS_CON_MACRO_XE; si no, se degrada a lo que corresponda
    (evita insertar tarifas MACRO XE en complejos que no tienen esas salas).
    """
    desc = ticket.get("description", "").upper()
    
    # Formato
    if "IMAX" in desc: formato_id = 13 if "3D" in desc else 5
    elif "3D" in desc: formato_id = 12
    else: formato_id = FORMATO_MAP.get(fallback_fmt.lower(), 11)

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
            if "IMAX" in fallback_exp.upper(): tipo_sala = "IMAX"
            elif "4D" in fallback_exp.upper(): tipo_sala = "4DX"
            elif "JUNIOR" in fallback_exp.upper(): tipo_sala = "Junior"
            else: tipo_sala = "Tradicional"
    elif "IMAX" in fallback_exp.upper(): tipo_sala = "IMAX"
    elif "4D" in fallback_exp.upper(): tipo_sala = "4DX"
    elif "JUNIOR" in fallback_exp.upper(): tipo_sala = "Junior"
    else: tipo_sala = "Tradicional"

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
            time.sleep((2 ** retry) * 3)
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
# MAIN
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

def main():
    log.info("Iniciando Viernes V3...")
    
    mapa_sesiones = cargar_sesiones_desde_json()
    if not mapa_sesiones: return

    api_key = capturar_apikey_playwright()
    http = cffi_requests.Session(impersonate="chrome120")

    engine = create_engine('postgresql://postgres:1234@localhost:5432/secret_wars')
    
    with engine.begin() as conn:
        res = conn.execute(text("SELECT tipo_boleto_id, nombre FROM TIPO_BOLETO")).fetchall()
        mapa_boletos = {row.nombre.lower().strip(): row.tipo_boleto_id for row in res}
        
        todos_registros = []
        vistos = set()

        for complejo_id, vista_id, nombre in COMPLEJO_VISTA_IDS:
            log.info(f"━━ [{complejo_id:02d}] {nombre} (vista_id={vista_id})")
            
            # Filtramos las sesiones que pertenecen a este cine
            sesiones_cine = {k: v for k, v in mapa_sesiones.items() if k[0] == vista_id}
            
            if not sesiones_cine:
                log.warning("  ! Sin sesiones en JSON para este complejo.")
                continue

            for (vid, fmt, exp), session_id in sesiones_cine.items():
                time.sleep(random.uniform(1.5, 3.0))
                areas_tickets = obtener_precios(http, api_key, vista_id, session_id)

                if not areas_tickets:
                    log.warning(f"  ! [FALTANTE] Respuesta vacía para complejo_id={complejo_id}, fmt={fmt}, exp={exp} "
                                f"(posible apikey expirada o bloqueo — revisar antes de dar la corrida por completa).")

                for area in areas_tickets:
                    for t in area.get("tickets", []):
                        # Ignorar paquetes extraños y 2x1 (usamos catálogo fijo para 2x1)
                        if t.get("isPackageTicket") or t.get("type") != "general": continue
                        
                        description = t.get("description", "")
                        if not description: continue
                        
                        tipo_boleto_id = obtener_tipo_boleto_id(conn, description, mapa_boletos)
                        
                        formato_id, tipo_sala = parsear_tipo_desde_api(t, exp, fmt, complejo_id)
                        
                        # MAGIA FINANCIERA: Cálculo real en centavos + cargos ocultos
                        precio_base = t.get("priceInCents", 0) / 100.0
                        cargo_srv   = t.get("bookingFee", 0) / 100.0
                        
                        # Sumar la renta obligatoria de Lentes 3D si existe
                        concesiones = t.get("packageContent", {}).get("concessions", [])
                        for extra in concesiones:
                            precio_base += extra.get("charge", 0) / 100.0

                        clave = (complejo_id, formato_id, tipo_boleto_id, tipo_sala)
                        if clave in vistos: continue
                        vistos.add(clave)

                        todos_registros.append({
                            "complejo_id": complejo_id,
                            "formato_id": formato_id,
                            "tipo_boleto_id": tipo_boleto_id,
                            "tipo_sala": tipo_sala,
                            "precio": precio_base,
                            "cargo": cargo_srv,
                        })
                        
                        log.info(f"  + {tipo_sala:11s} | Fmt: {formato_id} | Bol: {tipo_boleto_id} | ${precio_base:.2f} (+${cargo_srv:.2f} serv)")

    # EXPORTAR SQL
    if todos_registros:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        sql_path = OUTPUT_DIR / f"precios_vision_{ts}.sql"

        lineas = [
            "BEGIN;\n",
            "-- CORRECCIÓN #2: limpiar fallbacks obsoletos antes de insertar datos reales.",
            "TRUNCATE TABLE PRECIO_BOLETO RESTART IDENTITY;\n",
        ]
        for r in todos_registros:
            lineas.append(
                f"INSERT INTO PRECIO_BOLETO (complejo_id, formato_id, tipo_boleto_id, tipo_sala, precio, cargo_servicio_online) "
                f"VALUES ({r['complejo_id']}, {r['formato_id']}, {r['tipo_boleto_id']}, '{r['tipo_sala']}', {r['precio']:.2f}, {r['cargo']:.2f}) "
                f"ON CONFLICT ON CONSTRAINT uq_precio_boleto DO UPDATE SET precio=EXCLUDED.precio, cargo_servicio_online=EXCLUDED.cargo_servicio_online;"
            )
        lineas.append("\nCOMMIT;")
        
        sql_path.write_text("\n".join(lineas), encoding="utf-8")
        log.info(f"\n✅ Extracción completa. Se generaron {len(todos_registros)} tarifas en: {sql_path}")

        # Resumen de cobertura: cuántos complejos esperados aparecieron realmente
        complejos_con_datos = {r["complejo_id"] for r in todos_registros}
        complejos_esperados = {c[0] for c in COMPLEJO_VISTA_IDS}
        faltantes = sorted(complejos_esperados - complejos_con_datos)
        log.info(f"📊 Cobertura: {len(complejos_con_datos)}/{len(complejos_esperados)} complejos con al menos una tarifa.")
        if faltantes:
            log.warning(f"⚠️  Complejos SIN ninguna tarifa extraída: {faltantes} — revisar antes de considerar la corrida completa.")
    else:
        log.error("❌ No se generó ningún registro. Revisa el JSON local, la apikey y la conectividad antes de reintentar.")

if __name__ == "__main__":
    main()