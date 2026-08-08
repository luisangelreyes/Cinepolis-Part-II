"""
=============================================================================
SOFÍA V11: EXTRACTOR INCREMENTAL CON UPSERT DIRECTO A BD
=============================================================================
ESTRATEGIA:
  • Itera los 19 complejos uno por uno
  • Fase 1 → MenuByType: IDs activos del complejo
  • Fase 2 → BatchProducts (lotes 50): metadata + precios → UPSERT a BD
            Marca como disponibilidad=FALSE productos que ya no están en menú
  • Fase 3 → BatchProducts de modificadores DE ESTE COMPLEJO:
            UPSERT global en MODIFICADOR_OPCION
            UPSERT por cine en DISPONIBILIDAD_MODIFICADOR (activo + precio_extra)
  • Si precio cambió → INSERT en HISTORIAL_PRECIO_DULCERIA

DIFERENCIAS VS V10:
  ✓ Escribe directo a PostgreSQL (sin CSVs intermedios)
  ✓ UPSERT en vez de TRUNCATE + INSERT
  ✓ Modificadores resueltos POR complejo (no desde semilla única)
  ✓ Historial real de cambios de precio
  ✓ Productos desaparecidos marcados como no disponibles
=============================================================================
"""

import os
import sys
import time
import random
import csv
from datetime import datetime

# Evitar errores de codificación en Windows con emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ── Cargar .env relativo al script ────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL no encontrada en .env")
    sys.exit(1)

try:
    from curl_cffi import requests as cffi_requests
    import curl_cffi
    version = tuple(int(x) for x in curl_cffi.__version__.split(".")[:2])
    IMPERSONATE = "chrome124" if version >= (0, 7) else "chrome120"
    print(f"  ✓ curl_cffi {curl_cffi.__version__} → impersonate='{IMPERSONATE}'")
except ImportError:
    print("  ❌ Instala curl_cffi:  pip install curl_cffi")
    sys.exit(1)

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
API_KEY = "lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo"
API_URL = "https://api-g.cinepolis.com/v1/fab-struct-concession/graphql"

# 19 complejos de Veracruz: cinema_id (API) → slug
CINES_API = [
    ("658",  "cinepolis-acaya-coatzacoalcos"),
    ("635",  "cinepolis-el-dorado-coatzacoalcos"),
    ("484",  "cinepolis-el-dorado-veracruz"),
    ("545",  "cinepolis-vip-el-dorado-veracruz"),
    ("260",  "cinepolis-plaza-del-puerto-veracruz"),
    ("126",  "cinepolis-las-americas-veracruz"),
    ("192",  "cinepolis-vip-las-americas-veracruz"),
    ("1103", "cinepolis-portal-veracruz"),
    ("247",  "cinepolis-plaza-las-americas-xalapa"),
    ("665",  "cinepolis-vip-las-americas-xalapa"),
    ("040",  "cinepolis-plaza-crystal-xalapa"),
    ("125",  "cinepolis-plaza-museo-xalapa"),
    ("443",  "cinepolis-plaza-shangri-la-cordoba"),
    ("388",  "cinepolis-plaza-valle-orizaba"),
    ("609",  "cinepolis-rio-blanco-orizaba"),
    ("139",  "cinepolis-plaza-minatitlan"),
    ("298",  "cinepolis-plaza-crystal-tuxpan"),
    ("611",  "cinepolis-la-florida-acayucan"),
    ("573",  "cinepolis-chedraui-martinez-de-la-torre"),
]

TIPOS_VALIDOS = {"flavor", "size", "extra", "ingredient", "popcorn", "compound"}

# ─── QUERIES ──────────────────────────────────────────────────────────────────
QUERY_MENU = """
query MenuByType(
  $country: String!, $cinema: String!, $menuType: String!,
  $category: Int, $subCategory: Int, $userSession: String!
) {
  menuByType(
    country: $country, cinema: $cinema, menuType: $menuType,
    category: $category, subCategory: $subCategory, userSession: $userSession
  ) {
    categories {
      name
      products      { product active }
      subCategories { name products { product active } }
    }
  }
}
"""

QUERY_BATCH = """
query BatchProducts($cinema: String!, $country: String!, $products: [String]!) {
  batchProducts(cinema: $cinema, country: $country, products: $products) {
    product
    active
    price
    discount
    productName
    ingredientName
    productStructure
    productType
    promotionType
    category
    subCategory
    tag
    productDescription
    sellable
    order
    catSubOrder
    categoryOrder
    productOrder
    subCategoryOrder
    resource { web { normal wide promotional icon } }
    recipes   { product modifiers }
    references {
      defaults hasRules modifierProductList order subtitle title type
      rules { max min }
    }
    settings {
      comments id order subtitle title type
      modifierList {
        defaults hasRules modifierProductList order subtitle title type
        rules { max min }
      }
    }
  }
}
"""

# ─── UTILIDADES ───────────────────────────────────────────────────────────────
def limpiar(v):
    if v is None: return ""
    return str(v).replace("\n", " ").strip()

def precio(v):
    try:    return round(float(v) / 100, 2)
    except: return 0.0

def img(path):
    if not path: return None
    return f"https://foods-static-content.cinepolis.com{path}" if path.startswith("/") else path

def tipo_mod(mod_tipo):
    t = (mod_tipo or "").strip().lower()
    return t if t in TIPOS_VALIDOS else "ingredient"

def delay_aleatorio(min_s=3.0, max_s=6.0):
    time.sleep(random.uniform(min_s, max_s))

def post_graphql(session, headers, operation, variables, query, reintentos=3):
    payload = {"operationName": operation, "variables": variables, "query": query}
    for intento in range(1, reintentos + 1):
        try:
            res = session.post(API_URL, json=payload, headers=headers,
                               impersonate=IMPERSONATE, timeout=30)
            if res.status_code == 429:
                espera = 2 ** intento + random.uniform(0, 1)
                print(f"    ⚠ 429 Rate limit. Esperando {espera:.1f}s (intento {intento}/{reintentos})...")
                time.sleep(espera)
                continue
            if res.status_code != 200:
                raise RuntimeError(f"HTTP {res.status_code}: {res.text[:300]}")
            data = res.json()
            if data.get("errors"):
                raise RuntimeError(f"GraphQL: {data['errors'][0].get('message')}")
            return data["data"]
        except RuntimeError:
            raise
        except Exception as e:
            if intento == reintentos:
                raise
            print(f"    ⚠ Error de red ({e}). Reintentando ({intento}/{reintentos})...")
            time.sleep(2 ** intento)
    raise RuntimeError("Máximo de reintentos alcanzado.")

def extraer_ids_menu(session, headers, cinema_id):
    """Fase 1: IDs activos del menú de un complejo."""
    data = post_graphql(session, headers, "MenuByType",
        {"country": "MX", "cinema": cinema_id,
         "menuType": "sellable", "userSession": ""},
        QUERY_MENU)
    ids = []
    for cat in (data.get("menuByType") or {}).get("categories", []):
        for p in cat.get("products") or []:
            if p.get("active"):
                ids.append(p["product"])
        for sub in cat.get("subCategories") or []:
            for p in sub.get("products") or []:
                if p.get("active"):
                    ids.append(p["product"])
    return list(set(ids))

def extraer_batch(session, headers, cinema_id, ids, tamano_lote=50):
    """BatchProducts paginado en lotes."""
    resultados = []
    lotes = [ids[i:i+tamano_lote] for i in range(0, len(ids), tamano_lote)]
    for lote in lotes:
        data = post_graphql(session, headers, "BatchProducts",
            {"country": "MX", "cinema": cinema_id, "products": lote},
            QUERY_BATCH)
        resultados.extend(data.get("batchProducts") or [])
        if len(lotes) > 1:
            delay_aleatorio(1.5, 3.0)
    return resultados

# ─── UPSERTS A BD ─────────────────────────────────────────────────────────────

def upsert_categoria(conn, nombre):
    """Retorna categoria_id. Crea la categoría si no existe."""
    nombre = nombre.strip() or "Sin Categoría"
    row = conn.execute(text("""
        INSERT INTO CATEGORIA_DULCERIA (nombre_categoria)
        VALUES (:n)
        ON CONFLICT (nombre_categoria) DO UPDATE SET nombre_categoria = EXCLUDED.nombre_categoria
        RETURNING categoria_id
    """), {"n": nombre}).fetchone()
    return row[0]

def upsert_catalogo(conn, complejo_id, slug):
    """Retorna catalogo_id. Crea el catálogo si no existe."""
    nombre = f"Catálogo {slug}"
    row = conn.execute(text("""
        INSERT INTO CATALOGO_COMPLEJO (catalogo_nombre, complejo_id)
        VALUES (:n, :cid)
        ON CONFLICT (complejo_id) DO UPDATE SET catalogo_nombre = EXCLUDED.catalogo_nombre
        RETURNING catalogo_id
    """), {"n": nombre, "cid": complejo_id}).fetchone()
    return row[0]

def upsert_producto(conn, prod, cat_id):
    """Retorna producto_id. Crea o actualiza el producto."""
    web = ((prod.get("resource") or {}).get("web") or {})
    est_raw = (prod.get("productStructure") or "simple").strip().lower()
    estructura = "combo" if est_raw in ("combo", "compound") else "simple"

    row = conn.execute(text("""
        INSERT INTO PRODUCTO_DULCERIA
            (api_id, nombre_producto, estructura, descripcion, imagen_url, categoria_id)
        VALUES (:api_id, :nombre, :estructura, :desc, :img, :cat_id)
        ON CONFLICT (api_id) DO UPDATE SET
            nombre_producto = EXCLUDED.nombre_producto,
            estructura      = EXCLUDED.estructura,
            descripcion     = EXCLUDED.descripcion,
            imagen_url      = EXCLUDED.imagen_url,
            categoria_id    = EXCLUDED.categoria_id
        RETURNING producto_id
    """), {
        "api_id":    str(prod.get("product", "")),
        "nombre":    limpiar(prod.get("productName")),
        "estructura": estructura,
        "desc":      limpiar(prod.get("productDescription")) or None,
        "img":       img(web.get("promotional") or web.get("normal") or web.get("wide") or web.get("icon")),
        "cat_id":    cat_id,
    }).fetchone()
    return row[0]

def upsert_detalle_catalogo(conn, prod_id, catalogo_id, precio_actual, vendible):
    """Upsert precio+disponibilidad. Retorna (detalle_id, precio_anterior_o_None)."""
    # Leer precio anterior si existe
    old = conn.execute(text("""
        SELECT detalle_id, precio_actual
        FROM DETALLE_CATALOGO
        WHERE catalogo_id = :cat AND producto_id = :pid
    """), {"cat": catalogo_id, "pid": prod_id}).fetchone()

    precio_anterior = float(old[1]) if old else None

    row = conn.execute(text("""
        INSERT INTO DETALLE_CATALOGO
            (precio_actual, disponibilidad, catalogo_id, producto_id)
        VALUES (:precio, :disp, :cat, :pid)
        ON CONFLICT (catalogo_id, producto_id) DO UPDATE SET
            precio_actual  = EXCLUDED.precio_actual,
            disponibilidad = EXCLUDED.disponibilidad
        RETURNING detalle_id
    """), {
        "precio": precio_actual,
        "disp":   vendible,
        "cat":    catalogo_id,
        "pid":    prod_id,
    }).fetchone()

    return row[0], precio_anterior

def registrar_cambio_precio(conn, prod_id, catalogo_id, precio_ant, precio_nuevo):
    conn.execute(text("""
        INSERT INTO HISTORIAL_PRECIO_DULCERIA
            (producto_id, catalogo_id, precio_anterior, precio_nuevo, registrado_en)
        VALUES (:pid, :cat, :ant, :nuevo, NOW())
    """), {
        "pid":   prod_id,
        "cat":   catalogo_id,
        "ant":   precio_ant,
        "nuevo": precio_nuevo,
    })

def marcar_no_disponibles(conn, catalogo_id, ids_activos):
    """Marca como disponibilidad=FALSE los productos ya no en el menú del complejo."""
    if not ids_activos:
        return 0
    # Necesitamos los producto_id de los api_ids activos
    rows = conn.execute(text("""
        SELECT pd.producto_id
        FROM PRODUCTO_DULCERIA pd
        WHERE pd.api_id = ANY(:ids)
    """), {"ids": ids_activos}).fetchall()
    prod_ids_activos = [r[0] for r in rows]

    if not prod_ids_activos:
        return 0

    result = conn.execute(text("""
        UPDATE DETALLE_CATALOGO
        SET disponibilidad = FALSE
        WHERE catalogo_id = :cat
          AND producto_id != ALL(:activos)
          AND disponibilidad = TRUE
    """), {"cat": catalogo_id, "activos": prod_ids_activos})
    return result.rowcount

def upsert_modificador_regla(conn, prod_id, gru_titulo, mod_titulo, mod_tipo,
                              min_sel, max_sel, grupo_orden, mod_orden):
    """Retorna regla_id."""
    titulo_regla = mod_titulo or gru_titulo or "Selecciona"
    t_mod = tipo_mod(mod_tipo)

    row = conn.execute(text("""
        INSERT INTO MODIFICADOR_REGLA
            (producto_id, titulo_regla, tipo_modificador, min_items, max_items, grupo_titulo)
        VALUES (:pid, :titulo, :tipo, :min, :max, :grupo)
        ON CONFLICT (producto_id, grupo_titulo, titulo_regla, tipo_modificador) DO UPDATE SET
            min_items   = EXCLUDED.min_items,
            max_items   = EXCLUDED.max_items
        RETURNING regla_id
    """), {
        "pid":   prod_id,
        "titulo": titulo_regla,
        "tipo":  t_mod,
        "min":   min_sel,
        "max":   max_sel,
        "grupo": gru_titulo or titulo_regla,
    }).fetchone()
    return row[0]

def upsert_modificador_opcion(conn, regla_id, opt_id, nombre, precio_extra, imagen_url):
    """Retorna opcion_id."""
    row = conn.execute(text("""
        INSERT INTO MODIFICADOR_OPCION
            (regla_id, api_id_opcion, nombre_opcion, precio_adicional, imagen_url)
        VALUES (:rid, :api_id, :nombre, :precio, :img)
        ON CONFLICT (regla_id, api_id_opcion) DO UPDATE SET
            nombre_opcion    = EXCLUDED.nombre_opcion,
            precio_adicional = EXCLUDED.precio_adicional,
            imagen_url       = COALESCE(EXCLUDED.imagen_url, MODIFICADOR_OPCION.imagen_url)
        RETURNING opcion_id
    """), {
        "rid":    regla_id,
        "api_id": opt_id,
        "nombre": nombre,
        "precio": precio_extra,
        "img":    imagen_url,
    }).fetchone()
    return row[0]

def upsert_disponibilidad_mod(conn, opcion_id, catalogo_id, activo, precio_extra):
    """Upsert de disponibilidad del modificador por complejo."""
    conn.execute(text("""
        INSERT INTO DISPONIBILIDAD_MODIFICADOR
            (opcion_id, catalogo_id, activo, precio_extra, actualizado_en)
        VALUES (:oid, :cat, :activo, :precio, NOW())
        ON CONFLICT (opcion_id, catalogo_id) DO UPDATE SET
            activo         = EXCLUDED.activo,
            precio_extra   = EXCLUDED.precio_extra,
            actualizado_en = NOW()
    """), {
        "oid":    opcion_id,
        "cat":    catalogo_id,
        "activo": activo,
        "precio": precio_extra,
    })

# ─── PROCESAMIENTO DE MODIFICADORES ──────────────────────────────────────────

def recolectar_ids_mods(productos_raw):
    """Extrae todos los IDs de modificadores de la lista de productos."""
    ids = set()
    for prod in productos_raw:
        for setting in prod.get("settings") or []:
            for mod in setting.get("modifierList") or []:
                for mid in mod.get("modifierProductList") or []:
                    ids.add(str(mid))
        for ref in prod.get("references") or []:
            for mid in ref.get("modifierProductList") or []:
                ids.add(str(mid))
    return list(ids)

def procesar_modificadores_producto(conn, prod, prod_id, catalogo_id,
                                    mods_resueltos, perso_list, api_id, slug, verbose=False):
    """
    Para un producto, crea/actualiza sus reglas y opciones de modificador,
    y registra la disponibilidad por complejo.
    También agrega la fila a perso_list para el CSV de respaldo.
    """
    n_reglas = 0
    n_opciones = 0

    for setting in prod.get("settings") or []:
        gru_titulo = limpiar(setting.get("title"))
        gru_orden  = setting.get("order", 0)

        for mod in setting.get("modifierList") or []:
            mod_titulo = limpiar(mod.get("title"))
            mod_subtit = limpiar(mod.get("subtitle"))
            mod_tipo   = limpiar(mod.get("type"))
            mod_orden  = mod.get("order", 0)
            reglas_mod = mod.get("rules") or {}
            min_sel    = reglas_mod.get("min", 0)
            max_sel    = reglas_mod.get("max", 1)
            defaults   = ", ".join(str(d) for d in (mod.get("defaults") or []))
            has_rules  = mod.get("hasRules", False)

            # --- NUEVA LÓGICA DE NEGOCIO PARA PRECIOS DE COMBOS ---
            # Si el producto padre es un combo, los tamaños de los items (size) no deben
            # sumar el precio absoluto a la cuenta, sino solo la diferencia (upsize).
            min_size_price = 0.0
            if prod.get("productStructure") in ("combo", "compound") and mod_tipo == "size":
                precios_opt = []
                for opt_id in mod.get("modifierProductList") or []:
                    opt_info = mods_resueltos.get(str(opt_id), {})
                    precios_opt.append(opt_info.get("precio_extra", 0.0))
                if precios_opt:
                    min_size_price = min(precios_opt)

            regla_id = upsert_modificador_regla(
                conn, prod_id,
                gru_titulo, mod_titulo, mod_tipo,
                min_sel, max_sel, gru_orden, mod_orden
            )
            n_reglas += 1

            for opt_id in mod.get("modifierProductList") or []:
                opt_id = str(opt_id)
                info   = mods_resueltos.get(opt_id, {})
                nombre = info.get("nombre") or f"Opción {opt_id}"
                precio_extra = info.get("precio_extra", 0.0)
                
                # Descontar el precio base del combo en caso de ser "size"
                if prod.get("productStructure") in ("combo", "compound") and mod_tipo == "size":
                    precio_extra = max(0.0, precio_extra - min_size_price)

                activo = info.get("activo", True)
                imagen = info.get("img_icon") or info.get("img_normal")
                es_default = opt_id in (mod.get("defaults") or [])

                opcion_id = upsert_modificador_opcion(
                    conn, regla_id, opt_id, nombre, precio_extra, imagen
                )
                upsert_disponibilidad_mod(
                    conn, opcion_id, catalogo_id, activo, precio_extra
                )
                
                # Para el CSV de respaldo
                perso_list.append({
                    "slug_complejo":      slug,
                    "id_producto_padre":  api_id,
                    "grupo_titulo":       gru_titulo,
                    "mod_titulo":         mod_titulo,
                    "mod_tipo":           mod_tipo,
                    "seleccion_minima":   min_sel,
                    "seleccion_maxima":   max_sel,
                    "tiene_reglas":       has_rules,
                    "defaults_ids":       defaults,
                    "id_opcion":          opt_id,
                    "es_default":         es_default,
                    "opcion_nombre":      nombre,
                    "opcion_ingrediente": info.get("ingrediente", ""),
                    "opcion_activa":      activo,
                    "precio_extra_mxn":   precio_extra,
                    "opcion_imagen":      imagen,
                })
                
                n_opciones += 1

    return n_reglas, n_opciones

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def extraer():
    print("═" * 70)
    print("  SOFÍA V11: Extracción Incremental — UPSERT directo a BD")
    print(f"  Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 70)

    headers = {
        "accept": "*/*", "content-type": "application/json",
        "country-id": "MX", "origin": "https://cinepolis.com",
        "referer": "https://cinepolis.com/",
        "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36"),
        "x-apikey": API_KEY,
    }

    session    = cffi_requests.Session()
    engine     = create_engine(DATABASE_URL)

    stats = {
        "complejos_ok": 0,
        "complejos_fail": 0,
        "productos_upsert": 0,
        "precios_cambiados": 0,
        "no_disponibles": 0,
        "reglas_upsert": 0,
        "opciones_upsert": 0,
    }

    # Cargar mapeo dinámico de complejos
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT complejo_id, slug FROM COMPLEJO")).fetchall()
        mapa_complejos = {row.slug: row.complejo_id for row in rows}

    # Acumuladores CSV de respaldo
    csv_maestro = {}
    csv_precios = []
    csv_perso   = []

    for idx, (cinema_id, slug) in enumerate(CINES_API, 1):
        complejo_id = mapa_complejos.get(slug)
        if not complejo_id:
            print(f"\n  [{idx:02d}/{len(CINES_API)}] ❌ Error: El complejo {slug} no existe en la base de datos local.")
            stats["complejos_fail"] += 1
            continue

        print(f"\n  [{idx:02d}/{len(CINES_API)}] {slug}  (cinema_id={cinema_id} -> complejo_id={complejo_id})")

        # ── Fase 1: IDs activos en el menú ────────────────────────────────────
        try:
            ids_menu = extraer_ids_menu(session, headers, cinema_id)
            print(f"    ✓ Fase 1: {len(ids_menu)} productos activos")
        except Exception as e:
            print(f"    ❌ Fase 1 falló: {e} — saltando")
            stats["complejos_fail"] += 1
            delay_aleatorio()
            continue

        delay_aleatorio(2.0, 4.0)

        # ── Fase 2: Detalle de productos ─────────────────────────────────────
        try:
            productos_raw = extraer_batch(session, headers, cinema_id, ids_menu)
            print(f"    ✓ Fase 2: {len(productos_raw)} productos descargados")
        except Exception as e:
            print(f"    ❌ Fase 2 falló: {e} — saltando")
            stats["complejos_fail"] += 1
            delay_aleatorio()
            continue

        # ── Fase 3: Modificadores de ESTE complejo ────────────────────────────
        ids_mods = recolectar_ids_mods(productos_raw)
        mods_resueltos = {}

        if ids_mods:
            print(f"    → Fase 3: resolviendo {len(ids_mods)} modificadores...")
            try:
                mods_raw = extraer_batch(session, headers, cinema_id, ids_mods)
                for m in mods_raw:
                    web_m = ((m.get("resource") or {}).get("web") or {})
                    mods_resueltos[str(m["product"])] = {
                        "nombre":       limpiar(m.get("productName")),
                        "ingrediente":  limpiar(m.get("ingredientName")),
                        "precio_extra": precio(m.get("price")),
                        "descuento":    precio(m.get("discount")),
                        "tipo":         limpiar(m.get("productType")),
                        "estructura":   limpiar(m.get("productStructure")),
                        "activo":       m.get("active", True),
                        "img_normal":   img(web_m.get("promotional") or web_m.get("normal") or web_m.get("wide")),
                        "img_icon":     img(web_m.get("icon")),
                    }
                print(f"    ✓ Fase 3: {len(mods_resueltos)} modificadores resueltos")
            except Exception as e:
                print(f"    ⚠ Fase 3 falló: {e} — modificadores sin resolver")

        # ── Escribir a BD ──────────────────────────────────────────────────────
        with engine.connect() as conn:
            # Asegurar que el catálogo del complejo existe
            catalogo_id = upsert_catalogo(conn, complejo_id, slug)

            n_prods       = 0
            n_precios_ok  = 0
            n_reglas      = 0
            n_opciones    = 0

            for prod in productos_raw:
                api_id = str(prod.get("product", ""))
                if not api_id:
                    continue

                web = ((prod.get("resource") or {}).get("web") or {})
                cat_nombre = (prod.get("category") or "Sin Categoría").strip() or "Sin Categoría"

                # UPSERT categoría y producto
                cat_id  = upsert_categoria(conn, cat_nombre)
                prod_id = upsert_producto(conn, prod, cat_id)

                # UPSERT precio por complejo
                precio_actual = precio(prod.get("price"))
                vendible      = bool(prod.get("sellable", False))
                det_id, precio_ant = upsert_detalle_catalogo(
                    conn, prod_id, catalogo_id, precio_actual, vendible
                )

                # Detectar cambio de precio
                if precio_ant is not None and round(precio_ant, 2) != round(precio_actual, 2):
                    registrar_cambio_precio(conn, prod_id, catalogo_id, precio_ant, precio_actual)
                    n_precios_ok += 1

                # Modificadores para este producto en este complejo
                r, o = procesar_modificadores_producto(
                    conn, prod, prod_id, catalogo_id, mods_resueltos, csv_perso, api_id, slug
                )
                
                # Llenar CSV Maestro
                if api_id not in csv_maestro:
                    est_raw = (prod.get("productStructure") or "simple").strip().lower()
                    csv_maestro[api_id] = {
                        "id_producto": api_id,
                        "nombre": limpiar(prod.get("productName")),
                        "ingrediente": limpiar(prod.get("ingredientName")),
                        "categoria": cat_nombre,
                        "subcategoria": limpiar(prod.get("subCategory")),
                        "estructura": "combo" if est_raw in ("combo", "compound") else "simple",
                        "tipo": limpiar(prod.get("productType")),
                        "descripcion": limpiar(prod.get("productDescription")),
                        "order": prod.get("order"),
                        "category_order": prod.get("categoryOrder"),
                        "cat_sub_order": prod.get("catSubOrder"),
                        "product_order": prod.get("productOrder"),
                        "sub_category_order": prod.get("subCategoryOrder"),
                        "img_normal": img(web.get("normal")),
                        "img_wide": img(web.get("wide")),
                        "img_promo": img(web.get("promotional")),
                        "img_icon": img(web.get("icon")),
                    }

                # Llenar CSV Precios
                csv_precios.append({
                    "cinema_id": cinema_id,
                    "slug_complejo": slug,
                    "id_producto": api_id,
                    "precio_mxn": precio_actual,
                    "vendible": vendible,
                })
                
                n_reglas   += r
                n_opciones += o
                n_prods    += 1

            # Marcar no disponibles los que ya no están en el menú
            n_baja = marcar_no_disponibles(conn, catalogo_id, ids_menu)

            conn.commit()

        stats["complejos_ok"]      += 1
        stats["productos_upsert"]  += n_prods
        stats["precios_cambiados"] += n_precios_ok
        stats["no_disponibles"]    += n_baja
        stats["reglas_upsert"]     += n_reglas
        stats["opciones_upsert"]   += n_opciones

        print(f"    ✅ {n_prods} productos · {n_precios_ok} precios cambiados"
              f" · {n_baja} dados de baja · {n_reglas} reglas · {n_opciones} opciones")

        delay_aleatorio()

    # ── Guardar CSVs de respaldo ──────────────────────────────────────────────
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    
    lista_maestro = list(csv_maestro.values())
    if lista_maestro:
        path = os.path.join(BASE_DIR, f"respaldo_productos_v11.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=lista_maestro[0].keys())
            w.writeheader(); w.writerows(lista_maestro)

    if csv_precios:
        path = os.path.join(BASE_DIR, f"respaldo_precios_v11.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=csv_precios[0].keys())
            w.writeheader(); w.writerows(csv_precios)

    if csv_perso:
        path = os.path.join(BASE_DIR, f"respaldo_personalizaciones_v11.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=csv_perso[0].keys())
            w.writeheader(); w.writerows(csv_perso)

    # ── Resumen final ─────────────────────────────────────────────────────────
    print("\n" + "═" * 70)
    print("  ✅ Extracción V11 completada.")
    print(f"  Complejos OK:           {stats['complejos_ok']:>4}")
    print(f"  Complejos con error:    {stats['complejos_fail']:>4}")
    print(f"  Productos upsert:       {stats['productos_upsert']:>4}")
    print(f"  Cambios de precio:      {stats['precios_cambiados']:>4}")
    print(f"  Dados de baja:          {stats['no_disponibles']:>4}")
    print(f"  Reglas de mod upsert:   {stats['reglas_upsert']:>4}")
    print(f"  Opciones de mod upsert: {stats['opciones_upsert']:>4}")
    print("═" * 70)


if __name__ == "__main__":
    extraer()
