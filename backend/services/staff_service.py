from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from datetime import datetime
from schemas.models import PersonalLoginRequest, AbrirSesionRequest, CerrarSesionRequest

def login(payload: PersonalLoginRequest, db: Session):
    empleado = db.execute(text("""
        SELECT empleado_id, nombre, apellido_paterno, apellido_materno, rol_id, complejo_id 
        FROM EMPLEADO WHERE empleado_id = :eid AND LOWER(estatus) = 'activo'
    """), {"eid": payload.empleado_id}).fetchone()

    if not empleado:
        raise HTTPException(status_code=401, detail="ID de empleado incorrecto o el usuario está inactivo.")
        
    apellidos = f"{empleado.apellido_paterno} {empleado.apellido_materno or ''}".strip()
    return {"mensaje": "Login exitoso", "empleado_id": empleado.empleado_id, "nombre": f"{empleado.nombre} {apellidos}", "rol_id": empleado.rol_id, "complejo_id": empleado.complejo_id}


def abrir_sesion(payload: AbrirSesionRequest, db: Session):
    try:
        caja_abierta = db.execute(text("SELECT sesion_id FROM SESION WHERE punto_venta_id = :cid AND estado_sesion = 'abierta'"), {"cid": payload.caja_id}).fetchone()
        if caja_abierta: raise HTTPException(status_code=400, detail="Esta caja ya tiene una sesión abierta por otro empleado.")

        empleado_ocupado = db.execute(text("SELECT sesion_id, punto_venta_id FROM SESION WHERE empleado_id = :eid AND estado_sesion = 'abierta'"), {"eid": payload.empleado_id}).fetchone()
        if empleado_ocupado: raise HTTPException(status_code=400, detail=f"El empleado ya tiene la sesión {empleado_ocupado.sesion_id} abierta en la caja {empleado_ocupado.punto_venta_id}.")

        nueva_sesion = db.execute(text("""
            INSERT INTO SESION (empleado_id, punto_venta_id, fecha_hora_inicio, monto_inicial, estado_sesion, usuario_empleado)
            VALUES (:eid, :cid, :fecha, :saldo, 'abierta', COALESCE((SELECT nombre || ' ' || apellido_paterno FROM EMPLEADO WHERE empleado_id = :eid), 'Cajero'))
            RETURNING sesion_id
        """), {"eid": payload.empleado_id, "cid": payload.caja_id, "fecha": datetime.now(), "saldo": payload.saldo_inicial}).fetchone()
        
        db.commit()
        return {"mensaje": "Sesión de caja abierta exitosamente.", "sesion_id": nueva_sesion.sesion_id, "saldo_inicial": payload.saldo_inicial}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al abrir la sesión: {str(e)}")


def obtener_corte(sesion_id: int, db: Session):
    sesion_activa = db.execute(text("""
        SELECT s.sesion_id, s.estado_sesion, s.monto_inicial, s.usuario_empleado, s.punto_venta_id, e.nombre, e.apellido_paterno
        FROM sesion s JOIN EMPLEADO e ON s.empleado_id = e.empleado_id WHERE s.sesion_id = :sid
    """), {"sid": sesion_id}).fetchone()

    if not sesion_activa: raise HTTPException(status_code=404, detail="Sesión no encontrada.")
    
    ventas = db.execute(text("SELECT forma_pago, SUM(importe_total) as total FROM VENTA WHERE sesion_id = :sid GROUP BY forma_pago"), {"sid": sesion_id}).fetchall()

    total_efectivo = 0.0
    total_tarjeta = 0.0

    for v in ventas:
        monto = float(v.total)
        if v.forma_pago.lower() == 'efectivo': total_efectivo += monto
        else: total_tarjeta += monto

    efectivo_esperado = float(sesion_activa.monto_inicial) + total_efectivo

    return {"sesion_id": sesion_activa.sesion_id, "punto_venta_id": sesion_activa.punto_venta_id, "cajero": f"{sesion_activa.nombre} {sesion_activa.apellido_paterno}", "estado_sesion": sesion_activa.estado_sesion, "monto_inicial": float(sesion_activa.monto_inicial), "ventas_efectivo": total_efectivo, "ventas_tarjeta": total_tarjeta, "efectivo_esperado_en_caja": efectivo_esperado}


def cerrar_sesion(sesion_id: int, payload: CerrarSesionRequest, db: Session):
    try:
        sesion = db.execute(text("SELECT estado_sesion, monto_inicial FROM SESION WHERE sesion_id = :sid"), {"sid": sesion_id}).fetchone()
        if not sesion: raise HTTPException(status_code=404, detail="Sesión no encontrada.")
        if sesion.estado_sesion.lower() != 'abierta': raise HTTPException(status_code=400, detail=f"No se puede cerrar. El estado actual de la caja es: {sesion.estado_sesion}")

        diferencia = payload.saldo_reportado_efectivo - float(sesion.monto_inicial)
        estado_cuadre = "Perfecto"
        if diferencia > 0: estado_cuadre = f"Sobrante en Caja (Sobran ${abs(diferencia)})"
        elif diferencia < 0: estado_cuadre = f"Faltante en Caja (Faltan ${abs(diferencia)})"

        db.execute(text("UPDATE SESION SET estado_sesion = 'cerrada', monto_final_sistema = :final, fecha_hora_fin = :fecha WHERE sesion_id = :sid"), {"final": payload.saldo_reportado_efectivo, "fecha": datetime.now(), "sid": sesion_id})
        db.commit()

        return {"mensaje": "Corte de caja realizado exitosamente.", "sesion_id": sesion_id, "resultado_corte": estado_cuadre, "diferencia": diferencia}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al cerrar la sesión: {str(e)}")
