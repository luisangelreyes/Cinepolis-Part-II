import json
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:1234@localhost:5432/secret_wars"
engine = create_engine(db_url)

with engine.connect() as conn:
    db_movies = [row[0] for row in conn.execute(text("SELECT titulo FROM PELICULA")).fetchall()]
    print(f"Total movies in DB: {len(db_movies)}")

with open('cartelera_veracruz_completa.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

json_movies = [p.get('nombre') for p in data.get('peliculas', [])]
print(f"Total movies in JSON: {len(json_movies)}")

print("In DB but not in JSON:", [m for m in db_movies if m not in json_movies][:5])
