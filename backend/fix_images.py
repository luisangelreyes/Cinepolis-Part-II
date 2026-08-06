import pandas as pd
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:1234@localhost:5432/secret_wars"
engine = create_engine(db_url)

# High quality Unsplash placeholders
IMG_PALOMITAS = "https://images.unsplash.com/photo-1585647347384-259e5ac37a09?auto=format&fit=crop&w=400&q=80"
IMG_NACHOS = "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=400&q=80"
IMG_HOTDOG = "https://images.unsplash.com/photo-1619740455993-9e612b1af08a?auto=format&fit=crop&w=400&q=80"
IMG_SODA = "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?auto=format&fit=crop&w=400&q=80"
IMG_ICEE = "https://images.unsplash.com/photo-1556881286-fc6915169721?auto=format&fit=crop&w=400&q=80"
IMG_AGUA = "https://images.unsplash.com/photo-1523362628745-0c100150b504?auto=format&fit=crop&w=400&q=80"
IMG_CAFE = "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=400&q=80"
IMG_DULCES = "https://images.unsplash.com/photo-1582058091505-f87a2e55a40f?auto=format&fit=crop&w=400&q=80"
IMG_HELADO = "https://images.unsplash.com/photo-1570197781417-0a523b12384a?auto=format&fit=crop&w=400&q=80"
IMG_COMBO = "https://images.unsplash.com/photo-1662991060938-f1c5c7db81ee?auto=format&fit=crop&w=400&q=80"
IMG_DEFAULT = "https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=400&q=80" # Movie items

def get_img_for_name(name: str):
    name = name.lower()
    if "palomitas" in name or "popcorn" in name: return IMG_PALOMITAS
    if "nachos" in name: return IMG_NACHOS
    if "hot dog" in name or "jocho" in name: return IMG_HOTDOG
    if "refresco" in name or "coca" in name or "sprite" in name or "fanta" in name or "mundet" in name: return IMG_SODA
    if "icee" in name or "frappe" in name or "frappé" in name: return IMG_ICEE
    if "agua" in name or "ciel" in name or "fuze" in name: return IMG_AGUA
    if "café" in name or "cafe" in name or "latte" in name or "mocha" in name or "capuchino" in name: return IMG_CAFE
    if "helado" in name or "mordisko" in name or "cornetto" in name or "magnum" in name: return IMG_HELADO
    if "combo" in name or "maxicombo" in name or "cuates" in name: return IMG_COMBO
    if "skittles" in name or "milky" in name or "m&m" in name or "snickers" in name or "pelon" in name or "lucas" in name or "kinder" in name or "hershey" in name or "takis" in name or "doritos" in name or "cheetos" in name or "panditas" in name or "aritos" in name: return IMG_DULCES
    return IMG_DEFAULT

with engine.begin() as conn:
    # Get all products
    result = conn.execute(text("SELECT producto_id, nombre_producto FROM PRODUCTO_DULCERIA")).fetchall()
    print(f"Updating {len(result)} products with Unsplash placeholders...")
    
    count = 0
    for row in result:
        pid = row.producto_id
        pname = row.nombre_producto
        img = get_img_for_name(pname)
        
        conn.execute(
            text("UPDATE PRODUCTO_DULCERIA SET imagen_url = :img WHERE producto_id = :pid"),
            {"img": img, "pid": pid}
        )
        count += 1
        
    print(f"Successfully updated {count} product images!")
