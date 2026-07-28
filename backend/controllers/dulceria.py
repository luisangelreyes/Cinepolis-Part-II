from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from services.dulceria_service import get_catalogo

router = APIRouter(prefix="/api", tags=["Dulcería"])

@router.get("/dulceria/{complejo_slug}")
def obtener_catalogo_dulceria(complejo_slug: str, db: Session = Depends(get_db)):
    return get_catalogo(complejo_slug, db)
