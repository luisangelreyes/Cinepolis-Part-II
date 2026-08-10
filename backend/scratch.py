import json
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:1234@localhost:5432/secret_wars')

# Step 1: Get all complexes from DB
with engine.connect() as conn:
    db_complejos = conn.execute(text("SELECT complejo_id, slug FROM COMPLEJO ORDER BY complejo_id")).fetchall()
    print("=== COMPLEJOS EN LA BD ===")
    for row in db_complejos:
        print(f"  DB complejo_id={row.complejo_id:3d} | {row.slug}")

# Step 2: Extract vista_id -> slug mapping from the JSON
print("\n=== MAPEO DEL JSON (vista_id -> slug) ===")
with open('cartelera_veracruz_completa.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

vista_to_slug = {}
for fun in data.get('funciones', []):
    vid = fun.get('cinema_vista_id')
    slug = fun.get('complejo_slug')
    if vid and slug:
        vista_to_slug[vid] = slug

for vid, slug in sorted(vista_to_slug.items(), key=lambda x: int(x[0])):
    print(f"  vista_id={vid:5s} | {slug}")

# Step 3: Cross-reference — find the CORRECT complejo_id for each vista_id
print("\n=== MAPEO CORRECTO PARA COMPLEJO_VISTA_IDS ===")
slug_to_db_id = {row.slug: row.complejo_id for row in db_complejos}

for vid, slug in sorted(vista_to_slug.items(), key=lambda x: int(x[0])):
    db_id = slug_to_db_id.get(slug, "??? NO ENCONTRADO EN BD")
    print(f"  ({db_id}, '{vid}', '{slug}'),")
