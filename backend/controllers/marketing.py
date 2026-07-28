from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from core.database import get_db

router = APIRouter(prefix="/api", tags=["Marketing y Banners"])

@router.get("/banners/{complejo_slug}")
def obtener_banners_complejo(complejo_slug: str, db: Session = Depends(get_db)):
    from services.marketing_service import get_banners
    return get_banners(complejo_slug, db)

@router.get("/promociones/{complejo_slug}")
def obtener_promociones(complejo_slug: str, socio_id: int = None, db: Session = Depends(get_db)):
    from services.marketing_service import get_promociones
    return get_promociones(complejo_slug, socio_id, db)
