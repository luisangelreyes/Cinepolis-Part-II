"""
Actualiza las peliculas en la base de datos PostgreSQL que actualmente no tienen poster_url o sinopsis,
utilizando la API de TMDB y los datos del catalogo de Cinepolis.
"""
import urllib.request
import urllib.parse
import json
import time
import sys
from sqlalchemy import create_engine, text

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DB_URL = "postgresql://postgres:1234@localhost:5432/secret_wars"
TMDB_KEY = "097fd457526d3f04a7ee9a8cc001bf60"

def consultar_tmdb(titulo):
    clean = titulo
    for prefix in ["Menú Temático:", "Menu Tematico:", "Trivia Night:", "Preventa:", "Clásico:", "Tour de Cine Francés:"]:
        clean = clean.replace(prefix, "")
    clean = clean.strip()
    
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
        pelis = conn.execute(text("SELECT pelicula_id, slug, titulo, poster_url, sinopsis FROM PELICULA WHERE poster_url IS NULL OR sinopsis IS NULL OR sinopsis LIKE 'Sinopsis autom%' OR sinopsis = 'Sin sinopsis disponible'")).fetchall()
        print(f"Total de peliculas a enriquecer en BD: {len(pelis)}")
        
        actualizadas = 0
        for pid, slug, titulo, poster_url, sinopsis in pelis:
            datos = consultar_tmdb(titulo)
            if datos and (datos.get("poster_url") or datos.get("sinopsis")):
                p_url = datos.get("poster_url") or poster_url
                b_url = datos.get("banner_url")
                
                # Usar sinopsis si la actual es nula, corta o automatica
                sin_nueva = sinopsis
                if not sinopsis or len(sinopsis) < 30 or "Sinopsis autom" in sinopsis or sinopsis == "Sin sinopsis disponible":
                    sin_nueva = datos.get("sinopsis") or sinopsis
                
                conn.execute(
                    text("""
                        UPDATE PELICULA 
                        SET poster_url = COALESCE(:p, poster_url),
                            banner_url = COALESCE(:b, banner_url),
                            sinopsis = COALESCE(:s, sinopsis)
                        WHERE pelicula_id = :pid
                    """),
                    {"p": p_url, "b": b_url, "s": sin_nueva, "pid": pid}
                )
                actualizadas += 1
                print(f"  ✓ [{actualizadas}] {titulo}: Poster={'SÍ' if p_url else 'NO'}, Sinopsis={'SÍ' if sin_nueva and len(sin_nueva)>20 else 'NO'}")
            time.sleep(0.1)

        print(f"\n¡Listo! {actualizadas} peliculas enriquecidas con portadas y sinopsis en la BD.")

if __name__ == "__main__":
    main()
