import pandas as pd
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:1234@localhost:5432/secret_wars"
engine = create_engine(db_url)

df = pd.read_csv("productos_maestro.csv")
df = df.dropna(subset=['img_normal'])

updates_hechas = 0
with engine.begin() as conn:
    for idx, row in df.iterrows():
        nombre = row['nombre']
        img = row['img_normal']
        
        # Replace the domain with the working static domain
        new_img = img.replace("https://cinepolis.com", "https://foods-static-content.cinepolis.com")
        
        result = conn.execute(
            text("UPDATE PRODUCTO_DULCERIA SET imagen_url = :img WHERE nombre_producto = :nombre"),
            {"img": new_img, "nombre": nombre}
        )
        updates_hechas += result.rowcount
        
print(f"Updates realizadas: {updates_hechas} registros modificados (cambiados a foods-static-content).")
