import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
engine = create_engine(os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    print("Actualizando PRODUCTO_DULCERIA...")
    res1 = conn.execute(text("""
        UPDATE PRODUCTO_DULCERIA
        SET imagen_url = REPLACE(imagen_url, 'https://cinepolis.com', 'https://foods-static-content.cinepolis.com')
        WHERE imagen_url LIKE 'https://cinepolis.com%';
    """))
    print(f"[OK] {res1.rowcount} productos actualizados.")

    print("Actualizando MODIFICADOR_OPCION...")
    res2 = conn.execute(text("""
        UPDATE MODIFICADOR_OPCION
        SET imagen_url = REPLACE(imagen_url, 'https://cinepolis.com', 'https://foods-static-content.cinepolis.com')
        WHERE imagen_url LIKE 'https://cinepolis.com%';
    """))
    print(f"[OK] {res2.rowcount} opciones actualizadas.")
    
    conn.commit()
    print("[DONE] Todos los enlaces han sido actualizados.")
