from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from schemas.models import SolicitarOTPRequest, VerificarOTPRequest, CanjearPuntosRequest
from services.club_service import request_otp, verify_otp, get_profile, get_movements, redeem_points
from services.marketing_service import get_promociones

router = APIRouter(prefix="/api", tags=["Autenticación y Club Cinépolis"])

@router.post("/auth/otp/solicitar")
def solicitar_otp(payload: SolicitarOTPRequest, db: Session = Depends(get_db)):
    return request_otp(payload, db)

@router.post("/auth/otp/verificar")
def verificar_otp(payload: VerificarOTPRequest, db: Session = Depends(get_db)):
    return verify_otp(payload, db)

@router.get("/club/{socio_id}")
def obtener_perfil_club(socio_id: int, db: Session = Depends(get_db)):
    return get_profile(socio_id, db)

@router.get("/club/{socio_id}/movimientos")
def obtener_movimientos_puntos(socio_id: int, limite: int = 20, db: Session = Depends(get_db)):
    return get_movements(socio_id, limite, db)

@router.post("/club/{socio_id}/canjear")
def canjear_puntos(socio_id: int, payload: CanjearPuntosRequest, db: Session = Depends(get_db)):
    return redeem_points(socio_id, payload, db)

@router.get("/promociones_club/{complejo_slug}")
def obtener_promociones(complejo_slug: str, socio_id: Optional[int] = None, db: Session = Depends(get_db)):
    return get_promociones(complejo_slug, socio_id, db)

