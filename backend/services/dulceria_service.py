from sqlalchemy.orm import Session
from sqlalchemy import text

def get_catalogo(complejo_slug: str, db: Session):
    consulta = text("""
        SELECT 
            cd.nombre_categoria, pd.producto_id, pd.nombre_producto, pd.descripcion, pd.imagen_url, dc.precio_actual,
            mr.regla_id, mr.titulo_regla, mr.min_items, mr.max_items,
            mo.opcion_id, mo.nombre_opcion, mo.precio_adicional, mo.imagen_url AS opcion_imagen_url
        FROM COMPLEJO c
        JOIN CATALOGO_COMPLEJO cc ON c.complejo_id = cc.complejo_id
        JOIN DETALLE_CATALOGO dc ON cc.catalogo_id = dc.catalogo_id
        JOIN PRODUCTO_DULCERIA pd ON dc.producto_id = pd.producto_id
        JOIN CATEGORIA_DULCERIA cd ON pd.categoria_id = cd.categoria_id
        LEFT JOIN MODIFICADOR_REGLA mr ON pd.producto_id = mr.producto_id
        LEFT JOIN MODIFICADOR_OPCION mo ON mr.regla_id = mo.regla_id
        WHERE c.slug = :slug AND dc.disponibilidad = TRUE
        ORDER BY cd.categoria_id, pd.producto_id, mr.regla_id, mo.precio_adicional DESC
    """)
    
    resultados = db.execute(consulta, {"slug": complejo_slug}).fetchall()
    if not resultados:
        return {"mensaje": "No hay catálogo de dulcería configurado para este complejo."}

    catalogo = {}
    for row in resultados:
        cat_nombre = row.nombre_categoria
        prod_id = row.producto_id
        regla_id = row.regla_id
        
        if cat_nombre not in catalogo: catalogo[cat_nombre] = {}
        if prod_id not in catalogo[cat_nombre]:
            catalogo[cat_nombre][prod_id] = {
                "producto_id": prod_id, "nombre": row.nombre_producto, "descripcion": row.descripcion,
                "imagen_url": row.imagen_url, "precio": float(row.precio_actual), "personalizacion": {}
            }
            
        if regla_id:
            prod_obj = catalogo[cat_nombre][prod_id]["personalizacion"]
            if regla_id not in prod_obj:
                prod_obj[regla_id] = {"regla_id": regla_id, "titulo": row.titulo_regla, "limite_minimo": row.min_items, "limite_maximo": row.max_items, "opciones": []}
            if row.opcion_id:
                prod_obj[regla_id]["opciones"].append({
                    "opcion_id": row.opcion_id,
                    "nombre": row.nombre_opcion,
                    "precio_extra": float(row.precio_adicional),
                    "imagen_url": row.opcion_imagen_url or "",
                })

    menu_final = []
    for cat, productos_dict in catalogo.items():
        lista_productos = []
        for p in productos_dict.values():
            p["personalizacion"] = list(p["personalizacion"].values())
            lista_productos.append(p)
        menu_final.append({"categoria": cat, "productos": lista_productos})

    return {"complejo": complejo_slug, "menu": menu_final}
