"""
Aplica el elenco directamente desde TMDB a la BD usando inserciones parametrizadas.
"""
import psycopg2
import urllib.request
import urllib.parse
import json
import time

TMDB_API_KEY = "097fd457526d3f04a7ee9a8cc001bf60"
DB_URL = "postgresql://postgres:1234@localhost:5432/secret_wars"
TMDB_BASE = "https://api.themoviedb.org/3"

def tmdb_get(endpoint, params=None):
    p = params or {}
    p["api_key"] = TMDB_API_KEY
    p["language"] = "es-MX"
    url = f"{TMDB_BASE}{endpoint}?{urllib.parse.urlencode(p)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except:
        return {}

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# ── 0. Asegurar constraints únicos ──────────────────────────────────
print("Verificando constraints...")
cur.execute("""
    SELECT constraint_name FROM information_schema.table_constraints
    WHERE table_name = 'persona' AND constraint_name = 'uq_persona_nombre'
""")
if not cur.fetchone():
    cur.execute("ALTER TABLE PERSONA ADD CONSTRAINT uq_persona_nombre UNIQUE (nombre)")
    conn.commit()
    print("  ✅ UNIQUE en PERSONA(nombre) creado")

cur.execute("""
    SELECT constraint_name FROM information_schema.table_constraints
    WHERE table_name = 'pelicula_persona' AND constraint_name = 'uq_pel_per_rol'
""")
if not cur.fetchone():
    cur.execute("ALTER TABLE PELICULA_PERSONA ADD CONSTRAINT uq_pel_per_rol UNIQUE (pelicula_id, persona_id, rol)")
    conn.commit()
    print("  ✅ UNIQUE en PELICULA_PERSONA creado")

# ── 1. Obtener películas de la BD ───────────────────────────────────
cur.execute("SELECT pelicula_id, titulo, sinopsis FROM PELICULA ORDER BY titulo")
peliculas = cur.fetchall()
total = len(peliculas)
print(f"\nPelículas en BD: {total}")
print("Procesando...\n")

sin_match = 0

def insertar_persona(nombre):
    """Inserta persona y retorna su persona_id."""
    cur.execute(
        "INSERT INTO PERSONA (nombre) VALUES (%s) ON CONFLICT ON CONSTRAINT uq_persona_nombre DO NOTHING",
        (nombre,)
    )
    conn.commit()
    cur.execute("SELECT persona_id FROM PERSONA WHERE nombre = %s", (nombre,))
    row = cur.fetchone()
    return row[0] if row else None

def insertar_relacion(pelicula_id, persona_id, rol):
    cur.execute(
        "INSERT INTO PELICULA_PERSONA (pelicula_id, persona_id, rol) VALUES (%s, %s, %s) ON CONFLICT ON CONSTRAINT uq_pel_per_rol DO NOTHING",
        (pelicula_id, persona_id, rol)
    )
    conn.commit()

for idx, (pelicula_id, titulo, sinopsis_actual) in enumerate(peliculas, 1):
    data = tmdb_get("/search/movie", {"query": titulo})
    resultados = data.get("results", [])
    if not resultados:
        sin_match += 1
        continue

    tmdb_id = resultados[0]["id"]
    titulo_tmdb = resultados[0].get("title", titulo)
    print(f"  [{idx:>2}/{total}] ✅ {titulo} → {titulo_tmdb}")

    # Sinopsis si falta
    if not sinopsis_actual or len(str(sinopsis_actual)) < 30:
        det = tmdb_get(f"/movie/{tmdb_id}")
        sinopsis = det.get("overview", "")
        if sinopsis:
            cur.execute("UPDATE PELICULA SET sinopsis = %s WHERE pelicula_id = %s", (sinopsis, pelicula_id))
            conn.commit()

    # Créditos
    cred = tmdb_get(f"/movie/{tmdb_id}/credits")

    # Director
    for persona in cred.get("crew", []):
        if persona.get("job") == "Director":
            pid = insertar_persona(persona["name"])
            if pid:
                insertar_relacion(pelicula_id, pid, "director")
            break

    # Actores top 6
    for persona in cred.get("cast", [])[:6]:
        pid = insertar_persona(persona["name"])
        if pid:
            insertar_relacion(pelicula_id, pid, "actor")

    time.sleep(0.25)

# ── Resultado final ──────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) FROM PERSONA")
print(f"\n✅ Personas en BD:   {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM PELICULA_PERSONA WHERE rol = 'director'")
print(f"   Directores:       {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM PELICULA_PERSONA WHERE rol = 'actor'")
print(f"   Actores:          {cur.fetchone()[0]}")
print(f"   Sin match TMDB:   {sin_match}/{total}")

print("\n  Muestra:")
cur.execute("""
    SELECT p.titulo, per.nombre, pp.rol
    FROM PELICULA_PERSONA pp
    JOIN PELICULA p ON p.pelicula_id = pp.pelicula_id
    JOIN PERSONA per ON per.persona_id = pp.persona_id
    ORDER BY p.titulo, pp.rol DESC LIMIT 20
""")
for row in cur.fetchall():
    print(f"  [{row[2]:<8}] {row[1]:30} → {row[0]}")

cur.close()
conn.close()
