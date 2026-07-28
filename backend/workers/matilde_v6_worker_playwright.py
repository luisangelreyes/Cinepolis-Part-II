"""
=============================================================================
EXTRACTOR MATILDE — v6.0 (HÍBRIDO PLAYWRIGHT + CURL_CFFI)
=============================================================================
Mecanismos de Defensa:
  1. Fase 1: Playwright VISIBLE descubre películas y salta Cloudflare de la web.
  2. Fase 2: curl_cffi (API Directa) consulta ultrarrápido los horarios detallados
     sin depender del DOM ni timeouts de red orgánicos.
  3. DDL Dinámico: Elimina restricciones rígidas de vista_id.
=============================================================================
"""

import time
from datetime import datetime, timedelta
import json

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Faltan dependencias. Ejecuta: pip install playwright && playwright install chromium")
    exit(1)
    
try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("Faltan dependencias. Ejecuta: pip install curl_cffi")
    exit(1)

COMPLEJOS = [
    {"nombre": "La Florida Acayucan",      "slug": "cinepolis-la-florida-acayucan"},
    {"nombre": "VIP El Dorado Veracruz",   "slug": "cinepolis-vip-el-dorado-veracruz"},
    {"nombre": "Las Américas Veracruz",    "slug": "cinepolis-las-americas-veracruz"},
    {"nombre": "VIP Las Américas Veracruz","slug": "cinepolis-vip-las-americas-veracruz"},
    {"nombre": "El Dorado Coatzacoalcos",  "slug": "cinepolis-el-dorado-coatzacoalcos"},
    {"nombre": "Acaya Coatzacoalcos",      "slug": "cinepolis-acaya-coatzacoalcos"},
    {"nombre": "Plaza Shangri La Córdoba", "slug": "cinepolis-plaza-shangri-la-cordoba"},
    {"nombre": "Plaza Museo Xalapa",       "slug": "cinepolis-plaza-museo-xalapa"},
    {"nombre": "Plaza Crystal Xalapa",     "slug": "cinepolis-plaza-crystal-xalapa"},
    {"nombre": "VIP Las Américas Xalapa",  "slug": "cinepolis-vip-las-americas-xalapa"},
    {"nombre": "Plaza Las Américas Xalapa","slug": "cinepolis-plaza-las-americas-xalapa"},
    {"nombre": "Chedraui Martínez Torre",  "slug": "cinepolis-chedraui-martinez-de-la-torre"},
    {"nombre": "Plaza Minatitlán",         "slug": "cinepolis-plaza-minatitlan"},
    {"nombre": "Plaza Valle Orizaba",      "slug": "cinepolis-plaza-valle-orizaba"},
    {"nombre": "Río Blanco Orizaba",       "slug": "cinepolis-rio-blanco-orizaba"},
    {"nombre": "Plaza Crystal Tuxpan",     "slug": "cinepolis-plaza-crystal-tuxpan"},
    {"nombre": "Portal Veracruz",          "slug": "cinepolis-portal-veracruz"},
    {"nombre": "Plaza del Puerto Veracruz","slug": "cinepolis-plaza-del-puerto-veracruz"},
    {"nombre": "El Dorado Veracruz",       "slug": "cinepolis-el-dorado-veracruz"}
]

CDN_BASE_ASSETS = "https://tickets-static-content.cinepolis.com"
API_URL = "https://api-g.cinepolis.com/v1/billboards/graphql"
API_HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "country-id": "MX",
    "language": "ES",
    "origin": "https://cinepolis.com",
    "referer": "https://cinepolis.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "x-apikey": "lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo"
}
GRAPHQL_QUERY = """
query Billboard($countryId: String!, $movieId: String!, $cinemas: String!, $timezone: String) {
  billboard(
    countryId: $countryId
    movieId: $movieId
    cinemas: $cinemas
    timezone: $timezone
  ) {
    schedules {
      dates {
        date
        languages {
          displayLanguage
          showtimes {
            sessionId
            datetime
            screen
            format { name }
            experience { name }
            movieVistaId
            cinemaVistaId
          }
        }
      }
    }
  }
}
"""

class MatildeExtractor:
    def __init__(self, modo_debug: bool = True):
        self.peliculas_cache = {}
        self.pares_complejo_pelicula = [] # lista de (complejo_slug, movie_id, categoria)
        self.funciones = []
        self.modo_debug = modo_debug
        self._muestra_guardada = False

    def _buscar_en_media(self, media_list: list, codes: list, tipo: str = "image") -> dict:
        if not media_list: return None
        for code in codes:
            for item in media_list:
                if isinstance(item, dict) and item.get("code") == code and item.get("type") == tipo:
                    return item
        return None

    def _url_desde_media(self, item: dict) -> str:
        if not isinstance(item, dict): return None
        sizes = item.get("sizes") or {}
        ruta = sizes.get("large") or sizes.get("medium") or sizes.get("small")
        resource = item.get("resource")
        if not ruta or not resource: return None
        base = ruta if ruta.startswith("http") else f"{CDN_BASE_ASSETS}{ruta}"
        if not base.endswith("/"): base += "/"
        return f"{base}{resource}"

    def _procesar_json(self, body, slug):
        """Fase 1: Extrae la metadata completa de películas y sus identificadores por cine"""
        data = body.get("data") or {}
        
        # 1. Extraer Películas Base
        movies_data = data.get("movies") or {}
        for edge in movies_data.get("edges") or []:
            node = edge.get("node") or {}
            mid = node.get("id")

            if self.modo_debug and not self._muestra_guardada and node:
                with open("muestra_movie_node.json", "w", encoding="utf-8") as fdebug:
                    json.dump(node, fdebug, ensure_ascii=False, indent=2)
                self._muestra_guardada = True

            if mid and mid not in self.peliculas_cache:
                genero_crudo = node.get("genre", "")
                media_list = node.get("media") or []

                poster_item = self._buscar_en_media(media_list, ["poster", "movie_card"], tipo="image")
                poster_url = self._url_desde_media(poster_item)
                banner_item = self._buscar_en_media(media_list, ["header_movie_detail", "header_purchase_flow"], tipo="image")
                banner_url = self._url_desde_media(banner_item)
                trailer_item = self._buscar_en_media(media_list, ["trailer_mp4"], tipo="video")
                trailer_url = self._url_desde_media(trailer_item)

                self.peliculas_cache[mid] = {
                    "movie_id": mid,
                    "nombre": node.get("name", ""),
                    "clasificacion": node.get("rating", "A"),
                    "genero": ", ".join(genero_crudo) if isinstance(genero_crudo, list) else str(genero_crudo),
                    "duracion_min": node.get("length", 120) or 120,
                    "sinopsis": node.get("synopsis", "") or "",
                    "categoria": "Cartelera", # Fallback
                    "vista_id": None,
                    "poster_url": poster_url,
                    "banner_url": banner_url,
                    "trailer_url": trailer_url,
                    "director": None,
                    "actores": [],
                }

        # 2. Descubrir qué películas se proyectan en este cine
        billboard = data.get("billboardByCinema") or data.get("billboard") or {}
        for sched in billboard.get("schedules") or []:
            mid = sched.get("movieId")
            if not mid: continue
            
            cat_raw = sched.get("category", "Cartelera")
            cat_map = {"Estreno": "Estreno", "Preventa": "Preventa", "Próximamente": "Proximamente", "+Que Cine": "+Que Cine", "Sala de Arte": "Sala de Arte", "Garantía Cinépolis": "Garantia Cinepolis"}
            categoria_limpia = cat_map.get(cat_raw, "Cartelera")
            
            if mid in self.peliculas_cache:
                self.peliculas_cache[mid]["categoria"] = categoria_limpia

            par = (slug, mid, categoria_limpia)
            if par not in self.pares_complejo_pelicula:
                self.pares_complejo_pelicula.append(par)

    def _consultar_api_horarios(self, complejo_slug, movie_id):
        """Fase 2: Usa curl_cffi para descargar horarios de forma instantánea"""
        payload = {
            "operationName": "Billboard",
            "variables": {
                "movieId": movie_id,
                "cinemas": complejo_slug,
                "countryId": "MX",
                "timezone": "America/Mexico_City",
            },
            "query": GRAPHQL_QUERY,
        }
        try:
            response = cffi_requests.post(API_URL, json=payload, headers=API_HEADERS, impersonate="chrome110", timeout=15)
            if response.status_code != 200:
                print(f"      ❌ HTTP {response.status_code}")
                return
            
            data = response.json().get("data", {})
            schedules = data.get("billboard", {}).get("schedules", [])
            for schedule in schedules:
                for day in schedule.get("dates", []):
                    for lang in day.get("languages", []):
                        idioma_display = lang.get("displayLanguage", "Español")
                        for show in lang.get("showtimes", []):
                            formato_data = show.get("format") or {}
                            exp_data = show.get("experience") or {}
                            sala_raw = show.get("screen", "")
                            num_sala = ''.join(filter(str.isdigit, str(sala_raw))) or "1"
                            
                            movie_vista_id = show.get("movieVistaId")
                            if movie_vista_id and movie_id in self.peliculas_cache and not self.peliculas_cache[movie_id]["vista_id"]:
                                self.peliculas_cache[movie_id]["vista_id"] = movie_vista_id

                            self.funciones.append({
                                "complejo_slug": complejo_slug,
                                "cinema_vista_id": show.get("cinemaVistaId", ""),
                                "session_id": show.get("sessionId", ""),
                                "datetime": show.get("datetime", ""),
                                "numero_sala": num_sala,
                                "formato": formato_data.get("name", "2D"),
                                "idioma": idioma_display,
                                "experiencia": exp_data.get("name", "Tradicional"),
                                "movie_id": movie_id,
                            })
        except Exception as e:
            print(f"      ❌ Error de red: {e}")

    def ejecutar(self):
        print("═" * 60)
        print("  WORKER HÍBRIDO V6.0 (PLAYWRIGHT + CURL_CFFI)")
        print("═" * 60)
        
        # ── FASE 1: DESCUBRIMIENTO CON PLAYWRIGHT ──
        print("\n[FASE 1] Mapeando películas por complejo (Playwright)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = ctx.new_page()
            
            page.goto("https://cinepolis.com", wait_until="domcontentloaded")
            time.sleep(2)
            
            for i, complejo in enumerate(COMPLEJOS, 1):
                respuestas_cine = []
                def on_resp(r):
                    if "billboards/graphql" in r.url:
                        try:
                            if r.request.method != "OPTIONS":
                                body = r.json()
                                respuestas_cine.append(body)
                        except: pass
                
                page.on("response", on_resp)
                ahora = datetime.now()
                if ahora.hour >= 22:
                    manana = ahora + timedelta(days=1)
                    url_objetivo = f"https://cinepolis.com/mx?cinema={complejo['slug']}&date={manana.strftime('%Y-%m-%d')}"
                else:
                    url_objetivo = f"https://cinepolis.com/mx?cinema={complejo['slug']}"

                print(f"  [{i:>2}/{len(COMPLEJOS)}] {complejo['nombre']}...")
                try: page.evaluate("window.localStorage.clear(); window.sessionStorage.clear();")
                except: pass
                
                try:
                    page.goto(url_objetivo, wait_until="networkidle", timeout=25000)
                    time.sleep(2)
                except Exception as e:
                    print(f"    ⚠️ Timeout ignorado, usando lo capturado.")
                
                page.remove_listener("response", on_resp)
                for body in respuestas_cine:
                    self._procesar_json(body, complejo["slug"])
                
                time.sleep(1)
            browser.close()

        # ── FASE 2: DESCARGA PROFUNDA CON API DIRECTA ──
        print(f"\n[FASE 2] Descargando horarios detallados para {len(self.pares_complejo_pelicula)} pares...")
        total_pares = len(self.pares_complejo_pelicula)
        for i, par in enumerate(self.pares_complejo_pelicula, 1):
            complejo_slug, movie_id, categoria = par
            nombre_peli = self.peliculas_cache.get(movie_id, {}).get("nombre", movie_id)
            print(f"  [{i:>3}/{total_pares}] {complejo_slug} -> {nombre_peli}")
            self._consultar_api_horarios(complejo_slug, movie_id)
            time.sleep(0.1) # Pequeña pausa para no saturar

class ExportadorVisionWorker:
    def __init__(self, peliculas_cache, funciones):
        self.peliculas_cache = peliculas_cache
        self.funciones = funciones

    def guardar_sql(self, ruta="cartelera_vision_worker.sql"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "-- ============================================================",
            f"-- WORKER MATILDE v6.0 (HÍBRIDO) — {ts}",
            "-- ============================================================\n",
            "BEGIN;\n"
        ]

        lines.append("-- ── 0. PREPARACIÓN ARQUITECTÓNICA ──")
        lines.append("ALTER TABLE PELICULA DROP CONSTRAINT IF EXISTS pelicula_vista_id_key;")
        lines.append("ALTER TABLE FUNCION ADD COLUMN IF NOT EXISTS activa BOOLEAN NOT NULL DEFAULT TRUE;")
        lines.append("ALTER TABLE FUNCION DROP CONSTRAINT IF EXISTS uq_funcion_logica;")
        lines.append("ALTER TABLE FUNCION ADD CONSTRAINT uq_funcion_logica UNIQUE (sala_id, fecha_funcion, hora_inicio);\n")
        lines.append("CREATE TEMP TABLE tmp_funciones_activas (complejo_slug VARCHAR, numero_sala INT, fecha DATE, hora_inicio TIME);\n")

        lines.append("-- ── 1. UPSERT PELÍCULAS ────────────────────────────────────")
        for mid, p in self.peliculas_cache.items():
            vista_id = p.get("vista_id") or mid
            cl = p.get("clasificacion", "A").replace("'", "''")
            if cl not in ['AA', 'A', 'B', 'B15', 'C']: cl = 'A'
            ge = p.get("genero", "").replace("'", "''")
            n = p.get("nombre", "").replace("'", "''")
            dur_str = str(p.get("duracion_min", "120"))
            dur = ''.join(filter(str.isdigit, dur_str)) or "120"
            cat = p.get("categoria", "Cartelera")

            def _sql_val(v):
                if not v: return "NULL"
                return "'" + str(v).replace("'", "''") + "'"

            poster_sql = _sql_val(p.get("poster_url"))
            banner_sql = _sql_val(p.get("banner_url"))
            trailer_sql = _sql_val(p.get("trailer_url"))
            sinopsis_raw = p.get("sinopsis", "") or ""
            sinopsis_sql = _sql_val(sinopsis_raw) if sinopsis_raw else "NULL"

            lines.append(
                f"INSERT INTO PELICULA (vista_id, titulo, slug, clasificacion, genero, duracion_min, sinopsis, categoria, poster_url, banner_url, trailer_url) "
                f"VALUES ('{vista_id}', '{n}', '{mid}', '{cl}', '{ge}', {dur}, {sinopsis_sql}, '{cat}', {poster_sql}, {banner_sql}, {trailer_sql}) "
                f"ON CONFLICT (slug) DO UPDATE SET clasificacion = EXCLUDED.clasificacion, categoria = EXCLUDED.categoria, "
                f"sinopsis = COALESCE(EXCLUDED.sinopsis, PELICULA.sinopsis), "
                f"poster_url = COALESCE(EXCLUDED.poster_url, PELICULA.poster_url), "
                f"banner_url = COALESCE(EXCLUDED.banner_url, PELICULA.banner_url), "
                f"trailer_url = COALESCE(EXCLUDED.trailer_url, PELICULA.trailer_url);"
            )

        lines.append("\n-- ── 2. SALAS Y FORMATOS (DO NOTHING) ───────────────────────")
        salas_vistas = set()
        for f in self.funciones:
            clave_sala = (f["complejo_slug"], f["numero_sala"])
            if clave_sala not in salas_vistas:
                salas_vistas.add(clave_sala)
                infra_map = {"Tradicional": "Tradicional", "VIP": "VIP", "Macro XE": "MACRO XE", "IMAX": "IMAX", "4DX": "4DX", "Junior": "Junior"}
                tipo_sala = infra_map.get(f["experiencia"], "Tradicional")
                
                lines.append(
                    f"INSERT INTO SALA (numero_sala, nombre_sala, capacidad_asientos, tipo_sala, complejo_id) "
                    f"SELECT {f['numero_sala']}, 'Sala {f['numero_sala']}', 100, '{tipo_sala}', c.complejo_id "
                    f"FROM COMPLEJO c WHERE c.slug = '{f['complejo_slug']}' "
                    f"ON CONFLICT (complejo_id, numero_sala) DO NOTHING;"
                )
            
            fmt = f["formato"] if f["formato"] in ['2D', '3D', 'IMAX 3D'] else '2D'
            lines.append(
                f"INSERT INTO SALA_FORMATO_SALA (sala_id, formato_id) "
                f"SELECT s.sala_id, fs.formato_id FROM SALA s JOIN COMPLEJO c ON s.complejo_id = c.complejo_id "
                f"CROSS JOIN FORMATO_SALA fs WHERE c.slug = '{f['complejo_slug']}' AND s.numero_sala = {f['numero_sala']} AND fs.nombre_formato = '{fmt}' "
                f"ON CONFLICT DO NOTHING;"
            )

        lines.append("\n-- ── 3. UPSERT FUNCIONES Y REGISTRO TEMPORAL ────────────────")
        for f in self.funciones:
            try:
                dt_obj = datetime.fromisoformat(f["datetime"])
                fecha = dt_obj.strftime("%Y-%m-%d")
                hora_raw = int(dt_obj.strftime("%H"))
                hora_correcta = hora_raw % 24
                hora_ini = f"{hora_correcta:02d}:{dt_obj.strftime('%M:%S')}"
                hora_fin = f"{(hora_raw + 2) % 24:02d}:{dt_obj.strftime('%M:%S')}"
            except: continue

            idioma_raw = str(f["idioma"]).upper()
            if "SUB" in idioma_raw: idioma_val = "Subtitulada"
            elif "DOB" in idioma_raw: idioma_val = "Doblada"
            else: idioma_val = "Español"
                
            fmt = f["formato"] if f["formato"] in ['2D', '3D', 'IMAX 3D'] else '2D'
            
            lines.append(f"INSERT INTO tmp_funciones_activas VALUES ('{f['complejo_slug']}', {f['numero_sala']}, '{fecha}', '{hora_ini}');")
            
            lines.append(
                f"INSERT INTO FUNCION (fecha_funcion, hora_inicio, hora_termino, idioma, es_preventa, formato_id, sala_id, pelicula_id, activa) "
                f"SELECT '{fecha}', '{hora_ini}', '{hora_fin}', '{idioma_val}', FALSE, fs.formato_id, s.sala_id, p.pelicula_id, TRUE "
                f"FROM COMPLEJO c JOIN SALA s ON s.complejo_id = c.complejo_id CROSS JOIN FORMATO_SALA fs CROSS JOIN PELICULA p "
                f"WHERE c.slug = '{f['complejo_slug']}' AND s.numero_sala = {f['numero_sala']} AND fs.nombre_formato = '{fmt}' AND p.slug = '{f['movie_id']}' "
                f"ON CONFLICT (sala_id, fecha_funcion, hora_inicio) DO UPDATE SET activa = TRUE, formato_id = EXCLUDED.formato_id, pelicula_id = EXCLUDED.pelicula_id;"
            )

        lines.append("\n-- ── 4. RECOLECTOR DE BASURA (FAIL-SAFE) ──────────────────")
        if len(self.funciones) < 500:
            lines.append("-- ❌ [FAIL-SAFE ACTIVADO]: Se extrajeron muy pocas funciones.")
            lines.append("-- El Soft-Delete ha sido abortado para proteger la cartelera actual en BD.")
        else:
            lines.append("""
UPDATE FUNCION f
SET activa = FALSE
WHERE fecha_funcion >= CURRENT_DATE
AND NOT EXISTS (
    SELECT 1 FROM tmp_funciones_activas t
    JOIN COMPLEJO c ON c.slug = t.complejo_slug
    JOIN SALA s ON s.complejo_id = c.complejo_id AND s.numero_sala = t.numero_sala
    WHERE f.sala_id = s.sala_id 
      AND f.fecha_funcion = t.fecha 
      AND f.hora_inicio = t.hora_inicio
);
            """)
        
        lines.append("\nDROP TABLE tmp_funciones_activas;")
        lines.append("COMMIT;")

        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  [SQL WORKER] {ruta} guardado exitosamente.")

    def guardar_json(self, ruta="cartelera_veracruz_completa.json"):
        payload = {
            "generado": datetime.now().isoformat(),
            "peliculas": list(self.peliculas_cache.values()),
            "funciones": self.funciones,
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"  [JSON] {ruta} guardado exitosamente ({len(self.funciones)} funciones).")

    def guardar_csv(self, ruta_peliculas="peliculas.csv", ruta_funciones="funciones.csv"):
        import csv as _csv
        if self.peliculas_cache:
            campos_p = list(next(iter(self.peliculas_cache.values())).keys())
            with open(ruta_peliculas, "w", newline="", encoding="utf-8") as f:
                writer = _csv.DictWriter(f, fieldnames=campos_p)
                writer.writeheader()
                writer.writerows(self.peliculas_cache.values())
            print(f"  [CSV] {ruta_peliculas} guardado exitosamente.")

        if self.funciones:
            campos_f = list(self.funciones[0].keys())
            with open(ruta_funciones, "w", newline="", encoding="utf-8") as f:
                writer = _csv.DictWriter(f, fieldnames=campos_f)
                writer.writeheader()
                writer.writerows(self.funciones)
            print(f"  [CSV] {ruta_funciones} guardado exitosamente.")

def main():
    print("\n" + "═" * 60)
    print("  EXTRACTOR WORKER MATILDE v6.0 (HÍBRIDO)")
    print("═" * 60 + "\n")

    extractor = MatildeExtractor()
    extractor.ejecutar()

    if extractor.funciones:
        exportador = ExportadorVisionWorker(extractor.peliculas_cache, extractor.funciones)
        exportador.guardar_sql()
        exportador.guardar_json()
        exportador.guardar_csv()
        print(f"\n✅ Extracción exitosa. {len(extractor.funciones)} funciones encontradas.")
        if extractor.modo_debug:
            print("ℹ️  Revisa 'muestra_movie_node.json' para confirmar los nombres reales de campos.")
    else:
        print("\n⚠️ Falló la extracción. Cinépolis no devolvió horarios.")

if __name__ == "__main__":
    main()