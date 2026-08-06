from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:1234@localhost:5432/secret_wars"
engine = create_engine(db_url)
with engine.connect() as conn:
    print(conn.execute(text("SELECT poster_url FROM PELICULA WHERE titulo ILIKE '%Backrooms%'")).fetchall())
