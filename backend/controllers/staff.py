from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schemas.models import PersonalLoginRequest, AbrirSesionRequest, CerrarSesionRequest
from services.staff_service import login, abrir_sesion, obtener_corte, cerrar_sesion

router = APIRouter(prefix="/api", tags=["Personal y Caja"])

@router.post("/personal/login")
def login_personal(payload: PersonalLoginRequest, db: Session = Depends(get_db)):
    return login(payload, db)

@router.post("/sesiones/abrir")
def abrir_sesion_caja(payload: AbrirSesionRequest, db: Session = Depends(get_db)):
    return abrir_sesion(payload, db)

@router.get("/sesiones/{sesion_id}/corte")
def obtener_corte_caja(sesion_id: int, db: Session = Depends(get_db)):
    return obtener_corte(sesion_id, db)

@router.post("/sesiones/{sesion_id}/cerrar")
def cerrar_sesion_caja(sesion_id: int, payload: CerrarSesionRequest, db: Session = Depends(get_db)):
    return cerrar_sesion(sesion_id, payload, db)
