"""
Migración: agrega columna imagen_url a MODIFICADOR_OPCION
y la llena desde personalizaciones_maestro.csv usando api_id_opcion como llave.
"""
import csv
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))
engine = create_engine(os.getenv("DATABASE_URL"))

CSV_PATH = os.path.join(os.path.dirname(__file__), "personalizaciones_maestro.csv")

with engine.connect() as conn:
    # 1. Agregar columna si no existe
    conn.execute(text("""
        ALTER TABLE MODIFICADOR_OPCION
        ADD COLUMN IF NOT EXISTS imagen_url TEXT;
    """))
    conn.commit()
    print("[OK] Columna imagen_url agregada (o ya existia).")

    # 2. Leer CSV y construir mapa api_id → imagen_url
    imagen_por_api_id: dict[str, str] = {}
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            api_id = row.get("id_opcion", "").strip()
            url    = row.get("opcion_imagen", "").strip()
            if api_id and url:
                imagen_por_api_id[api_id] = url

    print(f"[OK] {len(imagen_por_api_id)} imagenes unicas en el CSV.")

    # 3. Actualizar la tabla
    actualizados = 0
    sin_imagen   = 0
    for api_id, url in imagen_por_api_id.items():
        result = conn.execute(
            text("UPDATE MODIFICADOR_OPCION SET imagen_url = :url WHERE api_id_opcion = :api_id"),
            {"url": url, "api_id": api_id}
        )
        if result.rowcount > 0:
            actualizados += result.rowcount
        else:
            sin_imagen += 1
    conn.commit()

    print(f"[OK] {actualizados} opciones actualizadas con imagen.")
    print(f"  {sin_imagen} IDs del CSV no tenian fila en MODIFICADOR_OPCION (normal, son opciones de otros complejos).")

    # 4. Reporte de cobertura
    total = conn.execute(text("SELECT COUNT(*) FROM MODIFICADOR_OPCION")).scalar()
    con_img = conn.execute(text("SELECT COUNT(*) FROM MODIFICADOR_OPCION WHERE imagen_url IS NOT NULL AND imagen_url != ''")).scalar()
    print(f"\n  Cobertura final: {con_img}/{total} opciones tienen imagen ({100*con_img//total if total else 0}%).")
    print("\n[DONE] Migracion completada.")
