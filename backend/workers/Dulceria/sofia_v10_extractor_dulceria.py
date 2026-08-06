"""
=============================================================================
SOFÍA V10: CATÁLOGO COMPLETO — Multi-Complejo + Deduplicación Inteligente
=============================================================================
ESTRATEGIA: Opción C
  • Itera los 19 complejos de Veracruz uno por uno
  • Deduplica productos por id_producto (maestro limpio)
  • Registra precios por complejo en archivo separado
  • Las personalizaciones son globales (no cambian por complejo)

FLUJO POR CADA COMPLEJO (3 fases):
  Fase 1 → MenuByType          : IDs del catálogo activo en ese complejo
  Fase 2 → BatchProducts (lotes 50): metadatos + settings/modifierProductList
  Fase 3 → BatchProducts (mods): nombre y precio de cada opción

SALIDA:
  • productos_maestro.csv        — un producto único por fila (metadatos)
  • precios_por_complejo.csv     — precio × complejo para cada producto
  • personalizaciones_maestro.csv — opciones de personalización por producto
=============================================================================
"""

import csv
import sys
import time
import random

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

CSV_MAESTRO         = "productos_maestro.csv"
CSV_PRECIOS         = "precios_por_complejo.csv"
CSV_PERSONALIZACION = "personalizaciones_maestro.csv"

# 19 complejos de Veracruz: cinema_id → slug (para identificación en CSV)
COMPLEJOS = [
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
    if not path: return ""
    return f"https://cinepolis.com{path}" if path.startswith("/") else path

def delay_aleatorio(min_s=2.0, max_s=4.5):
    t = random.uniform(min_s, max_s)
    time.sleep(t)

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
    """Fase 1: obtiene IDs activos del menú de un complejo."""
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
    """Fase 2/3: BatchProducts paginado en lotes para evitar error GraphQL en catálogos grandes."""
    resultados = []
    lotes = [ids[i:i+tamano_lote] for i in range(0, len(ids), tamano_lote)]
    for lote in lotes:
        data = post_graphql(session, headers, "BatchProducts",
            {"country": "MX", "cinema": cinema_id, "products": lote},
            QUERY_BATCH)
        resultados.extend(data.get("batchProducts") or [])
        if len(lotes) > 1:
            delay_aleatorio(0.8, 1.8)
    return resultados

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def extraer():
    print("═" * 70)
    print("  SOFÍA V10: Extracción Multi-Complejo con Deduplicación Inteligente")
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

    session = cffi_requests.Session()

    # ── Acumuladores globales ──────────────────────────────────────────────────
    productos_maestro     = {}   # id_producto → dict de metadatos
    precios_por_complejo  = []   # [{cinema_id, slug, id_producto, precio, activo, vendible}]
    ids_mods_global       = set() # todos los IDs de modificadores vistos
    mods_por_producto     = {}   # id_producto → lista de filas de personalizacion (sin info de mod aún)

    # ── Iterar complejos ───────────────────────────────────────────────────────
    for idx, (cinema_id, slug) in enumerate(COMPLEJOS, 1):
        print(f"\n  [{idx:02d}/{len(COMPLEJOS)}] {slug} (cinema_id={cinema_id})")

        # Fase 1: IDs del menú activo
        try:
            ids = extraer_ids_menu(session, headers, cinema_id)
            print(f"    ✓ Fase 1: {len(ids)} productos activos en menú")
        except Exception as e:
            print(f"    ❌ Fase 1 falló: {e} — saltando complejo")
            delay_aleatorio()
            continue

        delay_aleatorio(1.0, 2.5)

        # Fase 2: Detalle de productos (paginado en lotes de 50)
        n_lotes = (len(ids) + 49) // 50
        lote_info = f" en {n_lotes} lote{'s' if n_lotes > 1 else ''}" if n_lotes > 1 else ""
        try:
            productos_raw = extraer_batch(session, headers, cinema_id, ids)
            print(f"    ✓ Fase 2: {len(productos_raw)} productos descargados{lote_info}")
        except Exception as e:
            print(f"    ❌ Fase 2 falló: {e} — saltando complejo")
            delay_aleatorio()
            continue

        # Procesar cada producto
        for prod in productos_raw:
            pid = str(prod.get("product", ""))
            web = ((prod.get("resource") or {}).get("web") or {})

            # ── Maestro: solo si no lo hemos visto ───────────────────────────
            if pid not in productos_maestro:
                productos_maestro[pid] = {
                    "id_producto":  pid,
                    "nombre":       limpiar(prod.get("productName")),
                    "ingrediente":  limpiar(prod.get("ingredientName")),
                    "categoria":    limpiar(prod.get("category")),
                    "subcategoria": limpiar(prod.get("subCategory")),
                    "estructura":   limpiar(prod.get("productStructure")),
                    "tipo":         limpiar(prod.get("productType")),
                    "promocion":    limpiar(prod.get("promotionType")),
                    "tag":          limpiar(prod.get("tag")),
                    "descripcion":  limpiar(prod.get("productDescription")),
                    "img_normal":   img(web.get("normal")),
                    "img_wide":     img(web.get("wide")),
                    "img_promo":    img(web.get("promotional")),
                    "primer_complejo_visto": slug,
                }

            # ── Precios: siempre se registra por complejo ─────────────────────
            precios_por_complejo.append({
                "cinema_id":    cinema_id,
                "slug_complejo": slug,
                "id_producto":  pid,
                "precio_mxn":   precio(prod.get("price")),
                "descuento":    precio(prod.get("discount")),
                "activo":       prod.get("active", False),
                "vendible":     prod.get("sellable", False),
            })

            # ── Recolectar IDs de modificadores ──────────────────────────────
            if pid not in mods_por_producto:
                # Solo necesitamos guardar la estructura de settings una vez
                mods_por_producto[pid] = prod.get("settings") or []
                for setting in prod.get("settings") or []:
                    for mod in setting.get("modifierList") or []:
                        for mid in mod.get("modifierProductList") or []:
                            ids_mods_global.add(str(mid))
                for ref in prod.get("references") or []:
                    for mid in ref.get("modifierProductList") or []:
                        ids_mods_global.add(str(mid))

        delay_aleatorio()

    # ── Fase 3: Resolver modificadores (una sola vez, global) ─────────────────
    mapa_mods = {}
    if ids_mods_global:
        print(f"\n  [Fase 3/Global] Resolviendo {len(ids_mods_global)} opciones de modificador...")
        # Usamos el primer complejo (Acaya) como contexto de resolución
        cinema_semilla = COMPLEJOS[0][0]
        lista_mods = list(ids_mods_global)
        lotes = [lista_mods[i:i+50] for i in range(0, len(lista_mods), 50)]

        for i, lote in enumerate(lotes, 1):
            print(f"    Lote {i}/{len(lotes)} ({len(lote)} IDs)...")
            try:
                data3 = extraer_batch(session, headers, cinema_semilla, lote)
                for m in data3:
                    mapa_mods[str(m["product"])] = {
                        "nombre":       limpiar(m.get("productName")),
                        "ingrediente":  limpiar(m.get("ingredientName")),
                        "precio_extra": precio(m.get("price")),
                        "descuento":    precio(m.get("discount")),
                        "tipo":         limpiar(m.get("productType")),
                        "estructura":   limpiar(m.get("productStructure")),
                        "img_normal":   img((m.get("resource") or {}).get("web", {}).get("normal")),
                    }
            except Exception as e:
                print(f"    ⚠ Lote {i} falló: {e}")
            delay_aleatorio(0.5, 1.5)

        print(f"  ✓ {len(mapa_mods)} opciones resueltas.")
    else:
        print("\n  [Fase 3] Sin modificadores que resolver.")

    # ── Construir CSV de personalizaciones ────────────────────────────────────
    filas_personalizaciones = []
    for pid, settings in mods_por_producto.items():
        for setting in settings:
            grupo_titulo = limpiar(setting.get("title"))
            grupo_subtit = limpiar(setting.get("subtitle"))
            grupo_tipo   = limpiar(setting.get("type"))
            grupo_orden  = setting.get("order", 0)

            for mod in setting.get("modifierList") or []:
                mod_titulo = limpiar(mod.get("title"))
                mod_subtit = limpiar(mod.get("subtitle"))
                mod_tipo   = limpiar(mod.get("type"))
                mod_orden  = mod.get("order", 0)
                reglas     = mod.get("rules") or {}
                min_sel    = reglas.get("min", 0)
                max_sel    = reglas.get("max", 1)
                defaults   = ", ".join(str(d) for d in (mod.get("defaults") or []))
                has_rules  = mod.get("hasRules", False)

                for opt_id in mod.get("modifierProductList") or []:
                    opt_id = str(opt_id)
                    info = mapa_mods.get(opt_id, {})
                    es_default = opt_id in (mod.get("defaults") or [])

                    filas_personalizaciones.append({
                        "id_producto_padre":  pid,
                        "grupo_titulo":       grupo_titulo,
                        "grupo_subtitulo":    grupo_subtit,
                        "grupo_tipo":         grupo_tipo,
                        "grupo_orden":        grupo_orden,
                        "mod_titulo":         mod_titulo,
                        "mod_subtitulo":      mod_subtit,
                        "mod_tipo":           mod_tipo,
                        "mod_orden":          mod_orden,
                        "seleccion_minima":   min_sel,
                        "seleccion_maxima":   max_sel,
                        "tiene_reglas":       has_rules,
                        "defaults_ids":       defaults,
                        "id_opcion":          opt_id,
                        "es_default":         es_default,
                        "opcion_nombre":      info.get("nombre", ""),
                        "opcion_ingrediente": info.get("ingrediente", ""),
                        "opcion_tipo":        info.get("tipo", ""),
                        "opcion_estructura":  info.get("estructura", ""),
                        "precio_extra_mxn":   info.get("precio_extra", 0.0),
                        "descuento_mxn":      info.get("descuento", 0.0),
                        "opcion_imagen":      info.get("img_normal", ""),
                    })

    # ── Guardar CSVs ──────────────────────────────────────────────────────────
    lista_maestro = list(productos_maestro.values())

    if lista_maestro:
        with open(CSV_MAESTRO, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=lista_maestro[0].keys())
            w.writeheader(); w.writerows(lista_maestro)

    if precios_por_complejo:
        with open(CSV_PRECIOS, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=precios_por_complejo[0].keys())
            w.writeheader(); w.writerows(precios_por_complejo)

    if filas_personalizaciones:
        with open(CSV_PERSONALIZACION, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=filas_personalizaciones[0].keys())
            w.writeheader(); w.writerows(filas_personalizaciones)

    # ── Resumen final ─────────────────────────────────────────────────────────
    print("\n" + "═" * 70)
    print("  ✅ Extracción completada.")
    print(f"  📄 {CSV_MAESTRO:<35} → {len(lista_maestro):>4} productos únicos")
    print(f"  📄 {CSV_PRECIOS:<35} → {len(precios_por_complejo):>4} registros precio×complejo")
    print(f"  📄 {CSV_PERSONALIZACION:<35} → {len(filas_personalizaciones):>4} opciones de personalización")

    # Estadísticas de cobertura
    print(f"\n  Cobertura por complejo:")
    conteo = {}
    for r in precios_por_complejo:
        k = r["slug_complejo"]
        conteo[k] = conteo.get(k, 0) + 1
    for slug, n in conteo.items():
        print(f"    • {slug:<50} {n:>3} productos")

    # Tipos de modificador encontrados
    tipos = {}
    for f in filas_personalizaciones:
        k = f["mod_tipo"] or "sin_tipo"
        tipos[k] = tipos.get(k, 0) + 1
    if tipos:
        print("\n  Tipos de modificador encontrados:")
        for t, n in sorted(tipos.items(), key=lambda x: -x[1]):
            print(f"    • {t}: {n} opciones")
    print("═" * 70)


if __name__ == "__main__":
    extraer()