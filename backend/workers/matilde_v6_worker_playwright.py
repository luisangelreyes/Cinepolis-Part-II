"""
=============================================================================
EXTRACTOR MATILDE — v5.1 (WORKER BROWSER 100% REAL)
=============================================================================
Mecanismos de Defensa:
  1. 100% Playwright VISIBLE: Evita bloqueos de Cloudflare y CAPTCHAs.
  2. Single-Pass: Solo visita 19 URLs maestras interceptando GraphQL en red.
  3. Night Owl Patch: Navega a la fecha de mañana si son más de las 10 PM.
  4. Null-Safe: Protegido contra atributos vacíos de la API de Cinépolis.
  5. DDL Dinámico: Elimina restricciones rígidas de vista_id.
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

# CORRECCIÓN: Dominio base para reconstruir URLs de media (poster/banner/trailer).
# La API sólo devuelve rutas relativas tipo "/pimcore/19133/assets/.../carpeta/" +
# un nombre de archivo fijo ("resource.jpg" / "resource.mp4"). Dominio confirmado
# manualmente via Network tab (ejemplo real de poster):
# https://tickets-static-content.cinepolis.com/pimcore/19133/assets/Mexico/Tickets/
# Movies/MiniosYMonstruos/Es/9_P_ster_720x1022px__2/resource.jpg
CDN_BASE_ASSETS = "https://tickets-static-content.cinepolis.com"

class MatildeExtractor:
    def __init__(self, modo_debug: bool = True):
        self.peliculas_cache = {}
        self.funciones = []
        self.modo_debug = modo_debug
        self._muestra_guardada = False

    def _buscar_en_media(self, media_list: list, codes: list, tipo: str = "image") -> dict:
        """
        Busca en el arreglo 'media' del nodo el primer elemento cuyo 'code' coincida
        con alguno de los códigos candidatos (en orden de prioridad) y cuyo 'type'
        sea el esperado ('image' o 'video'). Devuelve el item completo (no la URL)
        para que _url_desde_media() construya la ruta final.
        """
        if not media_list:
            return None
        for code in codes:
            for item in media_list:
                if isinstance(item, dict) and item.get("code") == code and item.get("type") == tipo:
                    return item
        return None

    def _url_desde_media(self, item: dict) -> str:
        """
        Construye la URL completa de un elemento de 'media'. La API de Cinépolis
        (Pimcore) devuelve rutas relativas en sizes.large/medium/small (con "/" al
        final) y un nombre de archivo fijo en 'resource' (p.ej. "resource.jpg" o
        "resource.mp4"). La URL real = CDN_BASE_ASSETS + ruta + resource.
        """
        if not isinstance(item, dict):
            return None
        sizes = item.get("sizes") or {}
        ruta = sizes.get("large") or sizes.get("medium") or sizes.get("small")
        resource = item.get("resource")
        if not ruta or not resource:
            return None
        base = ruta if ruta.startswith("http") else f"{CDN_BASE_ASSETS}{ruta}"
        if not base.endswith("/"):
            base += "/"
        return f"{base}{resource}"

    def _procesar_json(self, body, slug):
        data = body.get("data") or {}
        
        # 1. Extraer Películas Base
        movies_data = data.get("movies") or {}
        for edge in movies_data.get("edges") or []:
            node = edge.get("node") or {}
            mid = node.get("id")

            # CORRECCIÓN: modo debug — vuelca el primer nodo 'movie' completo tal cual
            # llega de la API, para poder inspeccionar los nombres reales de los campos
            # de imagen/trailer sin adivinar. Se guarda UNA sola vez por corrida.
            if self.modo_debug and not self._muestra_guardada and node:
                with open("muestra_movie_node.json", "w", encoding="utf-8") as fdebug:
                    json.dump(node, fdebug, ensure_ascii=False, indent=2)
                print("  [DEBUG] Nodo 'movie' completo volcado en muestra_movie_node.json "
                      "— revisa ahí los nombres reales de campos de imagen/trailer.")
                self._muestra_guardada = True

            if mid and mid not in self.peliculas_cache:
                genero_crudo = node.get("genre", "")

                # CORRECCIÓN: extracción real desde el array 'media' (confirmado con
                # muestra_movie_node.json). Cada item trae code/type/resource/sizes.
                # Prioridad: "poster" (poster real) > "movie_card" (tarjeta cuadrada)
                # como fallback. Igual para banner y trailer.
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
                    "categoria": "Cartelera", # Se actualiza abajo si es Estreno/Preventa
                    "vista_id": None,
                    "poster_url": poster_url,
                    "banner_url": banner_url,
                    "trailer_url": trailer_url,
                    "director": None,
                    "actores": [],
                }

        # 2. Extraer Funciones y Horarios
        billboard = data.get("billboardByCinema") or data.get("billboard") or {}
        
        for sched in billboard.get("schedules") or []:
            mid = sched.get("movieId")
            if not mid: continue
            
            cat_raw = sched.get("category", "Cartelera")
            cat_map = {"Estreno": "Estreno", "Preventa": "Preventa", "Próximamente": "Proximamente", "+Que Cine": "+Que Cine", "Sala de Arte": "Sala de Arte", "Garantía Cinépolis": "Garantia Cinepolis"}
            categoria_limpia = cat_map.get(cat_raw, "Cartelera")
            
            # Actualizamos la categoría de la película si la encontramos
            if mid in self.peliculas_cache:
                self.peliculas_cache[mid]["categoria"] = categoria_limpia

            # Recorrer el árbol de horarios (Null-Safe)
            for day in sched.get("dates") or []:
                for lang in day.get("languages") or []:
                    for show in lang.get("showtimes") or []:
                        sala_raw = show.get("screen", "")
                        num_sala = ''.join(filter(str.isdigit, str(sala_raw))) or "1"
                        
                        if not getattr(self, "_lang_muestra", False):
                            with open("lang_muestra.json", "w", encoding="utf-8") as f:
                                json.dump(lang, f, ensure_ascii=False, indent=2)
                            self._lang_muestra = True

                        movie_vista_id = show.get("movieVistaId")
                        if movie_vista_id and mid in self.peliculas_cache and not self.peliculas_cache[mid]["vista_id"]:
                            self.peliculas_cache[mid]["vista_id"] = movie_vista_id

                        # PROTECCIÓN CONTRA NULOS (NULL) DE LA API
                        formato_data = show.get("format") or {}
                        experiencia_data = show.get("experience") or {}

                        self.funciones.append({
                            "complejo_slug": slug,
                            "cinema_vista_id": show.get("cinemaVistaId", ""),
                            "session_id": show.get("sessionId", ""),
                            "datetime": show.get("datetime", ""),
                            "numero_sala": num_sala,
                            "formato": formato_data.get("name", "2D"),
                            "idioma": lang.get("displayLanguage", "Español"),
                            "experiencia": experiencia_data.get("name", "Tradicional"),
                            "movie_id": mid,
                        })

    def _extraer_elenco_html(self, page) -> tuple:
        """
        Visita la página de detalle de la película (ya cargada en `page`) y
        extrae director y actores del HTML de Cinépolis.
        Devuelve (director: str | None, actores: list[str]).
        """
        director = None
        actores = []
        try:
            # Esperar a que cargue el contenido dinámico
            page.wait_for_selector("[class*='movie-detail'], [class*='cast'], [class*='crew'], main", timeout=8000)
        except:
            pass
        try:
            html = page.content()
            import re

            # ── Estrategia 1: buscar texto "Dirección" / "Director" seguido del nombre ──
            dir_match = re.search(
                r'(?i)(?:direcci[oó]n|director)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s\.]+?)(?:\s*<|\n|\||,)',
                html
            )
            if dir_match:
                director = dir_match.group(1).strip()

            # ── Estrategia 2: tag data-testid o class que contenga 'director' ──
            if not director:
                try:
                    el = page.query_selector('[data-testid*="director"], [class*="director"]')
                    if el:
                        director = el.inner_text().strip()[:80]
                except:
                    pass

            # ── Actores: buscar sección 'Actores' / 'Cast' / 'Reparto' ──
            cast_match = re.search(
                r'(?i)(?:actores|reparto|cast)\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ,\s\.]+?)(?:<\/|\n\n|\|)',
                html
            )
            if cast_match:
                actores_raw = cast_match.group(1).strip()
                actores = [a.strip() for a in re.split(r'[,|\n]', actores_raw) if a.strip() and len(a.strip()) > 3][:6]

            # ── Estrategia 2 actores: elementos con class 'actor' / 'cast' ──
            if not actores:
                try:
                    els = page.query_selector_all('[class*="actor"], [class*="cast-member"], [data-testid*="actor"]')
                    actores = [e.inner_text().strip() for e in els[:6] if e.inner_text().strip()]
                except:
                    pass

        except Exception as e:
            pass
        return director, actores

    def ejecutar(self):
        print("═" * 60)
        print("  WORKER PLAYWRIGHT V5.1 (MODO VISIBLE)")
        print("═" * 60)
        
        with sync_playwright() as p:
            # FIX: headless=False engaña a Cloudflare haciéndole creer que somos humanos
            browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = ctx.new_page()
            
            # Navegar primero al home para obtener cookies limpias
            print("  [INIT] Estableciendo sesión limpia...")
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
                        except Exception as e:
                            pass
                
                page.on("response", on_resp)
                
                # Parche "Night Owl" (Previene pantallas en blanco después de las 10PM)
                ahora = datetime.now()
                if ahora.hour >= 22:
                    manana = ahora + timedelta(days=1)
                    url_objetivo = f"https://cinepolis.com/mx?cinema={complejo['slug']}&date={manana.strftime('%Y-%m-%d')}"
                else:
                    url_objetivo = f"https://cinepolis.com/mx?cinema={complejo['slug']}"

                print(f"  [{i:>2}/19] Extrayendo {complejo['nombre']}...")
                try:
                    # LIMPIAR ESTADO DEL SPA PARA EVITAR MULTIPLES PETICIONES DEL CINE ANTERIOR
                    page.evaluate("window.localStorage.clear(); window.sessionStorage.clear();")
                except:
                    pass
                try:
                    page.goto(url_objetivo, wait_until="networkidle", timeout=30000)
                    time.sleep(3) # Pausa humana para asegurar carga
                except Exception as e:
                    print(f"    ⚠️ Timeout ignorado, procesando datos capturados...")
                
                page.remove_listener("response", on_resp)
                
                # PROCESAR TODAS LAS RESPUESTAS CAPTURADAS EN ESTA CARGA
                for body in respuestas_cine:
                    self._procesar_json(body, complejo["slug"])
                
                # Pausa humana antes del siguiente cine
                time.sleep(2.5)

            # ── FASE 2: Scrapear detalles (director y actores) de cada película ──
            print("\n  [FASE 2] Extrayendo director y actores de cada película...")
            peliculas_sin_detalle = [
                (mid, p) for mid, p in self.peliculas_cache.items()
                if p.get("director") is None
            ]
            total_peli = len(peliculas_sin_detalle)
            for idx, (mid, p) in enumerate(peliculas_sin_detalle, 1):
                slug_peli = mid  # el id es el slug, ej: "la-odisea"
                url_detalle = f"https://cinepolis.com/mx/pelicula/{slug_peli}"
                print(f"    [{idx:>2}/{total_peli}] {p['nombre']}...")
                try:
                    page.evaluate("window.localStorage.clear(); window.sessionStorage.clear();")
                    page.goto(url_detalle, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(3)
                    director, actores = self._extraer_elenco_html(page)
                    self.peliculas_cache[mid]["director"] = director
                    self.peliculas_cache[mid]["actores"]  = actores
                    if director or actores:
                        print(f"      ✅ Dir: {director}  |  Actores: {', '.join(actores[:3])}")
                    else:
                        print(f"      ⚠️  No se encontró elenco en la página")
                except Exception as e:
                    print(f"      ❌ Error: {e}")
                time.sleep(1.5)

            browser.close()

class ExportadorVisionWorker:
    def __init__(self, peliculas_cache, funciones):
        self.peliculas_cache = peliculas_cache
        self.funciones = funciones

    def guardar_sql(self, ruta="cartelera_vision_worker.sql"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "-- ============================================================",
            f"-- WORKER MATILDE v5.1 (BROWSER PURO) — {ts}",
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

            # CORRECCIÓN: poster_url / banner_url / trailer_url — NULL si no se encontró candidato válido
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

            # Insertar Director (si se scrapeó)
            director = p.get("director")
            if director:
                dir_sql = director.replace("'", "''")
                lines.append(
                    f"INSERT INTO PERSONA (nombre) VALUES ('{dir_sql}') ON CONFLICT (nombre) DO NOTHING;"
                )
                lines.append(
                    f"INSERT INTO PELICULA_PERSONA (pelicula_id, persona_id, rol) "
                    f"SELECT p.pelicula_id, per.persona_id, 'Director' "
                    f"FROM PELICULA p, PERSONA per "
                    f"WHERE p.slug = '{mid}' AND per.nombre = '{dir_sql}' "
                    f"ON CONFLICT DO NOTHING;"
                )

            # Insertar Actores (si se scrapearon)
            for actor in p.get("actores", []):
                act_sql = actor.replace("'", "''")
                lines.append(
                    f"INSERT INTO PERSONA (nombre) VALUES ('{act_sql}') ON CONFLICT (nombre) DO NOTHING;"
                )
                lines.append(
                    f"INSERT INTO PELICULA_PERSONA (pelicula_id, persona_id, rol) "
                    f"SELECT p.pelicula_id, per.persona_id, 'Actor' "
                    f"FROM PELICULA p, PERSONA per "
                    f"WHERE p.slug = '{mid}' AND per.nombre = '{act_sql}' "
                    f"ON CONFLICT DO NOTHING;"
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
            if "SUB" in idioma_raw:
                idioma_val = "Subtitulada"
            elif "DOB" in idioma_raw:
                idioma_val = "Doblada"
            else:
                idioma_val = "Español"
                
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
        if len(self.funciones) < 50:
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
        """
        Restaura el export a JSON (formato consumido por F.R.I.D.A.Y. V3 para
        extraer precios vía session_id). Se regenera SIEMPRE junto al SQL.
        """
        payload = {
            "generado": datetime.now().isoformat(),
            "peliculas": list(self.peliculas_cache.values()),
            "funciones": self.funciones,
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"  [JSON] {ruta} guardado exitosamente ({len(self.funciones)} funciones).")

    def guardar_csv(self, ruta_peliculas="peliculas.csv", ruta_funciones="funciones.csv"):
        """Restaura el export a CSV — útil para inspección rápida en Excel/Sheets."""
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
    print("  EXTRACTOR WORKER MATILDE v5.1 (MODO PRODUCCIÓN VISIBLE)")
    print("═" * 60 + "\n")

    extractor = MatildeExtractor()
    extractor.ejecutar()

    if extractor.funciones:
        exportador = ExportadorVisionWorker(extractor.peliculas_cache, extractor.funciones)
        exportador.guardar_sql()
        exportador.guardar_json()   # CORRECCIÓN: JSON restaurado — lo necesita F.R.I.D.A.Y. V3
        exportador.guardar_csv()    # CORRECCIÓN: CSV restaurado — para inspección rápida
        print(f"\n✅ Extracción exitosa. {len(extractor.funciones)} funciones encontradas.")
        if extractor.modo_debug:
            print("ℹ️  Revisa 'muestra_movie_node.json' para confirmar los nombres reales de "
                  "los campos de imagen/trailer y ajustar los candidatos en _extraer_imagen si hace falta.")
    else:
        print("\n⚠️ Falló la extracción. Cinépolis no devolvió horarios.")

if __name__ == "__main__":
    main()