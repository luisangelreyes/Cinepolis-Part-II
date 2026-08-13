import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

def check_funcion(funcion_id):
    with engine.connect() as conn:
        print(f"--- REVISANDO FUNCIÓN {funcion_id} ---")
        
        # 1. Ver ASIENTO_PLANTILLA
        res = conn.execute(text("""
            SELECT DISTINCT ap.area_category_code, ap.tipo_asiento
            FROM FUNCION f
            JOIN SALA s ON f.sala_id = s.sala_id
            JOIN ASIENTO_PLANTILLA ap ON ap.sala_id = s.sala_id
            WHERE f.funcion_id = :fid
        """), {"fid": funcion_id}).fetchall()
        print(f"Áreas en ASIENTO_PLANTILLA para la sala: {res}")
        
        # 2. Ver PRECIO_BOLETO
        res = conn.execute(text("""
            SELECT pb.area_category_code, tb.nombre, pb.precio
            FROM FUNCION f
            JOIN PRECIO_BOLETO pb ON pb.complejo_id = (SELECT complejo_id FROM SALA WHERE sala_id = f.sala_id)
                AND pb.formato_id = f.formato_id
                AND pb.tipo_sala = (SELECT tipo_sala FROM SALA WHERE sala_id = f.sala_id)
            JOIN TIPO_BOLETO tb ON pb.tipo_boleto_id = tb.tipo_boleto_id
            WHERE f.funcion_id = :fid
        """), {"fid": funcion_id}).fetchall()
        print(f"Precios en PRECIO_BOLETO: {res}")

if __name__ == "__main__":
    # Get a random function ID that exists
    with engine.connect() as conn:
        f_id = conn.execute(text("SELECT funcion_id FROM FUNCION LIMIT 1")).scalar()
        if f_id:
            check_funcion(f_id)
