import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from services.movies_service import get_precios

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_endpoint(funcion_id):
    db = SessionLocal()
    try:
        res = get_precios(funcion_id, db)
        print(f"Precios devueltos para funcion {funcion_id}:")
        for tarifa in res["tarifas"]:
            print(f"  - {tarifa['tipo_boleto']} (${tarifa['precio']}) [Area: {tarifa['area_code']}]")
    finally:
        db.close()

if __name__ == "__main__":
    from scripts.db_utils.check_query import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        # Check an normal function
        f_id = conn.execute(text("SELECT f.funcion_id FROM FUNCION f JOIN SALA s ON s.sala_id=f.sala_id WHERE s.tipo_sala = 'Tradicional' LIMIT 1")).scalar()
        if f_id:
            test_endpoint(f_id)
        
        # Check a junior function
        f_id2 = conn.execute(text("SELECT f.funcion_id FROM FUNCION f JOIN SALA s ON s.sala_id=f.sala_id WHERE s.tipo_sala = 'Junior' LIMIT 1")).scalar()
        if f_id2:
            test_endpoint(f_id2)
