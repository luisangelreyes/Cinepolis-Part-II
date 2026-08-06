from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:1234@localhost:5432/secret_wars"
engine = create_engine(db_url)

with engine.connect() as conn:
    result = conn.execute(text("SELECT slug, titulo, poster_url FROM PELICULA LIMIT 5")).fetchall()
    for row in result:
        print(row)
