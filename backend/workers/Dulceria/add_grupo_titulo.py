import csv
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
engine = create_engine(os.getenv("DATABASE_URL"))

CSV_PATH = os.path.join(os.path.dirname(__file__), "personalizaciones_maestro.csv")

with engine.connect() as conn:
    # 1. Agregar columna grupo_titulo (si no existe)
    conn.execute(text("""
        ALTER TABLE MODIFICADOR_REGLA
        ADD COLUMN IF NOT EXISTS grupo_titulo TEXT;
    """))
    conn.commit()

    # 2. Leer CSV y construir mapa id_opcion (api_id_opcion) -> grupo_titulo
    # Esto es mucho más preciso porque las opciones son únicas, mientras que el título de la regla se repite.
    grupo_por_opcion = {}
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            id_opcion = row.get("id_opcion", "").strip()
            grupo_titulo = row.get("grupo_titulo", "").strip()
            
            if id_opcion and grupo_titulo:
                grupo_por_opcion[id_opcion] = grupo_titulo

    print(f"[OK] {len(grupo_por_opcion)} mapeos de opciones unicas encontrados en el CSV.")

    # 3. Obtener las reglas actuales y sus opciones de la BD
    reglas_db = conn.execute(text("""
        SELECT mr.regla_id, mo.api_id_opcion
        FROM MODIFICADOR_REGLA mr
        LEFT JOIN MODIFICADOR_OPCION mo ON mr.regla_id = mo.regla_id
    """)).fetchall()

    # Agrupar por regla_id
    opciones_por_regla = {}
    for r in reglas_db:
        regla_id = r[0]
        api_id_opcion = r[1]
        if regla_id not in opciones_por_regla:
            opciones_por_regla[regla_id] = []
        if api_id_opcion:
            opciones_por_regla[regla_id].append(api_id_opcion)

    actualizados = 0
    for regla_id, opciones in opciones_por_regla.items():
        grupo = None
        # Buscar el grupo usando cualquiera de las opciones de esta regla
        for api_id_opcion in opciones:
            if api_id_opcion in grupo_por_opcion:
                grupo = grupo_por_opcion[api_id_opcion]
                break # Encontramos el grupo, ya no necesitamos checar más opciones
        
        if not grupo:
            grupo = "Personaliza tu producto"
            
        conn.execute(
            text("UPDATE MODIFICADOR_REGLA SET grupo_titulo = :g WHERE regla_id = :r_id"),
            {"g": grupo, "r_id": regla_id}
        )
        actualizados += 1

    conn.commit()
    print(f"[OK] {actualizados} reglas actualizadas con grupo_titulo corregido.")
    print("[DONE] Migracion completada.")
