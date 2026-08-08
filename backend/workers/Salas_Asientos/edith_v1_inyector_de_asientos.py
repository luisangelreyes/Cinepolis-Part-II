"""
========

=====================================================================
EDITH V1: EXTRACTOR AUTOMATIZADO DE BUTACAS (Proyecto Vision v3.4)
=============================================================================
Flujo en dos fases:
  FASE 1 (Playwright): Abre el navegador, evade Cloudflare y extrae
                       automáticamente la llave dinámica 'x-apikey'.
  FASE 2 (API): Lee 'cartelera_veracruz_completa.csv' (Generado por Matilde V4),
                filtra las salas únicas y extrae el mapa físico consultando 
                el endpoint /v1/ticket/graphql.

Genera:
  • catalogo_asientos_fisicos.csv
  • asientos_vision_inserts.sql (INSERTs listos para ASIENTO_PLANTILLA)
=============================================================================
"""

import pandas as pd
from curl_cffi import requests as cffi_requests
import time
import random
import csv
import os
from datetime import datetime

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
CSV_ENTRADA  = "cartelera_veracruz_completa.csv"
CSV_SALIDA   = "catalogo_asientos_fisicos.csv"
SQL_SALIDA   = "asientos_vision_inserts.sql"

API_URL = "https://api-g.cinepolis.com/v1/ticket/graphql"

PAUSA_MIN    = 1.5   
PAUSA_MAX    = 3.5   
MAX_INTENTOS = 4     

# ─── QUERY GRAPHQL ────────────────────────────────────────────────────────────
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
    "standard":     "Tradicional",
    "Standard":     "Tradicional",
    "vip":          "VIP",
    "VIP":          "VIP",
    "imax":         "IMAX",
    "IMAX":         "IMAX",
    "macroxe":      "MACRO XE",
    "macroXE":      "MACRO XE",
    "wheelchair":   "Silla de ruedas",
    "Wheelchair":   "Silla de ruedas",
    "special":      "Especial",
    "Special":      "Especial",
    "companion":    "Especial",
}

def mapear_tipo(tipo_api: str) -> str:
    return TIPO_ASIENTO_MAP.get(tipo_api, "Tradicional")

# ─── FASE 1: OBTENER LLAVE DINÁMICA ───────────────────────────────────────────
def obtener_llave_dinamica() -> str:
    from playwright.sync_api import sync_playwright
    
    print("═" * 65)
    print("  FASE 1: Obteniendo credenciales de acceso (EDITH / Playwright)")
    print("═" * 65)
    
    llave_secreta = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/146.0.0.0 Safari/537.36"
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
            time.sleep(3) # Tiempo extra para asegurar la intercepción
        except Exception as e:
            print(f"  [WARN] Timeout en Playwright, pero revisaremos si capturó la llave.")
            
        browser.close()

    if llave_secreta:
        print(f"  [ÉXITO] Llave dinámica obtenida: {llave_secreta[:10]}...\n")
    else:
        print("  [ERROR] No se pudo obtener la llave x-apikey.\n")
        
    return llave_secreta

# ─── FASE 2: EXTRACCIÓN DE SALAS ──────────────────────────────────────────────
def consultar_asientos(session_id: str, cinema_vista_id: str, experiencia: str, api_key: str) -> list:
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "country-id": "MX",
        "origin": "https://cinepolis.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/146.0.0.0 Safari/537.36",
        "x-apikey": api_key,
    }

    payload = {
        "operationName": "Seats",
        "variables": {
            "countryId":    "MX",
            "sessionId":    session_id,
            "cinemaVistaId":cinema_vista_id,
            "experience":   experiencia,
        },
        "query": QUERY_SEATS,
    }

    for intento in range(1, MAX_INTENTOS + 1):
        try:
            response = cffi_requests.post(API_URL, json=payload, headers=headers, impersonate="chrome110", timeout=15)
        except Exception as e:
            print(f"    ❌ Excepción de red (intento {intento}): {e}")
            time.sleep(5 * intento)
            continue

        if response.status_code == 200:
            data = response.json()
            if data.get("errors") or data.get("data") is None:
                print(f"    ⚠️ Error interno GraphQL: {data.get('errors')}")
                return []
                
            return data.get("data", {}).get("seats", {}).get("seatLayoutData", {}).get("areas", [])

        elif response.status_code == 429:
            espera = 10 * intento
            print(f"    ⏳ Rate limit (429). Esperando {espera}s... (intento {intento})")
            time.sleep(espera)
        else:
            print(f"    ❌ HTTP {response.status_code}")
            return []

    return []

def parsear_areas(areas: list, complejo_slug: str, sala_numero: str) -> list:
    butacas = []
    for area in areas:
        tipo_area = area.get("description") or area.get("areaCategoryCode") or ""
        
        for fila_datos in area.get("rows", []):
            letra_fila = fila_datos.get("physicalName", "")
            for asiento in fila_datos.get("seats", []):
                id_silla   = asiento.get("id", "")
                
                # Ignorar pasillos o espacios vacíos que no tienen ID de butaca
                if not id_silla: continue 
                
                tipo_raw   = asiento.get("seatStyle", tipo_area) 
                pos        = asiento.get("position", {})
                col_idx    = pos.get("columnIndex")
                
                # Proteger contra índices 0 que rompan el DDL CHECK (columna > 0)
                if not col_idx or int(col_idx) <= 0: col_idx = 1

                butacas.append({
                    "complejo_slug":  complejo_slug,
                    "sala_numero":    sala_numero,
                    "fila":           letra_fila,
                    "columna":        col_idx,
                    "id_silla_api":   id_silla,        
                    "tipo_asiento":   mapear_tipo(tipo_raw)
                })
    return butacas

# ─── EXPORTACIÓN ──────────────────────────────────────────────────────────────
def guardar_sql(butacas: list, ruta: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "-- ============================================================",
        "-- INSERTS ASIENTO_PLANTILLA — Proyecto Vision v3.4",
        f"-- Generado por EDITH V1: {ts}",
        "-- ============================================================\n",
    ]

    for b in butacas:
        slug     = b["complejo_slug"].replace("'", "''")
        sala_num = str(b["sala_numero"]).replace("'", "''")
        fila     = b["fila"].replace("'", "''")
        col      = b["columna"]
        tipo     = b["tipo_asiento"].replace("'", "''")
        api_id   = b["id_silla_api"].replace("'", "''")

        # Inserción con subquery y protección WHERE NOT EXISTS (Estándar Vision)
        lines.append(f"""
INSERT INTO ASIENTO_PLANTILLA (asiento_api_id, sala_id, fila, columna, tipo_asiento)
SELECT '{api_id}', s.sala_id, '{fila}', {col}, '{tipo}'
FROM SALA s
JOIN COMPLEJO c ON s.complejo_id = c.complejo_id
WHERE c.slug = '{slug}' AND s.numero_sala = {sala_num}
AND NOT EXISTS (
    SELECT 1 FROM ASIENTO_PLANTILLA ap2 
    WHERE ap2.sala_id = s.sala_id AND ap2.fila = '{fila}' AND ap2.columna = {col}
);
""")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip())

def guardar_csv(butacas: list, ruta: str):
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=butacas[0].keys())
        writer.writeheader()
        writer.writerows(butacas)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "═" * 65)
    print("  EDITH V1: MAPEO ARQUITECTÓNICO DE SALAS")
    print("═" * 65 + "\n")

    if not os.path.exists(CSV_ENTRADA):
        print(f"[ERROR] No se encontró '{CSV_ENTRADA}'.")
        print("  Debes correr 'matilde_vision_injector.py' primero para obtener las funciones.")
        return

    df = pd.read_csv(CSV_ENTRADA)

    # FASE 1: Obtener llave
    api_key = obtener_llave_dinamica()
    if not api_key:
        return

    # FASE 2: Mapear salas
    print("═" * 65)
    print("  FASE 2: Escaneando cuadrículas físicas de las salas")
    print("═" * 65)

    # Extraer las salas únicas basándonos en la extracción de Matilde V4 (FIX: 'numero_sala')
    salas_unicas = df.drop_duplicates(subset=["complejo_slug", "numero_sala"]).copy().reset_index(drop=True)
    total = len(salas_unicas)
    
    todas_las_butacas = []
    
    for i, row in salas_unicas.iterrows():
        slug        = row["complejo_slug"]
        nombre      = row["complejo_nombre"]
        sala_numero = str(row["numero_sala"]) # FIX: Apunta a 'numero_sala'
        session_id  = str(row["session_id"])
        vista_id    = str(row["cinema_vista_id"])
        
        # FIX: En Matilde V4 la columna se llama 'experiencia'
        experiencia = str(row.get("experiencia", "Tradicional"))

        print(f"  [{i+1:>3}/{total}] {nombre} — Sala {sala_numero}")
        areas = consultar_asientos(session_id, vista_id, experiencia, api_key)

        if areas:
            butacas = parsear_areas(areas, slug, sala_numero)
            todas_las_butacas.extend(butacas)
            print(f"    ✓ {len(butacas)} butacas extraídas")
        else:
            print(f"    ⚠ Sin datos para esta sala")

        time.sleep(random.uniform(PAUSA_MIN, PAUSA_MAX))

    # Guardar resultados
    if todas_las_butacas:
        guardar_csv(todas_las_butacas, CSV_SALIDA)
        guardar_sql(todas_las_butacas, SQL_SALIDA)
        print("\n" + "═" * 65)
        print(f"  [ÉXITO] Misión Cumplida.")
        print(f"  Se mapearon {len(todas_las_butacas)} butacas físicas en total.")
        print(f"  • {SQL_SALIDA} generado correctamente.")
        print("═" * 65)

if __name__ == "__main__":
    main()