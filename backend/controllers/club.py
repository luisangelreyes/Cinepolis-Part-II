from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schemas.models import SolicitarOTPRequest, VerificarOTPRequest, CanjearPuntosRequest
from typing import Optional

router = APIRouter(prefix="/api", tags=["Autenticación y Club Cinépolis"])

@router.post("/auth/otp/solicitar")
def solicitar_otp(payload: SolicitarOTPRequest, db: Session = Depends(get_db)):
    from services.club_service import request_otp
    return request_otp(payload, db)

@router.post("/auth/otp/verificar")
def verificar_otp(payload: VerificarOTPRequest, db: Session = Depends(get_db)):
    from services.club_service import verify_otp
    return verify_otp(payload, db)

@router.get("/club/{socio_id}")
def obtener_perfil_club(socio_id: int, db: Session = Depends(get_db)):
    from services.club_service import get_profile
    return get_profile(socio_id, db)

@router.get("/club/{socio_id}/movimientos")
def obtener_movimientos_puntos(socio_id: int, limite: int = 20, db: Session = Depends(get_db)):
    from services.club_service import get_movements
    return get_movements(socio_id, limite, db)

@router.post("/club/{socio_id}/canjear")
def canjear_puntos(socio_id: int, payload: CanjearPuntosRequest, db: Session = Depends(get_db)):
    from services.club_service import redeem_points
    return redeem_points(socio_id, payload, db)

@router.get("/promociones_club/{complejo_slug}")
def obtener_promociones(complejo_slug: str, socio_id: Optional[int] = None, db: Session = Depends(get_db)):
    from services.marketing_service import get_promociones
    return get_promociones(complejo_slug, socio_id, db)
