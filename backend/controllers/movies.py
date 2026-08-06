from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from services.movies_service import get_pelicula, get_cartelera, get_asientos, get_precios, get_fechas_disponibles

router = APIRouter(prefix="/api", tags=["Películas y Cartelera"])

@router.get("/pelicula/{pelicula_id}")
def obtener_detalle_pelicula(pelicula_id: int, db: Session = Depends(get_db)):
    return get_pelicula(pelicula_id, db)

@router.get("/cartelera/{complejo_slug}")
def obtener_cartelera(complejo_slug: str, fecha: Optional[str] = None, db: Session = Depends(get_db)):
    return get_cartelera(complejo_slug, fecha, db)

@router.get("/cartelera/{complejo_slug}/fechas")
def obtener_fechas_cartelera(complejo_slug: str, db: Session = Depends(get_db)):
    return get_fechas_disponibles(complejo_slug, db)

@router.get("/funcion/{funcion_id}/asientos")
def obtener_asientos(funcion_id: int, db: Session = Depends(get_db)):
    return get_asientos(funcion_id, db)

@router.get("/funcion/{funcion_id}/precios")
def obtener_precios_por_funcion(funcion_id: int, db: Session = Depends(get_db)):
    return get_precios(funcion_id, db)

from fastapi import Response, HTTPException
import requests

@router.get("/proxy-image")
def proxy_image(url: str):
    if not url.startswith("https://tickets-static-content.cinepolis.com/") and not url.startswith("https://foods-static-content.cinepolis.com/"):
        raise HTTPException(status_code=400, detail="Invalid domain")
    
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            return Response(content=r.content, media_type=r.headers.get("content-type", "image/jpeg"))
        raise HTTPException(status_code=r.status_code, detail="Failed to fetch image")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
