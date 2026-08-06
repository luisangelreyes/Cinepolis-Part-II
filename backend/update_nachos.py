import pandas as pd
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:1234@localhost:5432/secret_wars"
engine = create_engine(db_url)

target_url = "https://foods-static-content.cinepolis.com/redesign/MX/menus/tradicional/extra_queso_small.png"

with engine.begin() as conn:
    # Update products that have 'nachos' in the name
    result = conn.execute(
        text("UPDATE PRODUCTO_DULCERIA SET imagen_url = :url WHERE nombre_producto ILIKE '%nachos%'"),
        {"url": target_url}
    )
    print(f"Successfully updated {result.rowcount} product images for Nachos!")
