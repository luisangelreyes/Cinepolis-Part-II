from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from datetime import datetime, timedelta
from schemas.models import CrearCarritoRequest, AgregarAsientoRequest, AgregarProductoRequest, PagarCarritoRequest

def _validar_carrito_activo(db: Session, carrito_id: int):
    carrito = db.execute(text("SELECT carrito_id, estado, fecha_expiracion, socio_id, sesion_id FROM CARRITO WHERE carrito_id = :cid FOR UPDATE"), {"cid": carrito_id}).fetchone()
    if not carrito: raise HTTPException(status_code=404, detail="Carrito no encontrado.")
    if carrito.estado != 'activo': raise HTTPException(status_code=400, detail=f"El carrito ya está '{carrito.estado}', no admite más operaciones.")
    if carrito.fecha_expiracion < datetime.now():
        db.execute(text("UPDATE ASIENTO SET estado = 'disponible' WHERE asiento_id IN (SELECT asiento_id FROM DETALLE_CARRITO WHERE carrito_id = :cid AND asiento_id IS NOT NULL)"), {"cid": carrito_id})
        db.execute(text("UPDATE CARRITO SET estado = 'abandonado' WHERE carrito_id = :cid"), {"cid": carrito_id})
        db.commit()
        raise HTTPException(status_code=400, detail="El carrito expiró y sus asientos fueron liberados. Crea uno nuevo.")
    return carrito

def create_cart(payload: CrearCarritoRequest, db: Session):
    fecha_creacion = datetime.now()
    fecha_expiracion = fecha_creacion + timedelta(minutes=15)
    resultado = db.execute(text("""
        INSERT INTO CARRITO (fecha_creacion, fecha_expiracion, estado, sesion_id, socio_id)
        VALUES (:fc, :fe, 'activo', :sesion_id, :socio_id) RETURNING carrito_id
    """), {"fc": fecha_creacion, "fe": fecha_expiracion, "sesion_id": payload.sesion_id, "socio_id": payload.socio_id}).fetchone()
    db.commit()
    return {"carrito_id": resultado.carrito_id, "fecha_creacion": fecha_creacion, "fecha_expiracion": fecha_expiracion}

def get_cart(carrito_id: int, db: Session):
    carrito = db.execute(text("SELECT carrito_id, estado, fecha_creacion, fecha_expiracion, socio_id FROM CARRITO WHERE carrito_id = :cid"), {"cid": carrito_id}).fetchone()
    if not carrito: raise HTTPException(status_code=404, detail="Carrito no encontrado.")
    items = db.execute(text("SELECT detalle_carrito_id, tipo_item, cantidad, precio_unitario, asiento_id, producto_id, tipo_boleto_id FROM DETALLE_CARRITO WHERE carrito_id = :cid ORDER BY detalle_carrito_id"), {"cid": carrito_id}).fetchall()
    subtotal = sum(float(i.precio_unitario) * i.cantidad for i in items)
    return {"carrito_id": carrito_id, "estado": carrito.estado, "fecha_expiracion": carrito.fecha_expiracion, "items": [dict(i._mapping) for i in items], "subtotal": subtotal}

def add_seat(carrito_id: int, payload: AgregarAsientoRequest, db: Session):
    try:
        _validar_carrito_activo(db, carrito_id)
        asiento = db.execute(text("SELECT asiento_id, estado FROM ASIENTO WHERE asiento_id = :aid FOR UPDATE SKIP LOCKED"), {"aid": payload.asiento_id}).fetchone()
        if not asiento: raise HTTPException(status_code=409, detail="El asiento no está disponible o está siendo procesado por otro usuario en este momento.")
        if asiento.estado != 'disponible': raise HTTPException(status_code=409, detail=f"El asiento ya está en estado '{asiento.estado}'.")
        db.execute(text("UPDATE ASIENTO SET estado = 'reservado' WHERE asiento_id = :aid"), {"aid": payload.asiento_id})
        detalle = db.execute(text("""
            INSERT INTO DETALLE_CARRITO (carrito_id, tipo_item, cantidad, precio_unitario, asiento_id, producto_id, promocion_id, tipo_boleto_id)
            VALUES (:cid, 'boleto', 1, :precio, :aid, NULL, NULL, :tbid) RETURNING detalle_carrito_id
        """), {"cid": carrito_id, "precio": payload.precio_unitario, "aid": payload.asiento_id, "tbid": payload.tipo_boleto_id}).fetchone()
        db.commit()
        return {"detalle_carrito_id": detalle.detalle_carrito_id, "asiento_id": payload.asiento_id, "estado_asiento": "reservado"}
    except HTTPException: db.rollback(); raise
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"Error al reservar asiento: {str(e)}")

def add_product(carrito_id: int, payload: AgregarProductoRequest, db: Session):
    try:
        _validar_carrito_activo(db, carrito_id)
        suma_porcentajes = sum(p.porcentaje or 0 for p in payload.personalizaciones)
        if suma_porcentajes > 100: raise HTTPException(status_code=400, detail="La suma de porcentajes de personalización no puede exceder 100%.")
        detalle = db.execute(text("""
            INSERT INTO DETALLE_CARRITO (carrito_id, tipo_item, cantidad, precio_unitario, asiento_id, producto_id, promocion_id, tipo_boleto_id)
            VALUES (:cid, 'producto', :cant, :precio, NULL, :pid, NULL, NULL) RETURNING detalle_carrito_id
        """), {"cid": carrito_id, "cant": payload.cantidad, "precio": payload.precio_unitario, "pid": payload.producto_id}).fetchone()
        detalle_carrito_id = detalle.detalle_carrito_id
        for p in payload.personalizaciones:
            db.execute(text("INSERT INTO DETALLE_PERSONALIZACION (detalle_carrito_id, opcion_id, porcentaje, cantidad) VALUES (:did, :oid, :pct, :cant)"), {"did": detalle_carrito_id, "oid": p.opcion_id, "pct": p.porcentaje, "cant": p.cantidad})
        db.commit()
        return {"detalle_carrito_id": detalle_carrito_id, "producto_id": payload.producto_id, "personalizaciones_agregadas": len(payload.personalizaciones)}
    except HTTPException: db.rollback(); raise
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"Error al agregar producto: {str(e)}")

def remove_item(carrito_id: int, detalle_carrito_id: int, db: Session):
    try:
        item = db.execute(text("SELECT tipo_item, asiento_id FROM DETALLE_CARRITO WHERE detalle_carrito_id = :did AND carrito_id = :cid"), {"did": detalle_carrito_id, "cid": carrito_id}).fetchone()
        if not item: raise HTTPException(status_code=404, detail="Ítem no encontrado en este carrito.")
        if item.tipo_item == 'boleto' and item.asiento_id: db.execute(text("UPDATE ASIENTO SET estado = 'disponible' WHERE asiento_id = :aid"), {"aid": item.asiento_id})
        else: db.execute(text("DELETE FROM DETALLE_PERSONALIZACION WHERE detalle_carrito_id = :did"), {"did": detalle_carrito_id})
        db.execute(text("DELETE FROM DETALLE_CARRITO WHERE detalle_carrito_id = :did"), {"did": detalle_carrito_id})
        db.commit()
        return {"mensaje": "Ítem eliminado del carrito.", "detalle_carrito_id": detalle_carrito_id}
    except HTTPException: db.rollback(); raise
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"Error al eliminar ítem: {str(e)}")

def abandon_cart(carrito_id: int, db: Session):
    try:
        carrito = db.execute(text("SELECT estado FROM CARRITO WHERE carrito_id = :cid FOR UPDATE"), {"cid": carrito_id}).fetchone()
        if not carrito: raise HTTPException(status_code=404, detail="Carrito no encontrado.")
        if carrito.estado != 'activo': raise HTTPException(status_code=400, detail=f"El carrito ya está '{carrito.estado}'.")
        db.execute(text("UPDATE ASIENTO SET estado = 'disponible' WHERE asiento_id IN (SELECT asiento_id FROM DETALLE_CARRITO WHERE carrito_id = :cid AND asiento_id IS NOT NULL)"), {"cid": carrito_id})
        db.execute(text("UPDATE CARRITO SET estado = 'abandonado' WHERE carrito_id = :cid"), {"cid": carrito_id})
        db.commit()
        return {"mensaje": "Carrito abandonado y asientos liberados.", "carrito_id": carrito_id}
    except HTTPException: db.rollback(); raise
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"Error al abandonar carrito: {str(e)}")

def pay_cart(carrito_id: int, payload: PagarCarritoRequest, db: Session):
    try:
        carrito = _validar_carrito_activo(db, carrito_id)
        items = db.execute(text("SELECT detalle_carrito_id, tipo_item, cantidad, precio_unitario, asiento_id, producto_id, tipo_boleto_id FROM DETALLE_CARRITO WHERE carrito_id = :cid"), {"cid": carrito_id}).fetchall()
        if not items: raise HTTPException(status_code=400, detail="El carrito está vacío.")
        boletos = [i for i in items if i.tipo_item == 'boleto']
        productos = [i for i in items if i.tipo_item == 'producto']
        
        for b in boletos:
            asiento = db.execute(text("SELECT estado FROM ASIENTO WHERE asiento_id = :aid FOR UPDATE"), {"aid": b.asiento_id}).fetchone()
            if not asiento or asiento.estado != 'reservado': raise HTTPException(status_code=409, detail=f"El asiento {b.asiento_id} ya no está reservado. Vuelve a intentar la reserva.")
        
        cargo_servicio_total = payload.cargo_servicio_por_boleto * len(boletos)
        subtotal = sum(float(i.precio_unitario) * i.cantidad for i in items)
        importe_total = subtotal + cargo_servicio_total

        venta = db.execute(text("""
            INSERT INTO VENTA (importe_total, cargo_servicio, forma_pago, tipo_venta, fecha_venta, sesion_id, socio_id, nombre_comprador, apellido_comprador, correo_comprador)
            VALUES (:total, :cargo, :pago, :tipo, :fecha, :sesion_id, :socio_id, :nombre, :apellido, :correo) RETURNING venta_id
        """), {"total": importe_total, "cargo": cargo_servicio_total, "pago": payload.forma_pago, "tipo": payload.tipo_venta, "fecha": datetime.now(), "sesion_id": payload.sesion_id, "socio_id": carrito.socio_id, "nombre": payload.nombre_comprador, "apellido": payload.apellido_comprador, "correo": payload.correo_comprador}).fetchone()
        venta_id = venta.venta_id

        for b in boletos:
            db.execute(text("INSERT INTO DETALLE_VENTA_BOLETO (tipo_boleto_id, precio_unitario, venta_id, asiento_id) VALUES (:tbid, :precio, :vid, :aid)"), {"tbid": b.tipo_boleto_id, "precio": b.precio_unitario, "vid": venta_id, "aid": b.asiento_id})
            db.execute(text("UPDATE ASIENTO SET estado = 'vendido' WHERE asiento_id = :aid"), {"aid": b.asiento_id})

        for p in productos:
            detalle_prod = db.execute(text("INSERT INTO DETALLE_VENTA_PRODUCTO (cantidad, precio_unitario, venta_id, producto_id) VALUES (:cant, :precio, :vid, :pid) RETURNING detalle_producto_id"), {"cant": p.cantidad, "precio": p.precio_unitario, "vid": venta_id, "pid": p.producto_id}).fetchone()
            personalizaciones = db.execute(text("SELECT opcion_id, porcentaje, cantidad FROM DETALLE_PERSONALIZACION WHERE detalle_carrito_id = :did"), {"did": p.detalle_carrito_id}).fetchall()
            for perso in personalizaciones:
                db.execute(text("INSERT INTO PERSONALIZACION_VENTA (detalle_venta_producto_id, opcion_id, porcentaje, cantidad) VALUES (:dvpid, :oid, :pct, :cant)"), {"dvpid": detalle_prod.detalle_producto_id, "oid": perso.opcion_id, "pct": perso.porcentaje, "cant": perso.cantidad})

        puntos_ganados = None
        if carrito.socio_id:
            from services.club_service import _acreditar_puntos_por_venta
            puntos_ganados = _acreditar_puntos_por_venta(db, carrito.socio_id, venta_id, subtotal)

        db.execute(text("UPDATE CARRITO SET estado = 'convertido' WHERE carrito_id = :cid"), {"cid": carrito_id})
        db.commit()
        return {"mensaje": "Venta procesada exitosamente.", "puntos_ganados": puntos_ganados, "venta_id": venta_id, "importe_total": importe_total, "cargo_servicio": cargo_servicio_total, "boletos_confirmados": len(boletos), "productos_confirmados": len(productos)}
    except HTTPException: db.rollback(); raise
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"Error al procesar el pago: {str(e)}")
