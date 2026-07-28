from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from typing import Optional

router = APIRouter(prefix="/api", tags=["Películas y Cartelera"])

@router.get("/pelicula/{pelicula_id}")
def obtener_detalle_pelicula(pelicula_id: int, db: Session = Depends(get_db)):
    from services.movies_service import get_pelicula
    return get_pelicula(pelicula_id, db)

@router.get("/cartelera/{complejo_slug}")
def obtener_cartelera(complejo_slug: str, fecha: Optional[str] = None, db: Session = Depends(get_db)):
    from services.movies_service import get_cartelera
    return get_cartelera(complejo_slug, fecha, db)

@router.get("/funcion/{funcion_id}/asientos")
def obtener_asientos(funcion_id: int, db: Session = Depends(get_db)):
    from services.movies_service import get_asientos
    return get_asientos(funcion_id, db)

@router.get("/funcion/{funcion_id}/precios")
def obtener_precios_por_funcion(funcion_id: int, db: Session = Depends(get_db)):
    from services.movies_service import get_precios
    return get_precios(funcion_id, db)
