"""
=============================================================================
EXTRACTOR CINÉPOLIS VERACRUZ — v3 (Unificado)
=============================================================================
Flujo en dos fases:

  FASE 1 — Playwright (browser real)
    • Abre cada complejo en un browser visible para pasar Cloudflare
    • Intercepta respuestas GraphQL para obtener la lista de películas
      y sus IDs (movie_id) por complejo

  FASE 2 — curl_cffi (API directa)
    • Por cada película+complejo encontrado en Fase 1, consulta la API
      de horarios detallados
    • Obtiene formato, idioma, experiencia, sala y sessionId reales

  EXPORTACIÓN
    • cartelera_veracruz_completa.json
    • cartelera_veracruz_completa.csv
    • cartelera_veracruz_completa.sql  ← INSERTs para PELICULA, COMPLEJO, FUNCION

Dependencias:
  pip install playwright curl_cffi
  playwright install chromium
=============================================================================
"""

import json
import csv
import time
from datetime import datetime

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

COUNTRY_ID = "MX"
PAUSA_ENTRE_COMPLEJOS = 10  # segundos entre complejos en Fase 1
PAUSA_ENTRE_REQUESTS  = 10   # segundos entre requests en Fase 2

API_URL = "https://api-g.cinepolis.com/v1/billboards/graphql"
API_HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "country-id": "MX",
    "language": "ES",
    "origin": "https://cinepolis.com",
    "referer": "https://cinepolis.com/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
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
    dates
    schedules {
      cinemaId
      cityId
      movieId
      dates {
        date
        languages {
          language
          displayLanguage
          showtimes {
            format { icon name __typename }
            sessionId
            datetime
            screen
            experience { icon name __typename }
            movieVistaId
            cinemaVistaId
            alerts { section title message __typename }
            availability
            isAllocatedSeating
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

COMPLEJOS = [
    {"nombre": "Acaya Coatzacoalcos",      "slug": "cinepolis-acaya-coatzacoalcos"},
    {"nombre": "El Dorado Coatzacoalcos",  "slug": "cinepolis-el-dorado-coatzacoalcos"},
    {"nombre": "El Dorado Veracruz",       "slug": "cinepolis-el-dorado-veracruz"},
    {"nombre": "VIP El Dorado Veracruz",   "slug": "cinepolis-vip-el-dorado-veracruz"},
    {"nombre": "Plaza del Puerto Veracruz","slug": "cinepolis-plaza-del-puerto-veracruz"},
    {"nombre": "VIP Las Américas Veracruz","slug": "cinepolis-vip-las-americas-veracruz"},
    {"nombre": "Portal Veracruz",          "slug": "cinepolis-portal-veracruz"},
    {"nombre": "Plaza Las Américas Xalapa","slug": "cinepolis-plaza-las-americas-xalapa"},
    {"nombre": "VIP Las Américas Xalapa",  "slug": "cinepolis-vip-las-americas-xalapa"},
    {"nombre": "Plaza Crystal Xalapa",     "slug": "cinepolis-plaza-crystal-xalapa"},
    {"nombre": "Plaza Museo Xalapa",       "slug": "cinepolis-plaza-museo-xalapa"},
    {"nombre": "Plaza Shangri La Córdoba", "slug": "cinepolis-plaza-shangri-la-cordoba"},
    {"nombre": "Plaza Valle Orizaba",      "slug": "cinepolis-plaza-valle-orizaba"},
    {"nombre": "Río Blanco Orizaba",       "slug": "cinepolis-rio-blanco-orizaba"},
    {"nombre": "Plaza Minatitlán",         "slug": "cinepolis-plaza-minatitlan"},
    {"nombre": "Plaza Crystal Tuxpan",     "slug": "cinepolis-plaza-crystal-tuxpan"},
    {"nombre": "La Florida Acayucan",      "slug": "cinepolis-la-florida-acayucan"},
]


# ─── FASE 1: PLAYWRIGHT ────────────────────────────────────────────────────────

class Fase1_Playwright:
    """
    Navega a cada complejo con un browser real y captura:
      - peliculas_cache: {movie_id → datos de película}
      - pares_complejo_pelicula: lista de {complejo_slug, complejo_nombre, movie_id, categoria}
    """

    def __init__(self):
        self.peliculas_cache        = {}   # movie_id → dict con datos de película
        self.pares_complejo_pelicula = []  # [{complejo_slug, complejo_nombre, movie_id, categoria}]

    def _procesar_respuesta(self, body, slug, nombre):
        data = body.get("data", {})

        # ── Películas ──────────────────────────────────────────────────────────
        movies_data = data.get("movies", {})
        if movies_data:
            for edge in movies_data.get("edges", []):
                node = edge.get("node", {})
                mid  = node.get("id")
                if mid and mid not in self.peliculas_cache:
                    genero_crudo = node.get("genre", "")
                    self.peliculas_cache[mid] = {
                        "movie_id":      mid,
                        "nombre":        node.get("name", ""),
                        "nombre_orig":   node.get("originalName", ""),
                        "clasificacion": node.get("rating", ""),
                        "genero":        (
                            ", ".join(genero_crudo)
                            if isinstance(genero_crudo, list)
                            else str(genero_crudo)
                        ),
                        "duracion_min":  node.get("length", 0) or 0,
                        "fecha_estreno": node.get("releaseDate", ""),
                    }

        # ── Pares complejo-película ────────────────────────────────────────────
        billboard = data.get("billboardByCinema", {})
        if billboard:
            schedules = billboard.get("schedules", [])
            vistos = set()
            for sched in schedules:
                mid       = sched.get("movieId", "")
                categoria = sched.get("category", "")
                clave     = (slug, mid)
                if clave not in vistos and mid:
                    vistos.add(clave)
                    self.pares_complejo_pelicula.append({
                        "complejo_slug":   slug,
                        "complejo_nombre": nombre,
                        "movie_id":        mid,
                        "categoria":       categoria,
                    })

    def _extraer_complejo(self, page, complejo):
        nombre = complejo["nombre"]
        slug   = complejo["slug"]
        url    = f"https://cinepolis.com/mx?cinema={slug}"

        respuestas_capturadas = []

        def on_response(response):
            if "billboards/graphql" in response.url:
                try:
                    body = response.json()
                    respuestas_capturadas.append(body)
                    print(f"    [OK] GraphQL capturado")
                except Exception as e:
                    print(f"    [WARN] No se pudo parsear: {e}")

        page.on("response", on_response)
        print(f"\n▶ {nombre}")

        try:
            page.goto(url, wait_until="networkidle", timeout=40000)
        except Exception as e:
            print(f"  [TIMEOUT] {e} — usando lo capturado hasta ahora")

        time.sleep(3)
        page.remove_listener("response", on_response)

        if not respuestas_capturadas:
            print(f"  [WARN] Sin respuestas GraphQL para {nombre}")
            return

        for body in respuestas_capturadas:
            self._procesar_respuesta(body, slug, nombre)

        pares_este = sum(
            1 for p in self.pares_complejo_pelicula
            if p["complejo_slug"] == slug
        )
        print(f"  [OK] {pares_este} películas detectadas")

    def ejecutar(self):
        from playwright.sync_api import sync_playwright

        print("═" * 60)
        print("  FASE 1 — Playwright: captura de películas por complejo")
        print("═" * 60)
        print("  Se abrirá un browser. No lo cierres.\n")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                locale="es-MX",
                timezone_id="America/Mexico_City",
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            print("[INIT] Visitando cinepolis.com para establecer sesión CF...\n")
            page.goto("https://cinepolis.com", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            for complejo in COMPLEJOS:
                try:
                    page.evaluate(
                        "window.localStorage.clear(); window.sessionStorage.clear();"
                    )
                except:
                    pass
                self._extraer_complejo(page, complejo)
                time.sleep(PAUSA_ENTRE_COMPLEJOS)

            browser.close()

        print(f"\n{'═'*60}")
        print(f"  Películas únicas encontradas : {len(self.peliculas_cache)}")
        print(f"  Pares complejo-película      : {len(self.pares_complejo_pelicula)}")
        print(f"{'═'*60}\n")


# ─── FASE 2: API DIRECTA ───────────────────────────────────────────────────────

class Fase2_API:
    """
    Para cada par (complejo, película) hallado en Fase 1,
    consulta la API de horarios y construye la lista completa de funciones.
    """

    def __init__(self, peliculas_cache, pares):
        self.peliculas_cache = peliculas_cache
        self.pares           = pares
        self.funciones       = []   # lista final de funciones completas

    def _consultar(self, movie_id, complejo_slug, complejo_nombre, categoria):
        from curl_cffi import requests as cffi_requests

        payload = {
            "operationName": "Billboard",
            "variables": {
                "movieId":   movie_id,
                "cinemas":   complejo_slug,
                "countryId": COUNTRY_ID,
                "timezone":  "America/Mexico_City",
            },
            "query": GRAPHQL_QUERY,
        }

        try:
            response = cffi_requests.post(
                API_URL,
                json=payload,
                headers=API_HEADERS,
                impersonate="chrome110",
                timeout=15,
            )
        except Exception as e:
            print(f"    ❌ Excepción de red: {e}")
            return

        if response.status_code != 200:
            print(f"    ❌ HTTP {response.status_code}")
            return

        data      = response.json().get("data", {})
        billboard = data.get("billboard", {})
        schedules = billboard.get("schedules", [])
        pelicula  = self.peliculas_cache.get(movie_id, {})

        for schedule in schedules:
            for day in schedule.get("dates", []):
                for lang in day.get("languages", []):
                    idioma_display = lang.get("displayLanguage", "")
                    for show in lang.get("showtimes", []):
                        formato_data = show.get("format")  or {}
                        exp_data     = show.get("experience") or {}
                        self.funciones.append({
                            "complejo_slug":   complejo_slug,
                            "complejo_nombre": complejo_nombre,
                            "session_id":      show.get("sessionId", ""),
                            "cinema_vista_id": show.get("cinemaVistaId", ""),
                            "datetime":        show.get("datetime", ""),
                            "sala":            show.get("screen", ""),
                            "formato":         formato_data.get("name", "Estándar"),
                            "idioma":          idioma_display,
                            "experiencia":     exp_data.get("name", "Tradicional"),
                            "categoria":       categoria,
                            "movie_id":        movie_id,
                            "movie_vista_id":  show.get("movieVistaId", ""),
                            "pelicula_nombre": pelicula.get("nombre", ""),
                            "pelicula_orig":   pelicula.get("nombre_orig", ""),
                            "clasificacion":   pelicula.get("clasificacion", ""),
                            "genero":          pelicula.get("genero", ""),
                            "duracion_min":    pelicula.get("duracion_min", ""),
                            "fecha_estreno":   pelicula.get("fecha_estreno", ""),
                        })

    def ejecutar(self):
        total = len(self.pares)
        print("═" * 60)
        print("  FASE 2 — API: consulta de horarios detallados")
        print(f"  Total de consultas a realizar: {total}")
        print("═" * 60)

        for i, par in enumerate(self.pares, 1):
            nombre_peli = self.peliculas_cache.get(
                par["movie_id"], {}
            ).get("nombre", par["movie_id"])
            print(
                f"  [{i:>3}/{total}] {par['complejo_nombre']} — {nombre_peli}"
            )
            self._consultar(
                par["movie_id"],
                par["complejo_slug"],
                par["complejo_nombre"],
                par["categoria"],
            )
            time.sleep(PAUSA_ENTRE_REQUESTS)

        print(f"\n{'═'*60}")
        print(f"  TOTAL FUNCIONES OBTENIDAS: {len(self.funciones)}")
        print(f"{'═'*60}\n")


# ─── EXPORTACIÓN ──────────────────────────────────────────────────────────────

class Exportador:
    def __init__(self, peliculas_cache, funciones):
        self.peliculas_cache = peliculas_cache
        self.funciones       = funciones

    def guardar_json(self, ruta="cartelera_veracruz_completa.json"):
        salida = {
            "generado":        datetime.now().isoformat(),
            "total_funciones": len(self.funciones),
            "peliculas":       list(self.peliculas_cache.values()),
            "funciones":       self.funciones,
        }
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(salida, f, ensure_ascii=False, indent=2)
        print(f"  [JSON] {ruta}  ({len(self.funciones)} funciones)")

    def guardar_csv(self, ruta="cartelera_veracruz_completa.csv"):
        if not self.funciones:
            print("  [CSV] Sin datos.")
            return
        with open(ruta, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.funciones[0].keys())
            writer.writeheader()
            writer.writerows(self.funciones)
        print(f"  [CSV] {ruta}  ({len(self.funciones)} filas)")

    def guardar_sql(self, ruta="cartelera_veracruz_completa.sql"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            "-- ============================================================",
            "-- INSERTS CARTELERA CINÉPOLIS VERACRUZ — Proyecto Secret Wars",
            f"-- Generado: {ts}",
            "-- ============================================================\n",
        ]

        # ── PELICULA ──────────────────────────────────────────────────────────
        lines.append("-- ── TABLA: PELICULA ──────────────────────────────────────────\n")
        for mid, p in self.peliculas_cache.items():
            n  = p.get("nombre",      "").replace("'", "''")
            no = p.get("nombre_orig", "").replace("'", "''")
            cl = p.get("clasificacion","").replace("'", "''")
            ge = p.get("genero",      "").replace("'", "''")
            du = str(p.get("duracion_min", 0) or 0)
            es = p.get("fecha_estreno", "")
            es_sql = f"'{es}'" if es else "NULL"
            lines.append(
                f"INSERT INTO PELICULA "
                f"(id_pelicula, nombre, nombre_original, clasificacion, genero, duracion_min, fecha_estreno) "
                f"VALUES ('{mid}', '{n}', '{no}', '{cl}', '{ge}', {du}, {es_sql});"
            )

        # ── COMPLEJO ──────────────────────────────────────────────────────────
        lines.append("\n-- ── TABLA: COMPLEJO ──────────────────────────────────────────\n")
        slugs_vistos = set()
        for f in self.funciones:
            s = f["complejo_slug"]
            if s in slugs_vistos:
                continue
            slugs_vistos.add(s)
            n = f["complejo_nombre"].replace("'", "''")
            lines.append(
                f"INSERT INTO COMPLEJO (slug, nombre_comercial) "
                f"VALUES ('{s}', '{n}');"
            )

        # ── FUNCION ───────────────────────────────────────────────────────────
        lines.append("\n-- ── TABLA: FUNCION ───────────────────────────────────────────\n")
        for f in self.funciones:
            sid = f["session_id"].replace("'", "''")
            dt  = f["datetime"]
            lines.append(
                f"INSERT INTO FUNCION "
                f"(session_id, complejo_slug, movie_id, datetime, sala, formato, idioma, experiencia) "
                f"VALUES ('{sid}', '{f['complejo_slug']}', '{f['movie_id']}', "
                f"'{dt}', '{f['sala']}', '{f['formato']}', "
                f"'{f['idioma']}', '{f['experiencia']}');"
            )

        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  [SQL] {ruta}  ({len(self.funciones)} INSERTs FUNCION)")

    def ejecutar(self):
        print("═" * 60)
        print("  EXPORTANDO ARCHIVOS")
        print("═" * 60)
        self.guardar_json()
        self.guardar_csv()
        self.guardar_sql()
        print(f"\n✓ Archivos generados:")
        print("  • cartelera_veracruz_completa.json")
        print("  • cartelera_veracruz_completa.csv")
        print("  • cartelera_veracruz_completa.sql")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 60)
    print("  EXTRACTOR CINÉPOLIS VERACRUZ — v3 (Unificado)")
    print("═" * 60 + "\n")

    # ── Fase 1: Playwright ────────────────────────────────────────────────────
    fase1 = Fase1_Playwright()
    fase1.ejecutar()

    if not fase1.pares_complejo_pelicula:
        print("\n[ERROR] Fase 1 no encontró películas.")
        print("  Verifica conexión o resuelve el captcha de Cloudflare manualmente.")
        return

    # ── Fase 2: API directa ───────────────────────────────────────────────────
    fase2 = Fase2_API(fase1.peliculas_cache, fase1.pares_complejo_pelicula)
    fase2.ejecutar()

    if not fase2.funciones:
        print("\n[ERROR] Fase 2 no obtuvo funciones.")
        print("  Revisa la API key o la estructura de la respuesta.")
        return

    # ── Exportar ──────────────────────────────────────────────────────────────
    exportador = Exportador(fase1.peliculas_cache, fase2.funciones)
    exportador.ejecutar()

    print("\n" + "═" * 60)
    print(f"  Películas únicas : {len(fase1.peliculas_cache)}")
    print(f"  Funciones totales: {len(fase2.funciones)}")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    main()