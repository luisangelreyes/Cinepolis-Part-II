from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
from datetime import date, datetime

def get_pelicula(pelicula_id: int, db: Session):
    consulta = text("""
        SELECT pelicula_id, titulo, slug, clasificacion, genero, duracion_min, sinopsis, categoria, poster_url, banner_url, trailer_url
        FROM PELICULA
        WHERE pelicula_id = :pid
    """)
    resultado = db.execute(consulta, {"pid": pelicula_id}).fetchone()
    if not resultado:
        raise HTTPException(status_code=404, detail="Película no encontrada")

    pelicula = dict(resultado._mapping)

    elenco = db.execute(text("""
        SELECT per.nombre, pp.rol
        FROM PELICULA_PERSONA pp
        JOIN PERSONA per ON per.persona_id = pp.persona_id
        WHERE pp.pelicula_id = :pid
        ORDER BY pp.rol DESC, per.nombre
    """), {"pid": pelicula_id}).fetchall()

    pelicula["director"] = next((e.nombre for e in elenco if e.rol == "director"), None)
    pelicula["actores"] = [e.nombre for e in elenco if e.rol == "actor"]

    return pelicula


def get_fechas_disponibles(complejo_slug: str, db: Session):
    consulta = text("""
        SELECT DISTINCT f.fecha_funcion
        FROM FUNCION f
        JOIN SALA s ON f.sala_id = s.sala_id
        JOIN COMPLEJO c ON s.complejo_id = c.complejo_id
        WHERE c.slug = :slug AND f.activa = TRUE AND f.fecha_funcion >= CURRENT_DATE
        ORDER BY f.fecha_funcion
    """)
    resultados = db.execute(consulta, {"slug": complejo_slug}).fetchall()
    return [str(row[0]) for row in resultados]

def get_cartelera(complejo_slug: str, fecha: str, db: Session):
    if not fecha:
        fecha = date.today().isoformat()
        
    consulta = text("""
        SELECT 
            p.pelicula_id, p.titulo, p.clasificacion, p.duracion_min, p.poster_url, p.categoria,
            f.funcion_id, f.hora_inicio, fs.nombre_formato AS formato, f.idioma, s.nombre_sala, s.tipo_sala
        FROM FUNCION f
        JOIN PELICULA p ON f.pelicula_id = p.pelicula_id
        JOIN SALA s ON f.sala_id = s.sala_id
        JOIN COMPLEJO c ON s.complejo_id = c.complejo_id
        JOIN FORMATO_SALA fs ON f.formato_id = fs.formato_id
        WHERE c.slug = :slug AND f.fecha_funcion = :fecha AND f.activa = TRUE
        ORDER BY p.titulo, f.hora_inicio
    """)
    
    resultados = db.execute(consulta, {"slug": complejo_slug, "fecha": fecha}).fetchall()
    if not resultados:
        return {"mensaje": "No hay funciones programadas para este cine en esta fecha.", "peliculas": []}
    
    cartelera = {}
    for row in resultados:
        p_id = row.pelicula_id
        if p_id not in cartelera:
            cartelera[p_id] = {
                "pelicula_id": p_id, "titulo": row.titulo, "clasificacion": row.clasificacion,
                "duracion_min": row.duracion_min, "poster_url": row.poster_url,
                "categoria": row.categoria, "funciones": []
            }
        
        cartelera[p_id]["funciones"].append({
            "funcion_id": row.funcion_id, "hora_inicio": str(row.hora_inicio),
            "formato": row.formato, "idioma": row.idioma, "sala": row.nombre_sala, "tipo_sala": row.tipo_sala
        })
        
    return {"complejo": complejo_slug, "fecha_consulta": fecha, "total_peliculas": len(cartelera), "peliculas": list(cartelera.values())}


def get_asientos(funcion_id: int, db: Session):
    info_funcion = db.execute(text("""
        SELECT p.pelicula_id, p.titulo, p.clasificacion, p.duracion_min, p.poster_url,
               s.nombre_sala, f.hora_inicio, f.fecha_funcion
        FROM FUNCION f JOIN PELICULA p ON f.pelicula_id = p.pelicula_id JOIN SALA s ON f.sala_id = s.sala_id
        WHERE f.funcion_id = :fid
    """), {"fid": funcion_id}).fetchone()

    if not info_funcion: raise HTTPException(status_code=404, detail="Función no encontrada.")

    # Liberar asientos de carritos expirados antes de consultar el mapa
    db.execute(text("""
        UPDATE ASIENTO 
        SET estado = 'disponible' 
        WHERE funcion_id = :fid 
          AND estado = 'reservado'
          AND asiento_id IN (
              SELECT dc.asiento_id 
              FROM DETALLE_CARRITO dc 
              JOIN CARRITO c ON dc.carrito_id = c.carrito_id 
              WHERE c.estado = 'activo' AND c.fecha_expiracion < :now
          )
    """), {"fid": funcion_id, "now": datetime.now()})
    
    db.execute(text("""
        UPDATE CARRITO 
        SET estado = 'abandonado' 
        WHERE estado = 'activo' AND fecha_expiracion < :now
    """), {"now": datetime.now()})
    
    db.commit()

    asientos_raw = db.execute(text("""
        SELECT a.asiento_id, a.fila, a.columna, a.tipo_asiento, a.estado, ap.area_category_code
        FROM ASIENTO a
        JOIN FUNCION f ON a.funcion_id = f.funcion_id
        JOIN ASIENTO_PLANTILLA ap ON ap.sala_id = f.sala_id AND ap.fila = a.fila AND ap.columna = a.columna
        WHERE a.funcion_id = :fid 
        ORDER BY a.fila, a.columna
    """), {"fid": funcion_id}).fetchall()

    mapa_filas = {}
    total_disponibles = 0
    for a in asientos_raw:
        fila = a.fila
        if fila not in mapa_filas: mapa_filas[fila] = []
        mapa_filas[fila].append({
            "asiento_id": a.asiento_id, "columna": a.columna, "etiqueta": f"{fila}{a.columna}",
            "tipo": a.tipo_asiento, "estado": a.estado, "area_code": a.area_category_code
        })
        if a.estado == 'disponible': total_disponibles += 1

    return {
        "funcion_id": funcion_id,
        "pelicula_id": info_funcion.pelicula_id,
        "pelicula": info_funcion.titulo,
        "clasificacion": info_funcion.clasificacion,
        "duracion_min": info_funcion.duracion_min,
        "poster_url": info_funcion.poster_url,
        "sala": info_funcion.nombre_sala,
        "horario": str(info_funcion.hora_inicio),
        "fecha_funcion": str(info_funcion.fecha_funcion),
        "asientos_disponibles": total_disponibles,
        "mapa": mapa_filas
    }


def get_precios(funcion_id: int, db: Session):
    # 1. Obtener las áreas físicas (areaCategoryCode) que existen en la sala de esta función.
    #    Si area_category_code es NULL en ASIENTO_PLANTILLA, se trata como área genérica.
    areas_sala = db.execute(text("""
        SELECT DISTINCT ap.area_category_code
        FROM FUNCION f
        JOIN SALA s ON f.sala_id = s.sala_id
        JOIN ASIENTO_PLANTILLA ap ON ap.sala_id = s.sala_id
        WHERE f.funcion_id = :fid
          AND ap.area_category_code IS NOT NULL
    """), {"fid": funcion_id}).fetchall()

    codigos_area = {row[0] for row in areas_sala if row[0]}

    # 2. Traer los precios que coincidan con alguna de las áreas de la sala,
    #    O cuyo area_category_code sea NULL (boletos base que aplican a toda la sala).
    #
    #    Si la sala aún no tiene datos de ASIENTO_PLANTILLA (codigos_area vacío),
    #    se hace fallback a la consulta original por tipo_sala para no romper nada.
    if codigos_area:
        # Construir la lista de parámetros de forma segura
        area_params = {f"a{i}": code for i, code in enumerate(codigos_area)}
        area_placeholders = ", ".join(f":a{i}" for i in range(len(codigos_area)))

        precios = db.execute(text(f"""
            SELECT DISTINCT ON (tb.tipo_boleto_id, pb.area_category_code)
                tb.tipo_boleto_id,
                tb.nombre AS tipo_boleto,
                pb.precio,
                pb.cargo_servicio_online,
                pb.area_category_code
            FROM FUNCION f
            JOIN SALA s ON f.sala_id = s.sala_id
            JOIN PRECIO_BOLETO pb
                ON pb.complejo_id = s.complejo_id
               AND pb.formato_id  = f.formato_id
               AND pb.tipo_sala   = s.tipo_sala
               AND (pb.area_category_code IN ({area_placeholders})
                    OR pb.area_category_code IS NULL)
            JOIN TIPO_BOLETO tb ON pb.tipo_boleto_id = tb.tipo_boleto_id
            WHERE f.funcion_id = :fid
            ORDER BY tb.tipo_boleto_id, pb.area_category_code NULLS LAST, pb.precio DESC
        """), {"fid": funcion_id, **area_params}).fetchall()
    else:
        # Fallback: la sala todavía no tiene mapa de asientos → comportamiento anterior
        precios = db.execute(text("""
            SELECT tb.tipo_boleto_id, tb.nombre AS tipo_boleto,
                   pb.precio, pb.cargo_servicio_online, pb.area_category_code
            FROM FUNCION f
            JOIN SALA s ON f.sala_id = s.sala_id
            JOIN PRECIO_BOLETO pb
                ON pb.complejo_id = s.complejo_id
               AND pb.formato_id  = f.formato_id
               AND pb.tipo_sala   = s.tipo_sala
            JOIN TIPO_BOLETO tb ON pb.tipo_boleto_id = tb.tipo_boleto_id
            WHERE f.funcion_id = :fid
            ORDER BY pb.precio DESC
        """), {"fid": funcion_id}).fetchall()

    if not precios:
        raise HTTPException(status_code=404, detail="No se encontraron tarifas configuradas para esta función.")

    return {
        "funcion_id": funcion_id,
        "tarifas": [
            {
                "tipo_boleto_id":   p.tipo_boleto_id,
                "tipo_boleto":      p.tipo_boleto,
                "precio":           float(p.precio),
                "cargo_servicio":   float(p.cargo_servicio_online),
                "total_online":     float(p.precio + p.cargo_servicio_online),
                "area_code":        p.area_category_code,
            }
            for p in precios
        ],
    }

