from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException

def get_banners(complejo_slug: str, db: Session):
    consulta = text("""
        SELECT bp.banner_id, bp.titulo, bp.imagen_url, bp.url_destino
        FROM BANNER_PROMO bp
        JOIN COMPLEJO c ON c.slug = :slug
        WHERE (bp.aplica_todos = TRUE OR EXISTS (
            SELECT 1 FROM BANNER_PROMO_COMPLEJO bpc
            WHERE bpc.banner_id = bp.banner_id AND bpc.complejo_id = c.complejo_id
        ))
        AND bp.activo = TRUE 
        AND bp.fecha_inicio <= CURRENT_DATE
        AND (bp.fecha_fin >= CURRENT_DATE OR bp.fecha_fin IS NULL)
        ORDER BY bp.banner_id DESC
    """)
    try:
        resultados = db.execute(consulta, {"slug": complejo_slug}).fetchall()
        return {
            "complejo": complejo_slug,
            "total_banners": len(resultados),
            "banners": [dict(r._mapping) for r in resultados]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener los banners: {str(e)}")


def get_promociones(complejo_slug: str, socio_id: int, db: Session):
    try:
        nivel_socio = None
        if socio_id:
            cuenta = db.execute(text("SELECT nivel_id FROM CUENTA_CLUB WHERE socio_id = :sid"), {"sid": socio_id}).fetchone()
            if cuenta:
                nivel_socio = cuenta.nivel_id

        promos = db.execute(text("""
            SELECT p.promocion_id, p.nombre_promocion, p.tipo_promocion, p.descripcion,
                   p.fecha_inicio_vigencia, p.fecha_fin_vigencia, p.nivel_id
            FROM PROMOCION p
            JOIN COMPLEJO c ON c.slug = :slug
            WHERE (p.aplica_todos = TRUE OR EXISTS (
                      SELECT 1 FROM PROMOCION_COMPLEJO pc
                      WHERE pc.promocion_id = p.promocion_id AND pc.complejo_id = c.complejo_id
                  ))
              AND (p.fecha_fin_vigencia IS NULL OR p.fecha_fin_vigencia >= CURRENT_DATE)
              AND p.fecha_inicio_vigencia <= CURRENT_DATE
            ORDER BY p.fecha_inicio_vigencia DESC
        """), {"slug": complejo_slug}).fetchall()

        resultado = [
            dict(p._mapping) for p in promos
            if not (p.nivel_id and nivel_socio and p.nivel_id > nivel_socio)
        ]

        return {"complejo": complejo_slug, "total_promociones": len(resultado), "promociones": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener las promociones: {str(e)}")
