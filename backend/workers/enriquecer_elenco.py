"""
=============================================================================
ENRIQUECEDOR DE ELENCO — TMDB v1.0
=============================================================================
Script independiente que toma las películas de la BD y las enriquece con
datos de TMDB (The Movie Database): director, actores y sinopsis en español.

REQUISITO: Obtén tu API Key GRATIS en https://www.themoviedb.org/settings/api
Luego ponla en la variable TMDB_API_KEY abajo.
=============================================================================
"""

import psycopg2
import urllib.request
import urllib.parse
import json
import time

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
TMDB_API_KEY = "TU_API_KEY_AQUI"   # ← Pon aquí tu API key de TMDB
DB_URL = "postgresql://postgres:1234@localhost:5432/secret_wars"
TMDB_BASE = "https://api.themoviedb.org/3"
# ──────────────────────────────────────────────────────────────────────────────


def tmdb_get(endpoint, params=None):
    """Hace una petición GET a TMDB y devuelve el JSON."""
    p = params or {}
    p["api_key"] = TMDB_API_KEY
    p["language"] = "es-MX"
    url = f"{TMDB_BASE}{endpoint}?{urllib.parse.urlencode(p)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"      ⚠️  Error TMDB: {e}")
        return {}


def buscar_pelicula_tmdb(titulo, anio=None):
    """Busca la película en TMDB y devuelve el primer resultado."""
    params = {"query": titulo}
    if anio:
        params["year"] = anio
    data = tmdb_get("/search/movie", params)
    resultados = data.get("results", [])
    return resultados[0] if resultados else None


def obtener_creditos_tmdb(tmdb_id):
    """Obtiene director y actores de TMDB por movie_id."""
    data = tmdb_get(f"/movie/{tmdb_id}/credits")
    director = None
    actores = []

    for persona in data.get("crew", []):
        if persona.get("job") == "Director":
            director = persona.get("name")
            break

    for persona in data.get("cast", [])[:6]:  # Top 6 actores
        actores.append(persona.get("name"))

    return director, actores


def obtener_sinopsis_tmdb(tmdb_id):
    """Obtiene sinopsis en español."""
    data = tmdb_get(f"/movie/{tmdb_id}")
    return data.get("overview", "")


def enriquecer_bd():
    print("═" * 60)
    print("  ENRIQUECEDOR DE ELENCO — TMDB v1.0")
    print("═" * 60)

    if TMDB_API_KEY == "TU_API_KEY_AQUI":
        print("\n❌ ERROR: No has configurado tu TMDB_API_KEY.")
        print("   1. Ve a https://www.themoviedb.org/settings/api")
        print("   2. Regístrate gratis y copia tu API Key (v3)")
        print("   3. Pégala en la variable TMDB_API_KEY de este script")
        return

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Obtener todas las películas de la BD
    cur.execute("SELECT pelicula_id, titulo, sinopsis FROM PELICULA ORDER BY titulo")
    peliculas = cur.fetchall()
    total = len(peliculas)

    print(f"\n  Se encontraron {total} películas en la BD\n")

    sql_lines = [
        "-- ============================================================",
        "-- ENRIQUECIMIENTO ELENCO TMDB — generado por enriquecer_elenco.py",
        "-- ============================================================",
        "",
        "BEGIN;",
        "",
        "-- Asegurar que existen las tablas necesarias",
        "CREATE TABLE IF NOT EXISTS PERSONA (",
        "  persona_id SERIAL PRIMARY KEY,",
        "  nombre VARCHAR(200) NOT NULL UNIQUE",
        ");",
        "CREATE TABLE IF NOT EXISTS PELICULA_PERSONA (",
        "  pelicula_id INT REFERENCES PELICULA(pelicula_id),",
        "  persona_id  INT REFERENCES PERSONA(persona_id),",
        "  rol         VARCHAR(50) NOT NULL,",
        "  UNIQUE(pelicula_id, persona_id, rol)",
        ");",
        ""
    ]

    for idx, (pelicula_id, titulo, sinopsis_actual) in enumerate(peliculas, 1):
        print(f"  [{idx:>2}/{total}] {titulo}")

        # Buscar en TMDB
        resultado = buscar_pelicula_tmdb(titulo)
        if not resultado:
            print(f"         ⚠️  No encontrada en TMDB")
            continue

        tmdb_id = resultado["id"]
        titulo_tmdb = resultado.get("title", titulo)
        print(f"         ✅ Match TMDB: {titulo_tmdb} (id: {tmdb_id})")

        # Obtener sinopsis si la BD no tiene una buena
        sinopsis_nueva = ""
        if not sinopsis_actual or len(sinopsis_actual) < 30:
            sinopsis_nueva = obtener_sinopsis_tmdb(tmdb_id)
            if sinopsis_nueva:
                sin_esc = sinopsis_nueva.replace("'", "''")
                sql_lines.append(f"UPDATE PELICULA SET sinopsis = '{sin_esc}' WHERE pelicula_id = {pelicula_id};")
                print(f"         📝 Sinopsis actualizada ({len(sinopsis_nueva)} chars)")

        # Obtener elenco
        director, actores = obtener_creditos_tmdb(tmdb_id)
        if director:
            print(f"         🎬 Director: {director}")
        if actores:
            print(f"         👥 Actores: {', '.join(actores[:3])}...")

        # Insertar director en SQL
        if director:
            dir_esc = director.replace("'", "''")
            sql_lines.append(f"INSERT INTO PERSONA (nombre) VALUES ('{dir_esc}') ON CONFLICT (nombre) DO NOTHING;")
            sql_lines.append(
                f"INSERT INTO PELICULA_PERSONA (pelicula_id, persona_id, rol) "
                f"SELECT {pelicula_id}, persona_id, 'Director' FROM PERSONA WHERE nombre = '{dir_esc}' "
                f"ON CONFLICT DO NOTHING;"
            )

        # Insertar actores en SQL
        for actor in actores:
            act_esc = actor.replace("'", "''")
            sql_lines.append(f"INSERT INTO PERSONA (nombre) VALUES ('{act_esc}') ON CONFLICT (nombre) DO NOTHING;")
            sql_lines.append(
                f"INSERT INTO PELICULA_PERSONA (pelicula_id, persona_id, rol) "
                f"SELECT {pelicula_id}, persona_id, 'Actor' FROM PERSONA WHERE nombre = '{act_esc}' "
                f"ON CONFLICT DO NOTHING;"
            )

        sql_lines.append("")
        time.sleep(0.3)  # Ser amables con la API de TMDB

    sql_lines.append("COMMIT;")

    # Guardar el SQL generado
    sql_out = "elenco_tmdb.sql"
    with open(sql_out, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    print(f"\n  ✅ Archivo SQL guardado: {sql_out}")
    print(f"  📌 Ejecuta ese archivo en tu BD para actualizar el elenco.")
    print(f"     O corre directamente con psql:")
    print(f"     psql -U postgres -d secret_wars -f {sql_out}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    enriquecer_bd()
