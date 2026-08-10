"""
=============================================================================
Viernes V2.3 — EXTRACTOR DE PRECIOS DE BOLETO (Cinépolis)
=============================================================================
Fix vs V2.2:
  - COMPLEJO_VISTA_IDS reconstruido desde Vision (era incorrecto en V2.x)
  - COMPLEJO_SLUGS con prefijo "cinepolis-" correcto
  - TIPOS_SALA_POR_COMPLEJO: whitelist desde Vision (157 salas reales)
  - VIP override: complejo_ids 2, 4, 10 → tipo_sala="VIP" siempre
  - areaCategoryCode "0000000001" en VIP ya NO se mapea como Tradicional
=============================================================================
"""

import time, random, csv, json, argparse, logging
from datetime import datetime
from pathlib import Path

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("pip install curl_cffi playwright")
    exit(1)

# ─── CONFIG — reconstruido 100% desde Vision v3.4 ────────────────────────────

URL_TICKET = "https://api-g.cinepolis.com/v1/ticket/graphql"
URL_SEATS  = "https://api-g.cinepolis.com/v1/billboards/graphql"
API_KEY_BACKUP = "lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo"

# Fuente: SELECT complejo_id, vista_id, slug FROM complejo ORDER BY complejo_id
COMPLEJO_VISTA_IDS = [
    ( 1, "611",  "La Florida Acayucan"),
    ( 2, "545",  "VIP El Dorado Veracruz"),
    ( 3, "126",  "Las Américas Veracruz"),
    ( 4, "192",  "VIP Las Américas Veracruz"),
    ( 5, "635",  "El Dorado Coatzacoalcos"),
    ( 6, "658",  "Acaya Coatzacoalcos"),
    ( 7, "443",  "Plaza Shangri-La"),
    ( 8, "125",  "Plaza Museo Xalapa"),
    ( 9, "040",  "Plaza Crystal Xalapa"),
    (10, "665",  "VIP Las Américas Xalapa"),
    (11, "247",  "Plaza Las Américas Xalapa"),
    (12, "573",  "Chedraui Martínez de la Torre"),
    (13, "139",  "Plaza Minatitlán"),
    (14, "388",  "Plaza Valle Orizaba"),
    (15, "609",  "Río Blanco Orizaba"),
    (16, "298",  "Plaza Crystal Tuxpan"),
    (17, "1103", "Portal Veracruz"),
    (18, "260",  "Plaza del Puerto Veracruz"),
    (19, "484",  "El Dorado Veracruz"),
]

# Fuente: slug de la tabla complejo en Vision v3.4
COMPLEJO_SLUGS = {
    1:  "cinepolis-la-florida-acayucan",
    2:  "cinepolis-vip-el-dorado-veracruz",
    3:  "cinepolis-las-americas-veracruz",
    4:  "cinepolis-vip-las-americas-veracruz",
    5:  "cinepolis-el-dorado-coatzacoalcos",
    6:  "cinepolis-acaya-coatzacoalcos",
    7:  "cinepolis-plaza-shangri-la-cordoba",
    8:  "cinepolis-plaza-museo-xalapa",
    9:  "cinepolis-plaza-crystal-xalapa",
    10: "cinepolis-vip-las-americas-xalapa",
    11: "cinepolis-plaza-las-americas-xalapa",
    12: "cinepolis-chedraui-martinez-de-la-torre",
    13: "cinepolis-plaza-minatitlan",
    14: "cinepolis-plaza-valle-orizaba",
    15: "cinepolis-rio-blanco-orizaba",
    16: "cinepolis-plaza-crystal-tuxpan",
    17: "cinepolis-portal-veracruz",
    18: "cinepolis-plaza-del-puerto-veracruz",
    19: "cinepolis-el-dorado-veracruz",
}

# Whitelist: tipos de sala reales por complejo
# Fuente: SELECT complejo_id, STRING_AGG(DISTINCT tipo_sala) FROM sala GROUP BY complejo_id
TIPOS_SALA_POR_COMPLEJO = {
    1:  {"Tradicional"},
    2:  {"VIP"},
    3:  {"Tradicional", "IMAX"},
    4:  {"VIP"},
    5:  {"Tradicional"},
    6:  {"Tradicional", "MACRO XE"},
    7:  {"Tradicional"},
    8:  {"Tradicional"},
    9:  {"Tradicional"},
    10: {"VIP"},
    11: {"Tradicional", "MACRO XE", "Junior", "4DX"},
    12: {"Tradicional"},
    13: {"Tradicional"},
    14: {"Tradicional", "MACRO XE"},
    15: {"Tradicional"},
    16: {"Tradicional"},
    17: {"Tradicional"},
    18: {"Tradicional"},
    19: {"Tradicional", "MACRO XE"},
}

# Complejos VIP: areaCategoryCode siempre mapea a "VIP" sin importar el código
VIP_COMPLEJO_IDS = {2, 4, 10}

# ticketTypeCode confirmados desde DevTools (sesión Acaya 2D y 3D)
TICKETTYPE_MAP = {
    "0001": 1,  # Admisión General (2D y VIP — mismo código)
    "0002": 2,  # Niños 2D
    "0003": 3,  # Tercera Edad / INAPAM 2D
    "0004": 4,  # Estudiante 2D
    "0005": 1,  # Admisión General 3D
    "0006": 2,  # Niños 3D
    "0007": 3,  # Tercera Edad 3D
    "0008": 4,  # Estudiante 3D
}

# Fallback por description si ticketTypeCode no está en el mapa
DESCRIPTION_MAP = {
    "general": 1, "adulto": 1,
    "niño": 2,    "nino": 2,
    "tercera": 3, "inapam": 3,
    "estudiante": 4,
}

AREA_FALLBACK = {
    "0000000001": "Tradicional",
    "0000000002": "MACRO XE",
    "0000000003": "VIP",
    "0000000004": "IMAX",
    "0000000005": "4DX",
    "0000000006": "Junior",
}

NOMBRE_A_TIPO_SALA = {
    "tradicional": "Tradicional", "standard": "Tradicional",
    "macro xe": "MACRO XE",       "macroxe": "MACRO XE", "xe": "MACRO XE",
    "imax": "IMAX",               "vip": "VIP",
    "junior": "Junior",           "4dx": "4DX",
}

DELAY_MIN, DELAY_MAX, MAX_RETRIES = 2.0, 4.5, 4

OUTPUT_DIR = Path("output_precios")
OUTPUT_DIR.mkdir(exist_ok=True)
DUMP_DIR = OUTPUT_DIR / "dumps"
DUMP_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / "friday_v2_3.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)


# ─── PLAYWRIGHT ───────────────────────────────────────────────────────────────

def capturar_con_playwright(complejo_id, vista_id, slug, dump):
    from playwright.sync_api import sync_playwright
    import json
    
    api_key = API_KEY_BACKUP
    sessions_propias = []

    # 1. Extraer la x-apikey al vuelo con Playwright
    def on_request(req):
        nonlocal api_key
        if "graphql" in req.url:
            for h in ("x-apikey", "x-api-key"):
                if h in req.headers:
                    api_key = req.headers[h]
                    break

    url = f"https://www.cinepolis.com/cartelera/{slug}"
    log.info(f"  Playwright → Capturando API Key en {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ))
        page = ctx.new_page()
        page.on("request", on_request)
        try:
            # Solo esperamos a que cargue el HTML base, no necesitamos el networkidle
            page.goto(url, wait_until="commit", timeout=15_000)
            page.wait_for_timeout(2_000) # 2 segundos para cazar el token
        except Exception as e:
            log.warning(f"  Playwright timeout (ignorado): {e}")
        finally:
            browser.close()

    # 2. Extraer los sessionIds válidos de tu archivo JSON (Matilde)
    try:
        with open("cartelera_veracruz_completa.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            
        vistas_encontradas = set()
        for fun in data.get("funciones", []):
            # Adaptamos para soportar distintos nombres de llaves en tu JSON
            cine_id = str(fun.get("cinema_vista_id", fun.get("cinemaId", "")))
            
            if cine_id == vista_id:
                exp = str(fun.get("experience", "2D")).upper() 
                sid = str(fun.get("session_id", fun.get("sessionId", "")))
                
                # Solo necesitamos 1 sesión por cada tipo de formato (2D, 3D, IMAX)
                if sid and exp not in vistas_encontradas:
                    vistas_encontradas.add(exp)
                    sessions_propias.append({
                        "sessionId": sid,
                        "experience": exp,
                        "cinemaId": vista_id
                    })
    except FileNotFoundError:
        log.error("  ! No se encontró 'cartelera_veracruz_completa.json' en la carpeta.")
    except Exception as e:
        log.error(f"  ! Error leyendo JSON: {e}")

    log.info(f"  API key: {api_key[:15]}...")
    log.info(f"  Sessions locales: {len(sessions_propias)} "
             f"({[s['experience'] for s in sessions_propias]})")
    
    return api_key, sessions_propias


# ─── SEATS ────────────────────────────────────────────────────────────────────

QUERY_SEATS = """
query Seats($countryId: String!, $sessionId: String!,
            $cinemaVistaId: String!, $experience: String) {
  seats(countryId: $countryId, sessionId: $sessionId,
        cinemaVistaId: $cinemaVistaId, experience: $experience) {
    seatLayoutData {
      areaCategories { areaCategoryCode name }
    }
  }
}
"""

def construir_mapa_areas(http, api_key, vista_id, session_id,
                          experience, complejo_id, dump):
    payload = {"query": QUERY_SEATS, "variables": {
        "countryId": "MX", "cinemaVistaId": vista_id,
        "sessionId": session_id, "experience": experience or "",
    }}
    headers = {"x-apikey": api_key, "Content-Type": "application/json",
               "Origin": "https://www.cinepolis.com",
               "Referer": "https://www.cinepolis.com/"}
    mapa = {}
    try:
        resp = http.post(URL_SEATS, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            raw   = resp.json()
            areas = (raw.get("data", {}).get("seats", {})
                        .get("seatLayoutData", {})
                        .get("areaCategories", []))
            for area in areas:
                code = area.get("areaCategoryCode", "")
                name = (area.get("name") or "").strip().lower()
                tipo = next((v for k, v in NOMBRE_A_TIPO_SALA.items()
                             if k in name), None)
                if code and tipo:
                    mapa[code] = tipo
                    log.info(f"    Area: {code} → {tipo} ({area.get('name')})")
            if dump:
                dp = DUMP_DIR / f"seats_c{complejo_id}_s{session_id}.json"
                dp.write_text(json.dumps(raw, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    except Exception as e:
        log.warning(f"  Error Seats: {e}")

    if not mapa:
        log.warning("  Usando mapa de áreas fallback.")
        mapa = dict(AREA_FALLBACK)
    return mapa


# ─── TICKET ───────────────────────────────────────────────────────────────────

QUERY_TICKET = """
query Tickets($countryId: String!, $sessionId: String!, $cinemaVistaId: String!) {
  tickets(countryId: $countryId, cinemaVistaId: $cinemaVistaId, sessionId: $sessionId) {
    areaCategoryCode
    tickets {
      id ticketTypeCode description
      priceInCents bookingFee type isPackageTicket
    }
  }
}
"""

def detectar_formato(description: str) -> int:
    d = description.upper()
    if "IMAX" in d: return 13
    if "3D"   in d: return 12
    return 11

def tipo_boleto_desde_description(description: str):
    d = description.lower()
    for k, v in DESCRIPTION_MAP.items():
        if k in d:
            return v
    return None

def obtener_precios(http, api_key, vista_id, session_id,
                    complejo_id, dump, retry=0):
    payload = {"query": QUERY_TICKET, "variables": {
        "countryId": "MX", "cinemaVistaId": vista_id, "sessionId": session_id,
    }}
    headers = {"x-apikey": api_key, "Content-Type": "application/json",
               "Origin": "https://www.cinepolis.com",
               "Referer": "https://www.cinepolis.com/"}
    try:
        resp = http.post(URL_TICKET, json=payload, headers=headers, timeout=15)

        if resp.status_code == 429:
            wait = (2 ** retry) * 5 + random.uniform(1, 3)
            log.warning(f"  429 → {wait:.1f}s (intento {retry+1})")
            time.sleep(wait)
            if retry < MAX_RETRIES:
                return obtener_precios(http, api_key, vista_id, session_id,
                                       complejo_id, dump, retry + 1)
            return []

        if resp.status_code != 200:
            log.error(f"  HTTP {resp.status_code} Ticket session={session_id}")
            return []

        raw = resp.json()
        if dump:
            dp = DUMP_DIR / f"tickets_c{complejo_id}_s{session_id}.json"
            dp.write_text(json.dumps(raw, ensure_ascii=False, indent=2),
                          encoding="utf-8")
            log.info(f"  DUMP Tickets → {dp}")

        areas = raw.get("data", {}).get("tickets", []) or []
        resultados = []
        for area in areas:
            area_code = area.get("areaCategoryCode", "")
            for t in area.get("tickets", []):
                log.info(
                    f"    RAW: code={t.get('ticketTypeCode')} "
                    f"type={t.get('type')} pkg={t.get('isPackageTicket')} "
                    f"'{t.get('description')}' "
                    f"price={t.get('priceInCents')} fee={t.get('bookingFee')}"
                )
                if t.get("type") != "general": continue
                if t.get("isPackageTicket"):   continue
                resultados.append({
                    "areaCategoryCode": area_code,
                    "ticketTypeCode":   t.get("ticketTypeCode", ""),
                    "description":      t.get("description", ""),
                    "precio":           round(t.get("priceInCents", 0) / 100, 2),
                    "cargo":            round(t.get("bookingFee",   0) / 100, 2),
                })
        return resultados

    except Exception as e:
        log.error(f"  Error Ticket: {e}")
        return []


# ─── EXPORTAR ─────────────────────────────────────────────────────────────────

def exportar_sql(registros, path):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "-- ============================================================",
        f"-- PRECIO_BOLETO — Viernes V2.3 | Vision v3.4 | {ts}",
        f"-- Total registros únicos: {len(registros)}",
        "-- Whitelist de tipos de sala validada contra Vision (157 salas reales)",
        "-- ============================================================",
        "", "BEGIN;", "", "TRUNCATE PRECIO_BOLETO RESTART IDENTITY;", "",
        "INSERT INTO PRECIO_BOLETO",
        "  (complejo_id, formato_id, tipo_boleto_id, tipo_sala,",
        "   precio, cargo_servicio_online)",
        "VALUES",
    ]
    filas = [
        f"  ({r['complejo_id']}, {r['formato_id']}, {r['tipo_boleto_id']}, "
        f"'{r['tipo_sala']}', {r['precio']:.2f}, {r['cargo_servicio_online']:.2f})"
        for r in registros
    ]
    lines.append(",\n".join(filas))
    lines += [
        "ON CONFLICT ON CONSTRAINT uq_precio_boleto DO UPDATE SET",
        "  precio                = EXCLUDED.precio,",
        "  cargo_servicio_online = EXCLUDED.cargo_servicio_online;",
        "", "DO $$ BEGIN",
        "  RAISE NOTICE 'PRECIO_BOLETO: % registros totales',",
        "    (SELECT COUNT(*) FROM PRECIO_BOLETO);",
        "END; $$;", "", "COMMIT;",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"SQL → {path} ({len(registros)} registros)")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Viernes V2.3")
    parser.add_argument("--complejo", type=int, default=None)
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--dump",     action="store_true",
                        help="Guarda JSON crudo en output_precios/dumps/")
    args = parser.parse_args()

    http   = cffi_requests.Session(impersonate="chrome120")
    todos  = []
    vistos = set()

    complejos = COMPLEJO_VISTA_IDS
    if args.complejo:
        complejos = [c for c in COMPLEJO_VISTA_IDS if c[0] == args.complejo]
        if not complejos:
            log.error(f"complejo_id {args.complejo} no encontrado.")
            return

    for complejo_id, vista_id, nombre in complejos:
        log.info(f"━━ [{complejo_id:02d}] {nombre} (vista_id={vista_id})")
        slug        = COMPLEJO_SLUGS[complejo_id]
        tipos_validos = TIPOS_SALA_POR_COMPLEJO.get(complejo_id, {"Tradicional"})
        es_vip      = complejo_id in VIP_COMPLEJO_IDS

        api_key, sessions = capturar_con_playwright(
            complejo_id, vista_id, slug, args.dump
        )

        if not sessions:
            log.warning("  Sin sessions — omitido.")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        for s in sessions:
            session_id = s["sessionId"]
            experience = s["experience"]
            cine_id    = s["cinemaId"]
            log.info(f"  → session={session_id} exp='{experience or '2D'}' "
                     f"cine={cine_id}")

            mapa_areas = construir_mapa_areas(
                http, api_key, cine_id, session_id,
                experience, complejo_id, args.dump
            )
            time.sleep(random.uniform(0.5, 1.2))

            tickets = obtener_precios(
                http, api_key, cine_id, session_id, complejo_id, args.dump
            )
            log.info(f"  Tickets base filtrados: {len(tickets)}")

            for t in tickets:
                # Determinar tipo_sala
                if es_vip:
                    tipo_sala = "VIP"  # override: VIP siempre es VIP
                else:
                    tipo_sala = mapa_areas.get(
                        t["areaCategoryCode"],
                        AREA_FALLBACK.get(t["areaCategoryCode"], "Tradicional")
                    )

                # Validar contra whitelist de Vision
                if tipo_sala not in tipos_validos:
                    log.debug(f"  '{tipo_sala}' no existe en complejo {complejo_id} "
                              f"(válidos: {tipos_validos}) — omitido")
                    continue

                # Mapear tipo de boleto
                tipo_boleto_id = TICKETTYPE_MAP.get(t["ticketTypeCode"])
                if tipo_boleto_id is None:
                    tipo_boleto_id = tipo_boleto_desde_description(t["description"])
                    if tipo_boleto_id:
                        log.warning(f"  code '{t['ticketTypeCode']}' desconocido → "
                                    f"mapeado por description → boleto_id={tipo_boleto_id}. "
                                    f"Agregar a TICKETTYPE_MAP.")
                    else:
                        log.warning(f"  Sin mapeo para code='{t['ticketTypeCode']}' "
                                    f"'{t['description']}' — agregar a TICKETTYPE_MAP")
                        continue

                formato_id = detectar_formato(t["description"])

                clave = (complejo_id, formato_id, tipo_boleto_id, tipo_sala)
                if clave in vistos:
                    continue
                vistos.add(clave)

                registro = {
                    "complejo_id":           complejo_id,
                    "formato_id":            formato_id,
                    "tipo_boleto_id":        tipo_boleto_id,
                    "tipo_sala":             tipo_sala,
                    "precio":                t["precio"],
                    "cargo_servicio_online": t["cargo"],
                }
                todos.append(registro)
                log.info(
                    f"    ✓ {tipo_sala:12s} | fmt={formato_id} | "
                    f"boleto={tipo_boleto_id} | ${t['precio']:.2f}+${t['cargo']:.2f}"
                )

            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        time.sleep(random.uniform(1.0, 2.0))

    log.info(f"\n{'='*55}")
    log.info(f"Total registros únicos: {len(todos)}")
    log.info(f"Complejos procesados:   "
             f"{len(set(r['complejo_id'] for r in todos))}/19")
    log.info(f"{'='*55}")

    if args.dry_run or not todos:
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    exportar_sql(todos, OUTPUT_DIR / f"precio_boleto_{ts}.sql")


if __name__ == "__main__":
    main()