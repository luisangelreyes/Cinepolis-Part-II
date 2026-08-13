import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    # Contar total de ASIENTO_PLANTILLA y cuántos tienen area_category_code
    total = conn.execute(text("SELECT COUNT(*) FROM ASIENTO_PLANTILLA")).scalar()
    con_area = conn.execute(text("SELECT COUNT(*) FROM ASIENTO_PLANTILLA WHERE area_category_code IS NOT NULL")).scalar()
    
    print(f"Total asientos en plantilla: {total}")
    print(f"Asientos con area_category_code: {con_area}")
    
    # Revisar cuántas salas tienen codigos_area vacíos
    salas_total = conn.execute(text("SELECT COUNT(DISTINCT sala_id) FROM SALA")).scalar()
    salas_con_area = conn.execute(text("SELECT COUNT(DISTINCT sala_id) FROM ASIENTO_PLANTILLA WHERE area_category_code IS NOT NULL")).scalar()
    
    print(f"Total salas: {salas_total}")
    print(f"Salas con al menos un asiento con area_category_code: {salas_con_area}")
