import csv
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
engine = create_engine(os.getenv("DATABASE_URL"))

CSV_PATH = os.path.join(os.path.dirname(__file__), "personalizaciones_maestro.csv")

with engine.connect() as conn:
    # 1. Agregar columna grupo_titulo
    conn.execute(text("""
        ALTER TABLE MODIFICADOR_REGLA
        ADD COLUMN IF NOT EXISTS grupo_titulo TEXT;
    """))
    conn.commit()
    print("[OK] Columna grupo_titulo agregada (o ya existia).")

    # 2. Leer CSV y construir mapa titulo_regla (mod_titulo) -> grupo_titulo
    # OJO: Diferentes productos pueden tener el mismo mod_titulo pero diferente grupo.
    # Necesitamos mapear (api_id_producto_padre, mod_titulo) -> grupo_titulo
    grupo_por_regla = {}
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            api_padre = row.get("id_producto_padre", "").strip()
            mod_titulo = row.get("mod_titulo", "").strip()
            grupo_titulo = row.get("grupo_titulo", "").strip()
            
            if api_padre and mod_titulo and grupo_titulo:
                grupo_por_regla[(api_padre, mod_titulo)] = grupo_titulo

    print(f"[OK] {len(grupo_por_regla)} mapeos unicos encontrados en el CSV.")

    # 3. Obtener las reglas actuales de la BD (con el api_id_padre que podemos obtener cruzando tablas)
    # MODIFICADOR_REGLA tiene producto_id. PRODUCTO_DULCERIA tiene api_id.
    reglas_db = conn.execute(text("""
        SELECT mr.regla_id, pd.api_id, mr.titulo_regla
        FROM MODIFICADOR_REGLA mr
        JOIN PRODUCTO_DULCERIA pd ON mr.producto_id = pd.producto_id
    """)).fetchall()

    actualizados = 0
    for r in reglas_db:
        regla_id = r[0]
        api_padre = r[1]
        titulo_regla = r[2]

        grupo = grupo_por_regla.get((api_padre, titulo_regla))
        if not grupo:
            # Fallback if no specific group title is found
            grupo = "Personaliza tu producto"
            
        conn.execute(
            text("UPDATE MODIFICADOR_REGLA SET grupo_titulo = :g WHERE regla_id = :r_id"),
            {"g": grupo, "r_id": regla_id}
        )
        actualizados += 1

    conn.commit()
    print(f"[OK] {actualizados} reglas actualizadas con grupo_titulo.")
    print("[DONE] Migracion completada.")
