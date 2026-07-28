from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schemas.models import CrearCarritoRequest, AgregarAsientoRequest, AgregarProductoRequest, PagarCarritoRequest

router = APIRouter(prefix="/api", tags=["Carrito y Transacción"])

@router.post("/carrito")
def crear_carrito(payload: CrearCarritoRequest, db: Session = Depends(get_db)):
    from services.cart_service import create_cart
    return create_cart(payload, db)

@router.get("/carrito/{carrito_id}")
def obtener_carrito(carrito_id: int, db: Session = Depends(get_db)):
    from services.cart_service import get_cart
    return get_cart(carrito_id, db)

@router.post("/carrito/{carrito_id}/asientos")
def agregar_asiento_carrito(carrito_id: int, payload: AgregarAsientoRequest, db: Session = Depends(get_db)):
    from services.cart_service import add_seat
    return add_seat(carrito_id, payload, db)

@router.post("/carrito/{carrito_id}/productos")
def agregar_producto_carrito(carrito_id: int, payload: AgregarProductoRequest, db: Session = Depends(get_db)):
    from services.cart_service import add_product
    return add_product(carrito_id, payload, db)

@router.delete("/carrito/{carrito_id}/items/{detalle_carrito_id}")
def eliminar_item_carrito(carrito_id: int, detalle_carrito_id: int, db: Session = Depends(get_db)):
    from services.cart_service import remove_item
    return remove_item(carrito_id, detalle_carrito_id, db)

@router.post("/carrito/{carrito_id}/abandonar")
def abandonar_carrito(carrito_id: int, db: Session = Depends(get_db)):
    from services.cart_service import abandon_cart
    return abandon_cart(carrito_id, db)

@router.post("/carrito/{carrito_id}/pagar")
def pagar_carrito(carrito_id: int, payload: PagarCarritoRequest, db: Session = Depends(get_db)):
    from services.cart_service import pay_cart
    return pay_cart(carrito_id, payload, db)
