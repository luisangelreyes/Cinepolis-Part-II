from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date, timedelta
import random
from schemas.models import SolicitarOTPRequest, VerificarOTPRequest, CanjearPuntosRequest

def _semestre_actual(fecha: date) -> str:
    return f"{fecha.year}-S{1 if fecha.month <= 6 else 2}"

def _acreditar_puntos_por_venta(db: Session, socio_id: int, venta_id: int, monto_base: float):
    cuenta = db.execute(text("SELECT cc.visitas_semestre_actual, nc.porcentaje_acumulacion_puntos FROM CUENTA_CLUB cc JOIN NIVEL_CLUB nc ON cc.nivel_id = nc.nivel_id WHERE cc.socio_id = :sid FOR UPDATE"), {"sid": socio_id}).fetchone()
    if not cuenta: return None
    puntos_ganados = round(float(monto_base) * float(cuenta.porcentaje_acumulacion_puntos) / 100, 2)
    nuevas_visitas = cuenta.visitas_semestre_actual + 1
    db.execute(text("INSERT INTO DETALLE_PUNTOS (fecha_movimiento, tipo_movimiento, cantidad_puntos, descripcion_movimiento, socio_id, venta_id) VALUES (:fecha, 'acumulacion', :puntos, :desc, :sid, :vid)"), {"fecha": datetime.now(), "puntos": puntos_ganados, "desc": f"Acumulación por venta #{venta_id}", "sid": socio_id, "vid": venta_id})
    nuevo_nivel = db.execute(text("SELECT nivel_id FROM NIVEL_CLUB WHERE visitas_min_semestre <= :visitas AND (visitas_max_semestre IS NULL OR visitas_max_semestre >= :visitas) ORDER BY visitas_min_semestre DESC LIMIT 1"), {"visitas": nuevas_visitas}).fetchone()
    db.execute(text("UPDATE CUENTA_CLUB SET puntos_acumulados = puntos_acumulados + :puntos, visitas_semestre_actual = :visitas, nivel_id = COALESCE(:nuevo_nivel, nivel_id) WHERE socio_id = :sid"), {"puntos": puntos_ganados, "visitas": nuevas_visitas, "nuevo_nivel": nuevo_nivel.nivel_id if nuevo_nivel else None, "sid": socio_id})
    return puntos_ganados

def request_otp(payload: SolicitarOTPRequest, db: Session):
    codigo = f"{random.randint(0, 999999):06d}"
    expiracion = datetime.now() + timedelta(minutes=2)
    db.execute(text("INSERT INTO OTP_VERIFICACION (correo, codigo, intentos, expiracion, usado) VALUES (:correo, :codigo, 0, :exp, FALSE)"), {"correo": payload.correo, "codigo": codigo, "exp": expiracion})
    db.commit()
    return {"mensaje": f"Código OTP generado para {payload.correo}. Expira en 2 minutos.", "codigo_debug": codigo}

def verify_otp(payload: VerificarOTPRequest, db: Session):
    try:
        otp = db.execute(text("SELECT otp_id, codigo, intentos, expiracion, usado FROM OTP_VERIFICACION WHERE correo = :correo ORDER BY otp_id DESC LIMIT 1 FOR UPDATE"), {"correo": payload.correo}).fetchone()
        if not otp: raise HTTPException(status_code=404, detail="No se ha solicitado un código OTP para este correo.")
        if otp.usado: raise HTTPException(status_code=400, detail="Este código ya fue utilizado. Solicita uno nuevo.")
        if otp.intentos >= 3: raise HTTPException(status_code=400, detail="Se agotaron los intentos permitidos. Solicita un nuevo código.")
        if otp.expiracion < datetime.now(): raise HTTPException(status_code=400, detail="El código expiró. Solicita uno nuevo.")
        if otp.codigo != payload.codigo:
            db.execute(text("UPDATE OTP_VERIFICACION SET intentos = intentos + 1 WHERE otp_id = :oid"), {"oid": otp.otp_id})
            db.commit()
            raise HTTPException(status_code=400, detail="Código incorrecto.")
        
        db.execute(text("UPDATE OTP_VERIFICACION SET usado = TRUE WHERE otp_id = :oid"), {"oid": otp.otp_id})
        cuenta = db.execute(text("SELECT socio_id, nombre, apellidos, nivel_id, puntos_acumulados FROM CUENTA_CLUB WHERE correo = :correo"), {"correo": payload.correo}).fetchone()
        
        if cuenta:
            db.commit()
            return {"mensaje": "Login exitoso.", "es_nuevo": False, "socio_id": cuenta.socio_id, "nombre": cuenta.nombre, "apellidos": cuenta.apellidos, "nivel_id": cuenta.nivel_id, "puntos_acumulados": float(cuenta.puntos_acumulados)}
        
        if not payload.nombre or not payload.apellidos or not payload.fecha_nacimiento:
            db.commit()
            return {"mensaje": "Correo verificado. Faltan datos para completar el registro.", "es_nuevo": True, "requiere_registro": True, "campos_requeridos": ["nombre", "apellidos", "fecha_nacimiento"]}
        
        nivel_fan = db.execute(text("SELECT nivel_id FROM NIVEL_CLUB WHERE nombre_nivel = 'Fan' LIMIT 1")).fetchone()
        if not nivel_fan: raise HTTPException(status_code=500, detail="No existe el nivel 'Fan' en NIVEL_CLUB.")
        
        hoy = date.today()
        numero_tarjeta = " ".join(f"{random.randint(0, 9999):04d}" for _ in range(4))
        usuario_cc = payload.correo.split("@")[0] + str(random.randint(100, 999))
        
        nueva_cuenta = db.execute(text("""
            INSERT INTO CUENTA_CLUB (usuario_CC, numero_tarjeta, nombre, apellidos, correo, fecha_nacimiento, genero, codigo_postal, fecha_registro, puntos_acumulados, puntos_vencen_fecha, visitas_semestre_actual, semestre_actual, nivel_id)
            VALUES (:usuario, :tarjeta, :nombre, :apellidos, :correo, :fnac, :genero, :cp, :freg, 0, :pvence, 0, :sem, :nivel) RETURNING socio_id
        """), {"usuario": usuario_cc, "tarjeta": numero_tarjeta, "nombre": payload.nombre, "apellidos": payload.apellidos, "correo": payload.correo, "fnac": payload.fecha_nacimiento, "genero": payload.genero, "cp": payload.codigo_postal, "freg": hoy, "pvence": date(hoy.year, 12, 31), "sem": _semestre_actual(hoy), "nivel": nivel_fan.nivel_id}).fetchone()
        db.commit()
        return {"mensaje": "Registro completado exitosamente.", "es_nuevo": True, "socio_id": nueva_cuenta.socio_id, "numero_tarjeta": numero_tarjeta, "nivel_id": nivel_fan.nivel_id}
    except HTTPException: db.rollback(); raise
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"Error en verificación OTP: {str(e)}")

def get_profile(socio_id: int, db: Session):
    cuenta = db.execute(text("""
        SELECT cc.socio_id, cc.nombre, cc.apellidos, cc.numero_tarjeta, cc.puntos_acumulados, cc.visitas_semestre_actual, cc.semestre_actual, cc.puntos_vencen_fecha, nc.nivel_id, nc.nombre_nivel, nc.visitas_min_semestre, nc.visitas_max_semestre, nc.porcentaje_acumulacion_puntos, nc.descripcion_beneficios
        FROM CUENTA_CLUB cc JOIN NIVEL_CLUB nc ON cc.nivel_id = nc.nivel_id WHERE cc.socio_id = :sid
    """), {"sid": socio_id}).fetchone()
    if not cuenta: raise HTTPException(status_code=404, detail="Socio no encontrado.")
    
    nivel_por_visitas = db.execute(text("SELECT nivel_id, nombre_nivel, visitas_min_semestre, visitas_max_semestre FROM NIVEL_CLUB WHERE visitas_min_semestre <= :visitas AND (visitas_max_semestre IS NULL OR visitas_max_semestre >= :visitas) ORDER BY visitas_min_semestre DESC LIMIT 1"), {"visitas": cuenta.visitas_semestre_actual}).fetchone()
    siguiente_nivel = db.execute(text("SELECT nombre_nivel, visitas_min_semestre FROM NIVEL_CLUB WHERE visitas_min_semestre > :actual ORDER BY visitas_min_semestre ASC LIMIT 1"), {"actual": cuenta.visitas_semestre_actual}).fetchone()
    
    progreso = None
    if siguiente_nivel and nivel_por_visitas:
        rango = siguiente_nivel.visitas_min_semestre - nivel_por_visitas.visitas_min_semestre
        avance = cuenta.visitas_semestre_actual - nivel_por_visitas.visitas_min_semestre
        progreso = {"siguiente_nivel": siguiente_nivel.nombre_nivel, "visitas_faltantes": siguiente_nivel.visitas_min_semestre - cuenta.visitas_semestre_actual, "porcentaje_avance": round((avance / rango) * 100, 1) if rango > 0 else 100.0}
    
    inconsistencia_nivel = (nivel_por_visitas is not None and nivel_por_visitas.nivel_id != cuenta.nivel_id)
    return {"socio_id": cuenta.socio_id, "nombre": cuenta.nombre, "apellidos": cuenta.apellidos, "numero_tarjeta": cuenta.numero_tarjeta, "puntos_acumulados": float(cuenta.puntos_acumulados), "puntos_vencen_fecha": cuenta.puntos_vencen_fecha, "nivel": {"nivel_id": cuenta.nivel_id, "nombre_nivel": cuenta.nombre_nivel, "porcentaje_acumulacion_puntos": float(cuenta.porcentaje_acumulacion_puntos), "beneficios": cuenta.descripcion_beneficios}, "visitas_semestre_actual": cuenta.visitas_semestre_actual, "semestre_actual": cuenta.semestre_actual, "progreso_siguiente_nivel": progreso, "advertencia_nivel_inconsistente": (f"El nivel guardado ({cuenta.nombre_nivel}) no coincide con el que corresponde por visitas ({nivel_por_visitas.nombre_nivel}). Revisa el dato de prueba.") if inconsistencia_nivel else None}

def get_movements(socio_id: int, limite: int, db: Session):
    movimientos = db.execute(text("SELECT detalle_puntos_id, fecha_movimiento, tipo_movimiento, cantidad_puntos, descripcion_movimiento, venta_id FROM DETALLE_PUNTOS WHERE socio_id = :sid ORDER BY fecha_movimiento DESC LIMIT :lim"), {"sid": socio_id, "lim": limite}).fetchall()
    return {"socio_id": socio_id, "movimientos": [dict(m._mapping) for m in movimientos]}

def redeem_points(socio_id: int, payload: CanjearPuntosRequest, db: Session):
    try:
        cuenta = db.execute(text("SELECT puntos_acumulados FROM CUENTA_CLUB WHERE socio_id = :sid FOR UPDATE"), {"sid": socio_id}).fetchone()
        if not cuenta: raise HTTPException(status_code=404, detail="Socio no encontrado.")
        if payload.cantidad_puntos <= 0: raise HTTPException(status_code=400, detail="La cantidad a canjear debe ser positiva.")
        if float(cuenta.puntos_acumulados) < payload.cantidad_puntos: raise HTTPException(status_code=400, detail="Puntos insuficientes para este canje.")
        db.execute(text("INSERT INTO DETALLE_PUNTOS (fecha_movimiento, tipo_movimiento, cantidad_puntos, descripcion_movimiento, socio_id, venta_id) VALUES (:fecha, 'canje', :cant, NULL, :sid, NULL)"), {"fecha": datetime.now(), "cant": -abs(payload.cantidad_puntos), "sid": socio_id})
        db.commit()
        return {"mensaje": "Puntos canjeados exitosamente.", "puntos_canjeados": payload.cantidad_puntos}
    except HTTPException: db.rollback(); raise
    except IntegrityError as e: db.rollback(); raise HTTPException(status_code=400, detail="No se pudo completar el canje por una inconsistencia en la base de datos.")
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=f"Error al canjear puntos: {str(e)}")
