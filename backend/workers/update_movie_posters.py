import json
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:1234@localhost:5432/secret_wars"
engine = create_engine(db_url)

with open('cartelera_veracruz_completa.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extract a unique list of movies with their poster and banner urls
movies_dict = {}

for p in data.get('peliculas', []):
    movie_id = p.get('movie_id')
    poster_url = p.get('poster_url')
    banner_url = p.get('banner_url')
    trailer_url = p.get('trailer_url')
    
    if movie_id and movie_id not in movies_dict:
        movies_dict[movie_id] = {
            "poster": poster_url,
            "banner": banner_url,
            "trailer": trailer_url
        }

# Update database
updated_count = 0
with engine.begin() as conn:
    for slug, meta in movies_dict.items():
        if meta["poster"] or meta["banner"] or meta["trailer"]:
            res = conn.execute(
                text("UPDATE PELICULA SET poster_url = :p, banner_url = :b, trailer_url = :t WHERE slug = :s"),
                {"p": meta["poster"], "b": meta["banner"], "t": meta["trailer"], "s": slug}
            )
            updated_count += res.rowcount

print(f"Successfully updated {updated_count} movies with their poster, banner, and trailer URLs!")
