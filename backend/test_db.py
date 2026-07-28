import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    res = conn.execute(text("""
        SELECT f.hora_inicio, p.titulo, s.numero_sala, fs.nombre_formato, f.activa, f.idioma
        FROM FUNCION f 
        JOIN PELICULA p ON f.pelicula_id = p.pelicula_id 
        JOIN SALA s ON f.sala_id = s.sala_id 
        JOIN COMPLEJO c ON s.complejo_id = c.complejo_id 
        JOIN FORMATO_SALA fs ON f.formato_id = fs.formato_id
        WHERE c.slug='cinepolis-acaya-coatzacoalcos' 
          AND f.fecha_funcion='2026-08-01' 
          AND p.titulo LIKE '%Spider%' 
        ORDER BY f.hora_inicio
    """)).fetchall()
    for r in res:
        print(r)
