from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from datetime import datetime
from schemas.models import GarantiaReclamoRequest

def process_reclamo(payload: GarantiaReclamoRequest, db: Session):
    try:
        nuevo_reclamo = db.execute(text("""
            INSERT INTO garantia_reclamo (nombre_reclamante, correo, motivo, fecha_reclamo, 
                                          estado_reclamo, venta_id, pelicula_id, complejo_id)
            VALUES (:nom, :corr, :mot, :fecha, 'aprobado', :vid, :pid, :cid)
            RETURNING reclamo_id
        """), {
            "nom": payload.nombre_reclamante, "corr": payload.correo, "mot": payload.motivo,
            "fecha": datetime.now(), "vid": payload.venta_id, "pid": payload.pelicula_id, "cid": payload.complejo_id
        }).fetchone()
        
        reclamo_generado_id = nuevo_reclamo[0] if nuevo_reclamo else None
        asientos_liberados = 0
        puntos_revertidos = 0

        if payload.venta_id:
            resultado_asientos = db.execute(text("""
                WITH boletos_venta AS (
                    SELECT asiento_id FROM detalle_venta_boleto WHERE venta_id = :vid
                )
                UPDATE ASIENTO SET estado = 'disponible' WHERE asiento_id IN (SELECT asiento_id FROM boletos_venta)
            """), {"vid": payload.venta_id})
            
            asientos_liberados = resultado_asientos.rowcount

            venta_info = db.execute(text("SELECT socio_id, importe_total FROM VENTA WHERE venta_id = :vid"), {"vid": payload.venta_id}).fetchone()

            if venta_info and venta_info.socio_id:
                puntos_a_revertir = int(float(venta_info.importe_total) * 0.05)
                db.execute(text("UPDATE CUENTA_CLUB SET puntos_acumulados = GREATEST(0, puntos_acumulados - :puntos) WHERE socio_id = :sid"), {"puntos": puntos_a_revertir, "sid": venta_info.socio_id})
                puntos_revertidos = puntos_a_revertir

        db.commit()
        return {"mensaje": "Reclamo procesado exitosamente y garantía aplicada.", "reclamo_id": reclamo_generado_id, "asientos_liberados": asientos_liberados, "puntos_revertidos": puntos_revertidos}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar el reclamo: {str(e)}")
