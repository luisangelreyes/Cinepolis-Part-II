from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from services.marketing_service import get_banners, get_promociones

router = APIRouter(prefix="/api", tags=["Marketing y Banners"])

@router.get("/banners/{complejo_slug}")
def obtener_banners_complejo(complejo_slug: str, db: Session = Depends(get_db)):
    return get_banners(complejo_slug, db)

@router.get("/promociones/{complejo_slug}")
def obtener_promociones(complejo_slug: str, socio_id: Optional[int] = None, db: Session = Depends(get_db)):
    return get_promociones(complejo_slug, socio_id, db)
