import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

def check_junior():
    with engine.connect() as conn:
        # Encontrar una función en sala Junior
        f_id = conn.execute(text("""
            SELECT f.funcion_id, c.slug, s.numero_sala
            FROM FUNCION f
            JOIN SALA s ON f.sala_id = s.sala_id
            JOIN COMPLEJO c ON c.complejo_id = s.complejo_id
            WHERE s.tipo_sala = 'Junior'
            LIMIT 1
        """)).fetchone()
        
        if not f_id:
            print("No se encontraron funciones en sala Junior.")
            return
            
        print(f"--- REVISANDO FUNCIÓN JUNIOR {f_id[0]} (Complejo: {f_id[1]}, Sala: {f_id[2]}) ---")
        
        # 1. Ver ASIENTO_PLANTILLA
        res = conn.execute(text("""
            SELECT DISTINCT ap.area_category_code, ap.tipo_asiento
            FROM FUNCION f
            JOIN SALA s ON f.sala_id = s.sala_id
            JOIN ASIENTO_PLANTILLA ap ON ap.sala_id = s.sala_id
            WHERE f.funcion_id = :fid
        """), {"fid": f_id[0]}).fetchall()
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
        """), {"fid": f_id[0]}).fetchall()
        print(f"Precios en PRECIO_BOLETO para esta sala Junior: {res}")
        
        # 3. Ver qué retorna la query del backend real (simulando movies_service)
        codigos_area = {row[0] for row in res if row[0]}
        
        print(f"Códigos de área extraídos de ASIENTO_PLANTILLA: {codigos_area}")
        if codigos_area:
            pass # we know this logic
            
if __name__ == "__main__":
    check_junior()
