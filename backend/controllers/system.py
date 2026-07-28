from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from core.database import get_db

router = APIRouter(tags=["Sistema"])

@router.get("/")
def ruta_raiz():
    return {
        "sistema": "J.A.R.V.I.S.", 
        "estado": "En línea", 
        "mensaje": "Bienvenido al núcleo del Proyecto Vision."
    }

@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        resultado = db.execute(text("SELECT COUNT(*) FROM PELICULA")).scalar()
        return {
            "conexion_bd": "OK",
            "mensaje": "Base de datos PostgreSQL conectada y respondiendo.",
            "total_peliculas_registradas": resultado
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando a BD: {str(e)}")
