import urllib.request
import urllib.parse
import json
import time
import re
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:1234@localhost:5432/secret_wars"
TMDB_KEY = "097fd457526d3f04a7ee9a8cc001bf60"

def consultar_tmdb(titulo):
    clean = re.sub(r'^(TCF|HCF:|79 MIC|MIX)\s*', '', titulo, flags=re.IGNORECASE)
    clean = re.sub(r'\(.*?\)', '', clean)
    clean = clean.replace("Infinity Vision", "").replace("Bonus", "").replace("Trivia Night", "").strip()
    
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&language=es-MX&query={urllib.parse.quote(clean)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("results") or []
            if results:
                b = results[0]
                p = b.get("poster_path")
                bd = b.get("backdrop_path")
                return {
                    "poster_url": f"https://image.tmdb.org/t/p/w780{p}" if p else None,
                    "banner_url": f"https://image.tmdb.org/t/p/w1280{bd}" if bd else None,
                    "sinopsis": b.get("overview") or None
                }
    except Exception:
        pass
    return None

def main():
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        # Copy from base avengers to variants
        conn.execute(text("""
            UPDATE PELICULA v
            SET poster_url = b.poster_url, banner_url = b.banner_url
            FROM PELICULA b
            WHERE b.slug = 'avengers-doomsday' AND v.slug LIKE '%avengers-doomsday%' AND v.poster_url IS NULL;
        """))
        conn.execute(text("""
            UPDATE PELICULA v
            SET poster_url = b.poster_url, banner_url = b.banner_url
            FROM PELICULA b
            WHERE b.slug = 'avengers-endgame-bonus' AND v.slug LIKE '%avengers-endgame%' AND v.poster_url IS NULL;
        """))
        conn.execute(text("""
            UPDATE PELICULA v
            SET poster_url = b.poster_url, banner_url = b.banner_url
            FROM PELICULA b
            WHERE b.slug = 'bts-world-tour-arirang-in-buenos-aires' AND v.slug LIKE '%bts-world-tour%' AND v.poster_url IS NULL;
        """))

        pelis = conn.execute(text("SELECT pelicula_id, slug, titulo, poster_url, sinopsis FROM PELICULA WHERE poster_url IS NULL")).fetchall()
        for pid, slug, titulo, poster_url, sinopsis in pelis:
            datos = consultar_tmdb(titulo)
            if datos and datos.get("poster_url"):
                p_url = datos.get("poster_url")
                b_url = datos.get("banner_url")
                sin_nueva = datos.get("sinopsis") if (not sinopsis or len(sinopsis) < 30) else sinopsis
                conn.execute(
                    text("""
                        UPDATE PELICULA 
                        SET poster_url = :p,
                            banner_url = COALESCE(:b, banner_url),
                            sinopsis = COALESCE(:s, sinopsis)
                        WHERE pelicula_id = :pid
                    """),
                    {"p": p_url, "b": b_url, "s": sin_nueva, "pid": pid}
                )
                print(f"  [OK] {titulo} -> Poster OK")
            time.sleep(0.1)

if __name__ == "__main__":
    main()
