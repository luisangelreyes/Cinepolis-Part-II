import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# =================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# Las credenciales se cargan desde el archivo .env en la raíz del
# proyecto backend. Nunca pongas contraseñas directamente aquí.
# =================================================================
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "❌ Variable de entorno DATABASE_URL no encontrada. "
        "Asegúrate de tener un archivo .env con DATABASE_URL definida."
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependencia para inyectar la sesión de BD en cada petición
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
