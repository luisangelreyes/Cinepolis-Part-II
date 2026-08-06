"""
=============================================================================
EXTRACTOR MATILDE — v7.0 (BLINDADO: PLAYWRIGHT + CURL_CFFI + FALLBACK TOTAL)
=============================================================================
Filosofia: "NUNCA RENDIRSE" — cada complejo DEBE tener funciones al final.

Mecanismos de Defensa:
  1. Fase 0: Playwright VISIBLE con bypass Cloudflare inicial.
  2. Fase 1: Descubrimiento por complejo con REINTENTOS AGRESIVOS (5x).
  3. Fase 1.5: Fallback API-first para complejos sin datos.
             Usa el catalogo completo de peliculas descubiertas y prueba
             cada una contra el cine faltante via curl_cffi.
  4. Fase 2: Descarga profunda de horarios con backoff mejorado.
  5. Fase 3: Validacion final de cobertura 19/19.
  6. DDL Dinamico: Elimina restricciones rigidas de vista_id.
=============================================================================
"""

import time
import random
import sys
from datetime import datetime, timedelta
import json
import traceback

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

# ─── Forzar UTF-8 en consola Windows ───
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════════════════════

COMPLEJOS = [
    {"nombre": "La Florida Acayucan",      "slug": "cinepolis-la-florida-acayucan"},
    {"nombre": "VIP El Dorado Veracruz",   "slug": "cinepolis-vip-el-dorado-veracruz"},
    {"nombre": "Las Americas Veracruz",    "slug": "cinepolis-las-americas-veracruz"},
    {"nombre": "VIP Las Americas Veracruz","slug": "cinepolis-vip-las-americas-veracruz"},
    {"nombre": "El Dorado Coatzacoalcos",  "slug": "cinepolis-el-dorado-coatzacoalcos"},
    {"nombre": "Acaya Coatzacoalcos",      "slug": "cinepolis-acaya-coatzacoalcos"},
    {"nombre": "Plaza Shangri La Cordoba", "slug": "cinepolis-plaza-shangri-la-cordoba"},
    {"nombre": "Plaza Museo Xalapa",       "slug": "cinepolis-plaza-museo-xalapa"},
    {"nombre": "Plaza Crystal Xalapa",     "slug": "cinepolis-plaza-crystal-xalapa"},
    {"nombre": "VIP Las Americas Xalapa",  "slug": "cinepolis-vip-las-americas-xalapa"},
    {"nombre": "Plaza Las Americas Xalapa","slug": "cinepolis-plaza-las-americas-xalapa"},
    {"nombre": "Chedraui Martinez Torre",  "slug": "cinepolis-chedraui-martinez-de-la-torre"},
    {"nombre": "Plaza Minatitlan",         "slug": "cinepolis-plaza-minatitlan"},
    {"nombre": "Plaza Valle Orizaba",      "slug": "cinepolis-plaza-valle-orizaba"},
    {"nombre": "Rio Blanco Orizaba",       "slug": "cinepolis-rio-blanco-orizaba"},
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

# Query GraphQL para horarios detallados por pelicula+cine
GRAPHQL_QUERY_HORARIOS = """
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

# User-agents para rotacion en reintentos
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

IMPERSONATE_OPTIONS = ["chrome110", "chrome116", "chrome120", "safari15_5", "edge101"]


def ts():
    """Timestamp legible para logs"""
    return datetime.now().strftime("%H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTOR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

class MatildeExtractorV7:
    def __init__(self, modo_debug: bool = True):
        self.peliculas_cache = {}           # movie_id -> {metadata}
        self.pares_complejo_pelicula = []    # lista de (complejo_slug, movie_id, categoria)
        self.funciones = []                 # lista de funciones extraidas
        self.modo_debug = modo_debug
        self._muestra_guardada = False
        self.complejos_descubiertos = set() # slugs con >=1 par descubierto
        self.session = self._crear_session()
        self._consecutivos_429 = 0

    def _crear_session(self, impersonate=None):
        imp = impersonate or random.choice(IMPERSONATE_OPTIONS)
        s = cffi_requests.Session(impersonate=imp)
        s.headers.update(API_HEADERS)
        return s

    # ─── Helpers de media ───

    def _buscar_en_media(self, media_list: list, codes: list, tipo: str = "image") -> dict:
        if not media_list:
            return None
        for code in codes:
            for item in media_list:
                if isinstance(item, dict) and item.get("code") == code and item.get("type") == tipo:
                    return item
        return None

    def _url_desde_media(self, item: dict) -> str:
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

    # ─── Procesamiento de JSON GraphQL ───

    def _procesar_json(self, body, slug):
        """Extrae la metadata de peliculas y los pares complejo-pelicula de una respuesta GraphQL."""
        data = body.get("data") or {}

        # 1. Extraer Peliculas Base
        movies_data = data.get("movies") or {}
        for edge in movies_data.get("edges") or []:
            node = edge.get("node") or {}
            mid = node.get("id")

            if self.modo_debug and not self._muestra_guardada and node:
                try:
                    with open("muestra_movie_node.json", "w", encoding="utf-8") as fdebug:
                        json.dump(node, fdebug, ensure_ascii=False, indent=2)
                    self._muestra_guardada = True
                except Exception:
                    pass

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
                    "categoria": "Cartelera",
                    "vista_id": None,
                    "poster_url": poster_url,
                    "banner_url": banner_url,
                    "trailer_url": trailer_url,
                    "director": None,
                    "actores": [],
                }

        # 2. Descubrir que peliculas se proyectan en este cine
        billboard = data.get("billboardByCinema") or data.get("billboard") or {}
        pares_encontrados = 0
        for sched in billboard.get("schedules") or []:
            mid = sched.get("movieId")
            if not mid:
                continue

            cat_raw = sched.get("category", "Cartelera")
            cat_map = {
                "Estreno": "Estreno",
                "Preventa": "Preventa",
                "Proximamente": "Proximamente",
                "+Que Cine": "+Que Cine",
                "Sala de Arte": "Sala de Arte",
                "Garantia Cinepolis": "Garantia Cinepolis",
            }
            categoria_limpia = cat_map.get(cat_raw, "Cartelera")

            if mid in self.peliculas_cache:
                self.peliculas_cache[mid]["categoria"] = categoria_limpia

            par = (slug, mid, categoria_limpia)
            if par not in self.pares_complejo_pelicula:
                self.pares_complejo_pelicula.append(par)
                pares_encontrados += 1

        if pares_encontrados > 0:
            self.complejos_descubiertos.add(slug)

        return pares_encontrados

    # ─── FASE 1: Descubrimiento con Playwright + Reintentos ───

    def _fase1_descubrir_con_playwright(self, page, complejo, intento):
        """Intenta descubrir las peliculas de un complejo via Playwright.
        Retorna el numero de pares descubiertos (0 = fallo)."""
        slug = complejo["slug"]
        nombre = complejo["nombre"]

        # Timeouts escalados por intento
        timeout_nav = 45000 + (intento * 15000)   # 45s, 60s, 75s, 90s, 105s
        timeout_resp = 15000 + (intento * 5000)    # 15s, 20s, 25s, 30s, 35s

        respuestas_cine = []

        def on_resp(r):
            if "billboards/graphql" in r.url:
                try:
                    if r.request.method != "OPTIONS":
                        body = r.json()
                        respuestas_cine.append(body)
                except Exception:
                    pass

        page.on("response", on_resp)

        # Determinar URL objetivo
        ahora = datetime.now()
        if ahora.hour >= 22:
            manana = ahora + timedelta(days=1)
            url_objetivo = f"https://cinepolis.com/mx?cinema={slug}&date={manana.strftime('%Y-%m-%d')}"
        else:
            url_objetivo = f"https://cinepolis.com/mx?cinema={slug}"

        # Limpiar storage antes de cada intento
        try:
            page.evaluate("window.localStorage.clear(); window.sessionStorage.clear();")
        except Exception:
            pass

        try:
            page.goto(url_objetivo, wait_until="domcontentloaded", timeout=timeout_nav)

            # Esperar la respuesta GraphQL especifica
            try:
                page.wait_for_response(
                    lambda r: "billboards/graphql" in r.url and r.request.method != "OPTIONS",
                    timeout=timeout_resp
                )
            except Exception:
                pass

            # Espera adicional para capturar respuestas tardias
            time.sleep(3)

            # Scroll suave para activar lazy-loading si existe
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(1)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
            except Exception:
                pass

        except Exception as e:
            print(f"    [{ts()}] Intento {intento+1}: Error navegacion ({type(e).__name__})")

        page.remove_listener("response", on_resp)

        # Procesar las respuestas capturadas
        pares_totales = 0
        for body in respuestas_cine:
            pares_totales += self._procesar_json(body, slug)

        return pares_totales

    def _fase1(self):
        """FASE 1: Descubrimiento completo con Playwright + reintentos agresivos."""
        print(f"\n[{ts()}] ══════════════════════════════════════════════════")
        print(f"[{ts()}] FASE 1: Descubrimiento de peliculas por complejo")
        print(f"[{ts()}] ══════════════════════════════════════════════════")

        MAX_REINTENTOS = 5

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ]
            )
            ctx = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1280, "height": 800}
            )
            page = ctx.new_page()

            # Fase 0: Navegar a cinepolis.com para pasar el challenge de Cloudflare
            print(f"\n[{ts()}] [FASE 0] Bypass inicial de Cloudflare...")
            try:
                page.goto("https://cinepolis.com", wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)  # Dar tiempo al challenge JS de Cloudflare
                print(f"[{ts()}] [FASE 0] OK - Pagina principal cargada")
            except Exception as e:
                print(f"[{ts()}] [FASE 0] Advertencia: {e}")
                time.sleep(3)

            # Procesar cada complejo
            for i, complejo in enumerate(COMPLEJOS, 1):
                slug = complejo["slug"]
                nombre = complejo["nombre"]
                print(f"\n[{ts()}] [{i:>2}/{len(COMPLEJOS)}] {nombre} ({slug})")

                pares_antes = len([p for p in self.pares_complejo_pelicula if p[0] == slug])
                exito = False

                for intento in range(MAX_REINTENTOS):
                    if intento > 0:
                        espera = 10 + (intento * 5) + random.uniform(0, 5)
                        print(f"    [{ts()}] Esperando {espera:.0f}s antes de reintento {intento+1}...")
                        time.sleep(espera)

                        # Rotar user-agent en reintentos
                        if intento >= 2:
                            try:
                                ctx.close()
                            except Exception:
                                pass
                            ctx = browser.new_context(
                                user_agent=random.choice(USER_AGENTS),
                                viewport={"width": 1280, "height": 800}
                            )
                            page = ctx.new_page()
                            # Re-navegar a cinepolis.com para refrescar cookies
                            try:
                                page.goto("https://cinepolis.com", wait_until="domcontentloaded", timeout=30000)
                                time.sleep(3)
                            except Exception:
                                pass

                    pares = self._fase1_descubrir_con_playwright(page, complejo, intento)

                    if pares > 0 or slug in self.complejos_descubiertos:
                        pares_totales = len([p for p in self.pares_complejo_pelicula if p[0] == slug])
                        print(f"    [{ts()}] OK - {pares_totales} peliculas descubiertas (intento {intento+1})")
                        exito = True
                        break
                    else:
                        print(f"    [{ts()}] Intento {intento+1}/{MAX_REINTENTOS}: Sin peliculas")

                if not exito:
                    print(f"    [{ts()}] PENDIENTE - Se intentara con fallback API en Fase 1.5")

                # Pausa anti-ban entre complejos
                pausa = random.uniform(2.0, 4.0)
                time.sleep(pausa)

            browser.close()

        # Resumen de Fase 1
        descubiertos = len(self.complejos_descubiertos)
        total = len(COMPLEJOS)
        print(f"\n[{ts()}] ── Resumen Fase 1 ──")
        print(f"[{ts()}] Complejos descubiertos: {descubiertos}/{total}")
        print(f"[{ts()}] Peliculas en catalogo: {len(self.peliculas_cache)}")
        print(f"[{ts()}] Pares complejo-pelicula: {len(self.pares_complejo_pelicula)}")

    # ─── FASE 1.5: Fallback API-First para complejos faltantes ───

    def _fase15_fallback_api(self):
        """Para cada complejo sin datos, prueba TODAS las peliculas conocidas via API directa."""
        complejos_faltantes = [
            c for c in COMPLEJOS
            if c["slug"] not in self.complejos_descubiertos
        ]

        if not complejos_faltantes:
            print(f"\n[{ts()}] [FASE 1.5] No hay complejos faltantes. Saltando fallback.")
            return

        print(f"\n[{ts()}] ══════════════════════════════════════════════════════════")
        print(f"[{ts()}] FASE 1.5: Fallback API para {len(complejos_faltantes)} complejos faltantes")
        print(f"[{ts()}] ══════════════════════════════════════════════════════════")

        if not self.peliculas_cache:
            print(f"[{ts()}] ERROR CRITICO: No hay peliculas en catalogo. No se puede hacer fallback.")
            return

        peliculas_ids = list(self.peliculas_cache.keys())
        print(f"[{ts()}] Probando {len(peliculas_ids)} peliculas contra cada complejo faltante...")

        for complejo in complejos_faltantes:
            slug = complejo["slug"]
            nombre = complejo["nombre"]
            print(f"\n[{ts()}] Fallback: {nombre} ({slug})")
            pares_encontrados = 0

            for j, movie_id in enumerate(peliculas_ids, 1):
                nombre_peli = self.peliculas_cache[movie_id].get("nombre", movie_id)

                # Consultar API directamente
                payload = {
                    "operationName": "Billboard",
                    "variables": {
                        "movieId": movie_id,
                        "cinemas": slug,
                        "countryId": "MX",
                        "timezone": "America/Mexico_City",
                    },
                    "query": GRAPHQL_QUERY_HORARIOS,
                }

                intentos_api = 0
                max_intentos_api = 5

                while intentos_api < max_intentos_api:
                    try:
                        response = self.session.post(API_URL, json=payload, timeout=20)

                        if response.status_code == 429:
                            intentos_api += 1
                            espera = 10 * (2 ** (intentos_api - 1))
                            print(f"    [{ts()}] HTTP 429. Esperando {espera}s (intento {intentos_api})...")
                            time.sleep(espera)
                            self.session = self._crear_session()
                            continue

                        if response.status_code != 200:
                            break

                        data = response.json().get("data", {})
                        schedules = data.get("billboard", {}).get("schedules", [])

                        tiene_horarios = False
                        for schedule in schedules:
                            for day in schedule.get("dates", []):
                                for lang in day.get("languages", []):
                                    if lang.get("showtimes"):
                                        tiene_horarios = True
                                        break

                        if tiene_horarios:
                            par = (slug, movie_id, "Cartelera")
                            if par not in self.pares_complejo_pelicula:
                                self.pares_complejo_pelicula.append(par)
                                pares_encontrados += 1
                                print(f"    [{ts()}] [{j}/{len(peliculas_ids)}] ENCONTRADA: {nombre_peli}")

                        break  # Exito (con o sin horarios), salir del while

                    except Exception as e:
                        intentos_api += 1
                        if intentos_api < max_intentos_api:
                            time.sleep(5)
                            self.session = self._crear_session()
                        else:
                            print(f"    [{ts()}] Error persistente para {nombre_peli}: {e}")
                        break

                # Pausa entre consultas para evitar rate limiting
                time.sleep(random.uniform(1.5, 3.0))

            if pares_encontrados > 0:
                self.complejos_descubiertos.add(slug)
                print(f"    [{ts()}] Fallback exitoso: {pares_encontrados} peliculas encontradas para {nombre}")
            else:
                print(f"    [{ts()}] ADVERTENCIA: {nombre} sin peliculas (puede estar cerrado o sin cartelera)")

    # ─── FASE 2: Descarga de horarios via API ───

    def _consultar_api_horarios(self, complejo_slug, movie_id):
        """Descarga horarios detallados para un par complejo-pelicula con reintentos robustos."""
        payload = {
            "operationName": "Billboard",
            "variables": {
                "movieId": movie_id,
                "cinemas": complejo_slug,
                "countryId": "MX",
                "timezone": "America/Mexico_City",
            },
            "query": GRAPHQL_QUERY_HORARIOS,
        }

        intentos = 0
        max_intentos = 8

        while intentos < max_intentos:
            try:
                response = self.session.post(API_URL, json=payload, timeout=20)

                if response.status_code == 429:
                    intentos += 1
                    self._consecutivos_429 += 1

                    # Si hay demasiados 429 seguidos, pausa global
                    if self._consecutivos_429 >= 3:
                        pausa_global = 60
                        print(f"      [{ts()}] PAUSA GLOBAL: {self._consecutivos_429} 429s seguidos. Esperando {pausa_global}s...")
                        time.sleep(pausa_global)
                        self._consecutivos_429 = 0

                    espera = 5 * (2 ** (intentos - 1))
                    print(f"      [{ts()}] HTTP 429. Reintentando en {espera}s ({intentos}/{max_intentos})...")
                    time.sleep(espera)
                    self.session = self._crear_session()
                    continue

                # Reset contador de 429 si no fue 429
                self._consecutivos_429 = 0

                if response.status_code != 200:
                    print(f"      [{ts()}] HTTP {response.status_code}")
                    intentos += 1
                    if intentos < max_intentos:
                        time.sleep(5)
                    continue

                data = response.json().get("data", {})
                schedules = data.get("billboard", {}).get("schedules", [])
                funciones_nuevas = 0

                for schedule in schedules:
                    for day in schedule.get("dates", []):
                        for lang in day.get("languages", []):
                            idioma_display = lang.get("displayLanguage", "Espanol")
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
                                funciones_nuevas += 1

                return funciones_nuevas  # Exito

            except Exception as e:
                intentos += 1
                if intentos < max_intentos:
                    print(f"      [{ts()}] Error de red ({e}). Reintentando...")
                    time.sleep(5)
                    self.session = self._crear_session()
                else:
                    print(f"      [{ts()}] Error persistente: {e}")
                    return 0

        return 0

    def _fase2(self):
        """FASE 2: Descarga profunda de horarios para todos los pares descubiertos."""
        total_pares = len(self.pares_complejo_pelicula)
        print(f"\n[{ts()}] ══════════════════════════════════════════════════")
        print(f"[{ts()}] FASE 2: Descargando horarios para {total_pares} pares")
        print(f"[{ts()}] ══════════════════════════════════════════════════")

        for i, par in enumerate(self.pares_complejo_pelicula, 1):
            complejo_slug, movie_id, categoria = par
            nombre_peli = self.peliculas_cache.get(movie_id, {}).get("nombre", movie_id)

            if i % 25 == 0 or i == 1:
                print(f"\n[{ts()}] --- Progreso: {i}/{total_pares} ({len(self.funciones)} funciones) ---")

            print(f"  [{ts()}] [{i:>3}/{total_pares}] {complejo_slug} -> {nombre_peli}")
            funciones_nuevas = self._consultar_api_horarios(complejo_slug, movie_id)

            if funciones_nuevas > 0:
                print(f"    +{funciones_nuevas} funciones")

            # Pausa inteligente: mas rapido al inicio, mas lento si hay muchos 429
            pausa_base = random.uniform(3.0, 5.5)
            time.sleep(pausa_base)

    # ─── FASE 3: Validacion Final ───

    def _fase3_validacion(self):
        """Valida que todos los complejos tienen funciones y reporta el estado."""
        print(f"\n[{ts()}] ══════════════════════════════════════════════════")
        print(f"[{ts()}] FASE 3: Validacion Final de Cobertura")
        print(f"[{ts()}] ══════════════════════════════════════════════════")

        cobertura = {}
        for f in self.funciones:
            slug = f["complejo_slug"]
            cobertura[slug] = cobertura.get(slug, 0) + 1

        total_ok = 0
        total_fail = 0
        complejos_sin_funciones = []

        for complejo in COMPLEJOS:
            slug = complejo["slug"]
            nombre = complejo["nombre"]
            count = cobertura.get(slug, 0)

            if count > 0:
                total_ok += 1
                print(f"  OK  {nombre}: {count} funciones")
            else:
                total_fail += 1
                complejos_sin_funciones.append(nombre)
                print(f"  SIN DATOS  {nombre}: 0 funciones")

        print(f"\n[{ts()}] ── RESULTADO ──")
        print(f"[{ts()}] Cobertura: {total_ok}/{len(COMPLEJOS)} complejos")
        print(f"[{ts()}] Total funciones: {len(self.funciones)}")
        print(f"[{ts()}] Total peliculas: {len(self.peliculas_cache)}")

        if complejos_sin_funciones:
            print(f"\n[{ts()}] ADVERTENCIA: Los siguientes complejos NO tienen funciones:")
            for n in complejos_sin_funciones:
                print(f"  -> {n} (posiblemente cerrado o sin cartelera activa)")

        return total_fail == 0

    # ─── Orquestador principal ───

    def ejecutar(self):
        print("=" * 70)
        print("  WORKER MATILDE v7.0 (BLINDADO: PLAYWRIGHT + CURL_CFFI + FALLBACK)")
        print(f"  Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # FASE 1: Descubrimiento con Playwright
        self._fase1()

        # FASE 1.5: Fallback API-first para complejos faltantes
        self._fase15_fallback_api()

        # FASE 2: Descarga profunda de horarios
        self._fase2()

        # FASE 3: Validacion final
        cobertura_completa = self._fase3_validacion()

        return cobertura_completa


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTADOR (SQL + JSON + CSV)
# ═══════════════════════════════════════════════════════════════════════════

class ExportadorVisionWorker:
    def __init__(self, peliculas_cache, funciones):
        self.peliculas_cache = peliculas_cache
        self.funciones = funciones

    def guardar_sql(self, ruta="cartelera_vision_worker.sql"):
        ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "-- ============================================================",
            f"-- WORKER MATILDE v7.0 (BLINDADO) -- {ts_str}",
            "-- ============================================================\n",
            "BEGIN;\n"
        ]

        lines.append("-- -- 0. PREPARACION ARQUITECTONICA --")
        lines.append("ALTER TABLE PELICULA DROP CONSTRAINT IF EXISTS pelicula_vista_id_key;")
        lines.append("ALTER TABLE FUNCION ADD COLUMN IF NOT EXISTS activa BOOLEAN NOT NULL DEFAULT TRUE;")
        lines.append("ALTER TABLE FUNCION DROP CONSTRAINT IF EXISTS uq_funcion_logica;")
        lines.append("ALTER TABLE FUNCION ADD CONSTRAINT uq_funcion_logica UNIQUE (sala_id, fecha_funcion, hora_inicio);\n")
        lines.append("CREATE TEMP TABLE tmp_funciones_activas (complejo_slug VARCHAR, numero_sala INT, fecha DATE, hora_inicio TIME);\n")

        lines.append("-- -- 1. UPSERT PELICULAS ----")
        for mid, p in self.peliculas_cache.items():
            vista_id = p.get("vista_id") or mid
            cl = p.get("clasificacion", "A").replace("'", "''")
            if cl not in ['AA', 'A', 'B', 'B15', 'C']:
                cl = 'A'
            ge = p.get("genero", "").replace("'", "''")
            n = p.get("nombre", "").replace("'", "''")
            dur_str = str(p.get("duracion_min", "120"))
            dur = ''.join(filter(str.isdigit, dur_str)) or "120"
            cat = p.get("categoria", "Cartelera")

            def _sql_val(v):
                if not v:
                    return "NULL"
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

        lines.append("\n-- -- 2. SALAS Y FORMATOS (DO NOTHING) ---")
        salas_vistas = set()
        for f in self.funciones:
            clave_sala = (f["complejo_slug"], f["numero_sala"])
            if clave_sala not in salas_vistas:
                salas_vistas.add(clave_sala)
                infra_map = {
                    "Tradicional": "Tradicional",
                    "VIP": "VIP",
                    "Macro XE": "MACRO XE",
                    "XE": "MACRO XE",
                    "IMAX": "IMAX",
                    "4DX": "4DX",
                    "Junior": "Junior",
                    "SJ": "Junior",
                    "SP": "Tradicional",
                }
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

        lines.append("\n-- -- 3. UPSERT FUNCIONES Y REGISTRO TEMPORAL ----")
        for f in self.funciones:
            try:
                dt_obj = datetime.fromisoformat(f["datetime"])
                fecha = dt_obj.strftime("%Y-%m-%d")
                hora_raw = int(dt_obj.strftime("%H"))
                hora_correcta = hora_raw % 24
                hora_ini = f"{hora_correcta:02d}:{dt_obj.strftime('%M:%S')}"
                hora_fin = f"{(hora_raw + 2) % 24:02d}:{dt_obj.strftime('%M:%S')}"
            except Exception:
                continue

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

        lines.append("\n-- -- 4. RECOLECTOR DE BASURA (FAIL-SAFE) --")
        if len(self.funciones) < 500:
            lines.append("-- [FAIL-SAFE ACTIVADO]: Se extrajeron muy pocas funciones.")
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


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 70)
    print("  EXTRACTOR WORKER MATILDE v7.0 (BLINDADO)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    inicio = time.time()

    extractor = MatildeExtractorV7()
    cobertura_ok = extractor.ejecutar()

    if extractor.funciones:
        exportador = ExportadorVisionWorker(extractor.peliculas_cache, extractor.funciones)
        exportador.guardar_sql()
        exportador.guardar_json()
        exportador.guardar_csv()

        duracion = time.time() - inicio
        minutos = int(duracion // 60)
        segundos = int(duracion % 60)

        print(f"\n{'=' * 70}")
        print(f"  EXTRACCION COMPLETADA")
        print(f"  Funciones: {len(extractor.funciones)}")
        print(f"  Peliculas: {len(extractor.peliculas_cache)}")
        print(f"  Cobertura: {'19/19 COMPLETA' if cobertura_ok else 'PARCIAL (ver advertencias)'}")
        print(f"  Duracion: {minutos}m {segundos}s")
        print(f"{'=' * 70}")

        if extractor.modo_debug:
            print("  Revisa 'muestra_movie_node.json' para confirmar los nombres reales de campos.")
    else:
        print("\n  Fallo la extraccion. Cinepolis no devolvio horarios.")


if __name__ == "__main__":
    main()