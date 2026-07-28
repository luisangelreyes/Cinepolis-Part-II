from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schemas.models import GarantiaReclamoRequest
from services.claims_service import process_reclamo

router = APIRouter(prefix="/api", tags=["Garantía y Reembolsos"])

@router.post("/garantia/reclamo")
def crear_reclamo(payload: GarantiaReclamoRequest, db: Session = Depends(get_db)):
    return process_reclamo(payload, db)
