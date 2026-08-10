"""
=============================================================================
EDITH V2: EXTRACTOR AUTOMATIZADO DE BUTACAS (Proyecto Vision — Matilde V7)
=============================================================================

Cambios vs V1:
  - Lee el JSON unificado 'cartelera_veracruz_completa.json' generado por
    Matilde V7 (en lugar del CSV antiguo).
  - Reutiliza la x-apikey hardcodeada de Matilde V7 como primer intento,
    evitando la necesidad de lanzar Playwright en la mayoria de los casos.
  - Playwright solo se activa como FALLBACK si la llave estatica falla
    (HTTP 401/403).
  - Deduplica salas directamente desde el JSON (por complejo_slug + numero_sala).
  - Mantiene la logica de reintentos, rate-limit y parseo de butacas intacta.

Genera:
  * catalogo_asientos_fisicos.csv
  * asientos_vision_inserts.sql  (INSERTs listos para ASIENTO_PLANTILLA)

Uso:
  python edith_v2_inyector_de_asientos.py
=============================================================================
"""

import json
import csv
import os
import time
import random
import sys
from datetime import datetime

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("Faltan dependencias. Ejecuta: pip install curl_cffi")
    sys.exit(1)

# Forzar UTF-8 en consola Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ===========================================================================
# CONFIGURACION
# ===========================================================================

# El JSON esta en la raiz del proyecto (3 niveles arriba de este script)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR   = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", ".."))

JSON_ENTRADA = os.path.join(_ROOT_DIR, "cartelera_veracruz_completa.json")
CSV_SALIDA   = os.path.join(_SCRIPT_DIR, "catalogo_asientos_fisicos.csv")
SQL_SALIDA   = os.path.join(_SCRIPT_DIR, "asientos_vision_inserts.sql")

API_URL = "https://api-g.cinepolis.com/v1/ticket/graphql"

# Llave estatica reutilizada de Matilde V7
# Si caduca, Playwright la renueva automaticamente
APIKEY_ESTATICA = "lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo"

PAUSA_MIN    = 1.5
PAUSA_MAX    = 3.5
MAX_INTENTOS = 4

IMPERSONATE_OPTIONS = ["chrome110", "chrome116", "chrome120", "safari15_5", "edge101"]

# ===========================================================================
# QUERY GRAPHQL
# ===========================================================================

QUERY_SEATS = """
query Seats($countryId: String!, $sessionId: String!, $cinemaVistaId: String!, $experience: String) {
  seats(
    countryId: $countryId
    sessionId: $sessionId
    cinemaVistaId: $cinemaVistaId
    experience: $experience
  ) {
    seatLayoutData {
      areas {
        areaCategoryCode
        description
        rows {
          physicalName
          seats {
            id
            seatStyle
            position {
              columnIndex
              rowIndex
            }
          }
        }
      }
    }
  }
}
"""

TIPO_ASIENTO_MAP = {
    "standard":   "Tradicional",
    "Standard":   "Tradicional",
    "vip":        "VIP",
    "VIP":        "VIP",
    "imax":       "IMAX",
    "IMAX":       "IMAX",
    "macroxe":    "MACRO XE",
    "macroXE":    "MACRO XE",
    "wheelchair": "Silla de ruedas",
    "Wheelchair": "Silla de ruedas",
    "special":    "Especial",
    "Special":    "Especial",
    "companion":  "Especial",
}


def mapear_tipo(tipo_api: str) -> str:
    return TIPO_ASIENTO_MAP.get(tipo_api, "Tradicional")


# ===========================================================================
# FASE 0: CARGAR DATOS DEL JSON DE MATILDE V7
# ===========================================================================

def cargar_salas_desde_json(ruta: str) -> list:
    """
    Lee cartelera_veracruz_completa.json (Matilde V7) y devuelve
    una lista de salas unicas deduplicadas por (complejo_slug, numero_sala).
    Cada sala tiene: complejo_slug, complejo_nombre, sala_numero,
                     session_id, cinema_vista_id, experiencia.
    """
    print(f"  Leyendo JSON: {ruta}")
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)

    funciones = data.get("funciones", [])
    print(f"  Total funciones en JSON: {len(funciones)}")

    vistas = {}  # (complejo_slug, numero_sala) -> dict con la primera sesion encontrada

    for fn in funciones:
        slug        = fn.get("complejo_slug", "").strip()
        sala_num    = str(fn.get("numero_sala", "")).strip()
        session_id  = str(fn.get("session_id", "")).strip()
        vista_id    = str(fn.get("cinema_vista_id", "")).strip()
        experiencia = str(fn.get("experiencia", "Tradicional")).strip()

        if not slug or not sala_num or not session_id or not vista_id:
            continue

        clave = (slug, sala_num)
        if clave not in vistas:
            nombre_legible = slug.replace("cinepolis-", "").replace("-", " ").title()
            vistas[clave] = {
                "complejo_slug":   slug,
                "complejo_nombre": nombre_legible,
                "sala_numero":     sala_num,
                "session_id":      session_id,
                "cinema_vista_id": vista_id,
                "experiencia":     experiencia,
            }

    salas = list(vistas.values())
    print(f"  Salas unicas identificadas: {len(salas)}")
    return salas


# ===========================================================================
# FASE 1: FALLBACK — OBTENER LLAVE DINAMICA VIA PLAYWRIGHT
# ===========================================================================

def obtener_llave_dinamica() -> str:
    """
    Lanza Playwright para capturar la x-apikey desde el trafico de cinepolis.com.
    Se invoca SOLO cuando la llave estatica devuelve HTTP 401/403.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [WARN] Playwright no esta instalado.")
        print("         Ejecuta: pip install playwright && playwright install chromium")
        return None

    print("\n" + "=" * 65)
    print("  FALLBACK PLAYWRIGHT: Renovando llave dinamica...")
    print("=" * 65)

    llave_secreta = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        def on_request(request):
            nonlocal llave_secreta
            if "graphql" in request.url:
                key = request.headers.get("x-apikey")
                if key and not llave_secreta:
                    llave_secreta = key

        page.on("request", on_request)

        try:
            print("  Navegando a cinepolis.com para evadir Cloudflare...")
            page.goto("https://cinepolis.com", wait_until="networkidle", timeout=30000)
            time.sleep(4)
        except Exception:
            print("  [WARN] Timeout en Playwright, revisando si se capturo llave...")

        browser.close()

    if llave_secreta:
        print(f"  [EXITO] Llave capturada: {llave_secreta[:10]}...\n")
    else:
        print("  [ERROR] No se pudo capturar la x-apikey.\n")

    return llave_secreta


# ===========================================================================
# FASE 2: EXTRACCION DE BUTACAS VIA API
# ===========================================================================

def _hacer_headers(api_key: str) -> dict:
    return {
        "accept": "*/*",
        "content-type": "application/json",
        "country-id": "MX",
        "origin": "https://cinepolis.com",
        "referer": "https://cinepolis.com/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        ),
        "x-apikey": api_key,
    }


def consultar_asientos(session_id: str, cinema_vista_id: str, experiencia: str, api_key: str):
    """
    Consulta el endpoint /v1/ticket/graphql con reintentos y manejo de rate-limit.
    Retorna:
      - list: lista de areas (puede ser lista vacia si no hay datos)
      - "LLAVE_INVALIDA": si se recibe HTTP 401 o 403
    """
    payload = {
        "operationName": "Seats",
        "variables": {
            "countryId":     "MX",
            "sessionId":     session_id,
            "cinemaVistaId": cinema_vista_id,
            "experience":    experiencia,
        },
        "query": QUERY_SEATS,
    }
    headers = _hacer_headers(api_key)
    imp     = random.choice(IMPERSONATE_OPTIONS)

    for intento in range(1, MAX_INTENTOS + 1):
        try:
            response = cffi_requests.post(
                API_URL, json=payload, headers=headers,
                impersonate=imp, timeout=15
            )
        except Exception as e:
            print(f"    [x] Error de red (intento {intento}): {e}")
            time.sleep(5 * intento)
            continue

        if response.status_code == 200:
            data = response.json()
            if data.get("errors") or data.get("data") is None:
                print(f"    [!] Error GraphQL: {data.get('errors')}")
                return []
            seats_data      = (data.get("data") or {}).get("seats") or {}
            layout_data     = seats_data.get("seatLayoutData") or {}
            areas           = layout_data.get("areas") or []
            return areas

        elif response.status_code in (401, 403):
            print(f"    [LLAVE] HTTP {response.status_code}: Llave invalida o expirada.")
            return "LLAVE_INVALIDA"

        elif response.status_code == 429:
            espera = 10 * intento
            print(f"    [429] Rate limit. Esperando {espera}s... (intento {intento})")
            time.sleep(espera)

        else:
            print(f"    [x] HTTP {response.status_code}")
            return []

    return []


def parsear_areas(areas: list, complejo_slug: str, sala_numero: str) -> list:
    """Convierte la respuesta de la API en una lista de butacas normalizadas."""
    butacas = []

    for area in areas:
        tipo_area = area.get("description") or area.get("areaCategoryCode") or ""

        for fila_datos in area.get("rows", []):
            letra_fila = fila_datos.get("physicalName", "")

            for asiento in fila_datos.get("seats", []):
                id_silla = asiento.get("id", "")

                # Ignorar pasillos/espacios vacios sin ID de butaca
                if not id_silla:
                    continue

                tipo_raw = asiento.get("seatStyle", tipo_area)
                pos      = asiento.get("position", {})
                col_idx  = pos.get("columnIndex")
                
                # La API devuelve columnIndex empezando en 0. 
                # Sumamos 1 a TODAS para pasarlo a base 1 y evitar colisiones
                # en la base de datos (que tiene restricción columna > 0).
                col_idx = int(col_idx) + 1 if col_idx is not None else 1

                butacas.append({
                    "complejo_slug": complejo_slug,
                    "sala_numero":   sala_numero,
                    "fila":          letra_fila,
                    "columna":       col_idx,
                    "id_silla_api":  id_silla,
                    "tipo_asiento":  mapear_tipo(tipo_raw),
                })

    return butacas


# ===========================================================================
# EXPORTACION
# ===========================================================================

def guardar_sql(butacas: list, ruta: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "-- ============================================================",
        "-- INSERTS ASIENTO_PLANTILLA -- Proyecto Vision (EDITH V2)",
        f"-- Generado: {ts}",
        "-- ============================================================\n",
        "BEGIN;\n",
    ]

    for b in butacas:
        slug     = b["complejo_slug"].replace("'", "''")
        sala_num = str(b["sala_numero"]).replace("'", "''")
        fila     = b["fila"].replace("'", "''")
        col      = b["columna"]
        tipo     = b["tipo_asiento"].replace("'", "''")
        api_id   = b["id_silla_api"].replace("'", "''")

        lines.append(
            f"INSERT INTO ASIENTO_PLANTILLA (asiento_api_id, sala_id, fila, columna, tipo_asiento)\n"
            f"SELECT '{api_id}', s.sala_id, '{fila}', {col}, '{tipo}'\n"
            f"FROM SALA s\n"
            f"JOIN COMPLEJO c ON s.complejo_id = c.complejo_id\n"
            f"WHERE c.slug = '{slug}' AND s.numero_sala = {sala_num}\n"
            f"  AND NOT EXISTS (\n"
            f"    SELECT 1 FROM ASIENTO_PLANTILLA ap2\n"
            f"    WHERE ap2.sala_id = s.sala_id\n"
            f"      AND ap2.fila = '{fila}'\n"
            f"      AND ap2.columna = {col}\n"
            f"  );\n"
        )

    lines.append("COMMIT;")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  SQL guardado: {ruta}")


def guardar_csv(butacas: list, ruta: str):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=butacas[0].keys())
        writer.writeheader()
        writer.writerows(butacas)

    print(f"  CSV guardado: {ruta}")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print("\n" + "=" * 65)
    print("  EDITH V2: MAPEO ARQUITECTONICO DE BUTACAS")
    print("  Fuente: cartelera_veracruz_completa.json (Matilde V7)")
    print("=" * 65 + "\n")

    # 0. Verificar JSON de entrada
    if not os.path.exists(JSON_ENTRADA):
        print(f"[ERROR] No se encontro el JSON de entrada:\n  {JSON_ENTRADA}")
        print("  Corre primero matilde_v6_worker_playwright.py para generarlo.")
        return

    # 0. Cargar salas unicas
    salas = cargar_salas_desde_json(JSON_ENTRADA)
    if not salas:
        print("[ERROR] No se encontraron salas validas en el JSON.")
        return

    # 1. Validar llave de acceso
    print("\n" + "=" * 65)
    print("  FASE 1: Validando llave de acceso (estatica de Matilde V7)...")
    print("=" * 65)

    api_key     = APIKEY_ESTATICA
    sala_prueba = salas[0]
    resultado   = consultar_asientos(
        sala_prueba["session_id"],
        sala_prueba["cinema_vista_id"],
        sala_prueba["experiencia"],
        api_key
    )

    if resultado == "LLAVE_INVALIDA":
        print("  Llave estatica expirada. Activando fallback Playwright...")
        api_key = obtener_llave_dinamica()
        if not api_key:
            print("[ERROR FATAL] Sin llave valida. Abortando.")
            return
    else:
        print(f"  [OK] Llave estatica valida: {api_key[:10]}...")

    # 2. Escanear todas las salas
    print("\n" + "=" * 65)
    print(f"  FASE 2: Escaneando {len(salas)} salas unicas")
    print("=" * 65)

    todas_las_butacas      = []
    salas_sin_datos        = []
    llave_renovada         = False

    for i, sala in enumerate(salas, 1):
        slug        = sala["complejo_slug"]
        nombre      = sala["complejo_nombre"]
        sala_numero = sala["sala_numero"]
        session_id  = sala["session_id"]
        vista_id    = sala["cinema_vista_id"]
        experiencia = sala["experiencia"]

        print(f"  [{i:>3}/{len(salas)}] {nombre} - Sala {sala_numero}  (session={session_id})")

        areas = consultar_asientos(session_id, vista_id, experiencia, api_key)

        # Renovacion de llave a mitad del proceso (una sola vez)
        if areas == "LLAVE_INVALIDA" and not llave_renovada:
            print("  Llave expiro durante el escaneo. Renovando via Playwright...")
            nueva_llave  = obtener_llave_dinamica()
            llave_renovada = True
            if nueva_llave:
                api_key = nueva_llave
                areas   = consultar_asientos(session_id, vista_id, experiencia, api_key)
            else:
                print("  [ERROR] No se pudo renovar la llave. Saltando sala.")
                salas_sin_datos.append(f"{nombre} - Sala {sala_numero}")
                continue
        elif areas == "LLAVE_INVALIDA":
            print("  [ERROR] Llave sigue invalida tras renovacion. Saltando.")
            salas_sin_datos.append(f"{nombre} - Sala {sala_numero}")
            continue

        if areas:
            butacas = parsear_areas(areas, slug, sala_numero)
            todas_las_butacas.extend(butacas)
            print(f"    [+] {len(butacas)} butacas")
        else:
            print(f"    [!] Sin datos para esta sala")
            salas_sin_datos.append(f"{nombre} - Sala {sala_numero}")

        time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))

    # 3. Exportar
    print("\n" + "=" * 65)

    if todas_las_butacas:
        guardar_csv(todas_las_butacas, CSV_SALIDA)
        guardar_sql(todas_las_butacas, SQL_SALIDA)
        salas_ok = len(salas) - len(salas_sin_datos)
        print(f"\n  [EXITO] {len(todas_las_butacas)} butacas mapeadas en {salas_ok}/{len(salas)} salas.")
    else:
        print("  [ERROR] No se mapeo ninguna butaca.")

    if salas_sin_datos:
        print(f"\n  Salas sin datos ({len(salas_sin_datos)}):")
        for s in salas_sin_datos:
            print(f"    - {s}")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
