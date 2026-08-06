"""
=============================================================================
GENERADOR DE SEED — Dulcería Vision v3.4
=============================================================================
Lee los 3 CSVs producidos por Sofía V10 y genera un SQL completo con:

  TRUNCATE en cascada de todas las tablas de dulcería
  INSERT → CATEGORIA_DULCERIA
  INSERT → PRODUCTO_DULCERIA
  INSERT → CATALOGO_COMPLEJO
  INSERT → DETALLE_CATALOGO
  INSERT → MODIFICADOR_REGLA
  INSERT → MODIFICADOR_OPCION

Valores válidos para tipo_modificador (CHECK constraint en Vision):
  flavor | size | extra | ingredient | popcorn | compound
=============================================================================
"""

import csv

CSV_MAESTRO         = "productos_maestro.csv"
CSV_PRECIOS         = "precios_por_complejo.csv"
CSV_PERSONALIZACION = "personalizaciones_maestro.csv"
SQL_SALIDA          = "seed_dulceria_vision.sql"

SLUG_A_COMPLEJO_ID = {
    "cinepolis-la-florida-acayucan":           1,
    "cinepolis-vip-el-dorado-veracruz":        2,
    "cinepolis-las-americas-veracruz":         3,
    "cinepolis-vip-las-americas-veracruz":     4,
    "cinepolis-el-dorado-coatzacoalcos":       5,
    "cinepolis-acaya-coatzacoalcos":           6,
    "cinepolis-plaza-shangri-la-cordoba":      7,
    "cinepolis-plaza-museo-xalapa":            8,
    "cinepolis-plaza-crystal-xalapa":          9,
    "cinepolis-vip-las-americas-xalapa":      10,
    "cinepolis-plaza-las-americas-xalapa":    11,
    "cinepolis-chedraui-martinez-de-la-torre":12,
    "cinepolis-plaza-minatitlan":             13,
    "cinepolis-plaza-valle-orizaba":          14,
    "cinepolis-rio-blanco-orizaba":           15,
    "cinepolis-plaza-crystal-tuxpan":         16,
    "cinepolis-portal-veracruz":              17,
    "cinepolis-plaza-del-puerto-veracruz":    18,
    "cinepolis-el-dorado-veracruz":           19,
}

TIPOS_VALIDOS = {"flavor", "size", "extra", "ingredient", "popcorn", "compound"}

def tipo_mod(mod_tipo):
    t = (mod_tipo or "").strip().lower()
    return t if t in TIPOS_VALIDOS else "ingredient"

def esc(v):
    if v is None or str(v).strip() == "":
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"

def num(v):
    try:    return str(round(float(v), 2))
    except: return "0.00"

def leer(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def generar():
    print("=" * 65)
    print("  GENERADOR SEED DULCERÍA — Vision v3.4 (rebuild completo)")
    print("=" * 65)

    maestro  = leer(CSV_MAESTRO)
    precios  = leer(CSV_PRECIOS)
    perso    = leer(CSV_PERSONALIZACION)

    print(f"  productos_maestro:         {len(maestro):>4}")
    print(f"  precios_por_complejo:      {len(precios):>4}")
    print(f"  personalizaciones_maestro: {len(perso):>4}")

    sql = []
    sql.append("-- Seed dulcería Vision v3.4 — rebuild completo")
    sql.append("BEGIN;")
    sql.append("")
    sql.append("-- Limpiar en orden inverso de dependencias")
    sql.append("TRUNCATE DETALLE_PERSONALIZACION CASCADE;")
    sql.append("TRUNCATE MODIFICADOR_OPCION      CASCADE;")
    sql.append("TRUNCATE MODIFICADOR_REGLA       CASCADE;")
    sql.append("TRUNCATE DETALLE_CATALOGO        CASCADE;")
    sql.append("TRUNCATE HISTORIAL_PRODUCTO      CASCADE;")
    sql.append("TRUNCATE CATALOGO_COMPLEJO       CASCADE;")
    sql.append("TRUNCATE PRODUCTO_DULCERIA       CASCADE;")
    sql.append("TRUNCATE CATEGORIA_DULCERIA      CASCADE;")
    sql.append("")

    # ── 1. CATEGORIA_DULCERIA ─────────────────────────────────────────────────
    sql.append("-- 1. CATEGORIA_DULCERIA")
    categorias = {}
    cat_seq = 1
    for row in maestro:
        cat = (row.get("categoria") or "Sin Categoría").strip()
        if cat not in categorias:
            categorias[cat] = cat_seq
            sql.append(
                f"INSERT INTO CATEGORIA_DULCERIA (categoria_id, nombre_categoria) "
                f"VALUES ({cat_seq}, {esc(cat)});"
            )
            cat_seq += 1
    sql.append(f"-- {len(categorias)} categorías")
    sql.append("")

    # ── 2. PRODUCTO_DULCERIA ──────────────────────────────────────────────────
    sql.append("-- 2. PRODUCTO_DULCERIA")
    productos = {}
    prod_seq = 1
    for row in maestro:
        api_id = str(row.get("id_producto", "")).strip()
        if not api_id or api_id in productos:
            continue
        nombre   = (row.get("nombre") or "").strip()
        desc     = (row.get("descripcion") or "").strip() or None
        imagen   = (row.get("img_normal") or "").strip() or None
        cat_name = (row.get("categoria") or "Sin Categoría").strip()
        cat_id   = categorias.get(cat_name, 1)
        est_raw  = (row.get("estructura") or "simple").strip().lower()
        estructura = "combo" if est_raw in ("combo", "compound") else "simple"
        productos[api_id] = prod_seq
        sql.append(
            f"INSERT INTO PRODUCTO_DULCERIA "
            f"(producto_id, api_id, nombre_producto, estructura, descripcion, imagen_url, categoria_id) "
            f"VALUES ({prod_seq}, {esc(api_id)}, {esc(nombre)}, {esc(estructura)}, "
            f"{esc(desc)}, {esc(imagen)}, {cat_id});"
        )
        prod_seq += 1
    sql.append(f"-- {len(productos)} productos")
    sql.append("")

    # ── 3. CATALOGO_COMPLEJO ──────────────────────────────────────────────────
    sql.append("-- 3. CATALOGO_COMPLEJO")
    catalogos = {}
    cat_comp_seq = 1
    for row in precios:
        slug = row.get("slug_complejo", "").strip()
        if not slug or slug in catalogos:
            continue
        complejo_id = SLUG_A_COMPLEJO_ID.get(slug)
        if complejo_id is None:
            print(f"  ⚠ slug sin mapeo: {slug}")
            continue
        catalogos[slug] = cat_comp_seq
        sql.append(
            f"INSERT INTO CATALOGO_COMPLEJO (catalogo_id, catalogo_nombre, complejo_id) "
            f"VALUES ({cat_comp_seq}, {esc('Catálogo ' + slug)}, {complejo_id});"
        )
        cat_comp_seq += 1
    sql.append(f"-- {len(catalogos)} catálogos")
    sql.append("")

    # ── 4. DETALLE_CATALOGO ───────────────────────────────────────────────────
    sql.append("-- 4. DETALLE_CATALOGO")
    det_seq = 1
    det_omit = 0
    for row in precios:
        slug      = row.get("slug_complejo", "").strip()
        api_id    = str(row.get("id_producto", "")).strip()
        precio_v  = num(row.get("precio_mxn"))
        vendible  = "TRUE" if str(row.get("vendible","")).lower() in ("true","1") else "FALSE"
        cat_id    = catalogos.get(slug)
        prod_id   = productos.get(api_id)
        if cat_id is None or prod_id is None:
            det_omit += 1
            continue
        sql.append(
            f"INSERT INTO DETALLE_CATALOGO "
            f"(detalle_id, precio_actual, disponibilidad, catalogo_id, producto_id) "
            f"VALUES ({det_seq}, {precio_v}, {vendible}, {cat_id}, {prod_id});"
        )
        det_seq += 1
    sql.append(f"-- {det_seq-1} detalles ({det_omit} omitidos)")
    sql.append("")

    # ── 5. MODIFICADOR_REGLA ──────────────────────────────────────────────────
    sql.append("-- 5. MODIFICADOR_REGLA")
    reglas = {}
    reg_seq = 1
    for row in perso:
        api_id      = str(row.get("id_producto_padre", "")).strip()
        gru_titulo  = (row.get("grupo_titulo") or "").strip()
        mod_titulo  = (row.get("mod_titulo") or "").strip()
        mod_tipo    = (row.get("mod_tipo") or "").strip()
        clave       = (api_id, gru_titulo, mod_titulo)
        if clave in reglas:
            continue
        prod_id = productos.get(api_id)
        if prod_id is None:
            continue
        t_mod        = tipo_mod(mod_tipo)
        titulo_regla = mod_titulo or gru_titulo or "Selecciona"
        reglas[clave] = reg_seq
        sql.append(
            f"INSERT INTO MODIFICADOR_REGLA "
            f"(regla_id, producto_id, titulo_regla, tipo_modificador, min_items, max_items) "
            f"VALUES ({reg_seq}, {prod_id}, {esc(titulo_regla)}, {esc(t_mod)}, "
            f"{row.get('seleccion_minima',0)}, {row.get('seleccion_maxima',1)});"
        )
        reg_seq += 1
    sql.append(f"-- {len(reglas)} reglas")
    sql.append("")

    # ── 6. MODIFICADOR_OPCION ─────────────────────────────────────────────────
    sql.append("-- 6. MODIFICADOR_OPCION")
    opciones_vistas = set()
    opc_seq  = 1
    opc_omit = 0
    for row in perso:
        api_id      = str(row.get("id_producto_padre", "")).strip()
        gru_titulo  = (row.get("grupo_titulo") or "").strip()
        mod_titulo  = (row.get("mod_titulo") or "").strip()
        api_id_opc  = str(row.get("id_opcion", "")).strip()
        nombre_opc  = (row.get("opcion_nombre") or "").strip() or f"Opción {api_id_opc}"
        precio_ex   = num(row.get("precio_extra_mxn"))
        clave_reg   = (api_id, gru_titulo, mod_titulo)
        reg_id      = reglas.get(clave_reg)
        if reg_id is None or not api_id_opc:
            opc_omit += 1
            
            continue
        clave_opc = (reg_id, api_id_opc)
        if clave_opc in opciones_vistas:
            continue
        opciones_vistas.add(clave_opc)
        sql.append(
            f"INSERT INTO MODIFICADOR_OPCION "
            f"(opcion_id, regla_id, api_id_opcion, nombre_opcion, precio_adicional) "
            f"VALUES ({opc_seq}, {reg_id}, {esc(api_id_opc)}, {esc(nombre_opc)}, {precio_ex});"
        )
        opc_seq += 1
    sql.append(f"-- {opc_seq-1} opciones ({opc_omit} omitidas)")
    sql.append("")
    sql.append("COMMIT;")

    with open(SQL_SALIDA, "w", encoding="utf-8") as f:
        f.write("\n".join(sql))

    print(f"\n  SQL generado: {SQL_SALIDA}")
    print(f"  CATEGORIA_DULCERIA:  {len(categorias):>5}")
    print(f"  PRODUCTO_DULCERIA:   {len(productos):>5}")
    print(f"  CATALOGO_COMPLEJO:   {len(catalogos):>5}")
    print(f"  DETALLE_CATALOGO:    {det_seq-1:>5}")
    print(f"  MODIFICADOR_REGLA:   {len(reglas):>5}")
    print(f"  MODIFICADOR_OPCION:  {opc_seq-1:>5}")
    print("=" * 65)

if __name__ == "__main__":
    generar()