"""
Script de prueba para ver qué devuelve exactamente la API de Cinépolis
para M&M's® Mega standalone en El Dorado Veracruz (cinema=484) y en Plaza Museo Xalapa (cinema=125).
"""
import os, sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print("Instala curl_cffi: pip install curl_cffi")
    sys.exit(1)

API_KEY = "lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo"
API_URL = "https://api-g.cinepolis.com/v1/fab-struct-concession/graphql"

QUERY_BATCH = """
query BatchProducts($cinema: String!, $country: String!, $products: [String]!) {
  batchProducts(cinema: $cinema, country: $country, products: $products) {
    product price productName productStructure
    settings {
      title order
      modifierList {
        title type order
        rules { max min }
        defaults modifierProductList
      }
    }
  }
}
"""

headers = {
    "accept": "*/*", "content-type": "application/json",
    "country-id": "MX", "origin": "https://cinepolis.com",
    "referer": "https://cinepolis.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "x-apikey": API_KEY,
}

# IDs conocidos de M&M's® Mega (los api_ids que tenemos en la BD)
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    res = conn.execute(text("SELECT api_id FROM PRODUCTO_DULCERIA WHERE nombre_producto ILIKE '%M&M%Mega%' AND estructura = 'simple'")).fetchall()
    api_ids = [r[0] for r in res]
    print(f"api_ids de M&M's® Mega standalone: {api_ids}")

session = cffi_requests.Session()

for cinema_id, slug in [("484", "El Dorado Veracruz"), ("125", "Plaza Museo Xalapa")]:
    print(f"\n{'='*60}")
    print(f"CINEMA: {cinema_id} ({slug})")
    
    payload = {
        "operationName": "BatchProducts",
        "variables": {"country": "MX", "cinema": cinema_id, "products": api_ids},
        "query": QUERY_BATCH
    }
    r = session.post(API_URL, json=payload, headers=headers, impersonate="chrome124", timeout=30)
    data = r.json()
    
    for prod in data.get("data", {}).get("batchProducts", []):
        price = prod.get("price", 0)
        print(f"\nProducto: {prod.get('productName')} | price: {price} (= ${price/100:.2f})")
        
        # Recolectar IDs de modificadores
        mod_ids = []
        for setting in (prod.get("settings") or []):
            for mod in (setting.get("modifierList") or []):
                print(f"  Regla: {mod.get('title')} | type: {mod.get('type')}")
                for mid in (mod.get("modifierProductList") or []):
                    mod_ids.append(str(mid))
        
        # Fetch modifier products
        if mod_ids:
            payload2 = {
                "operationName": "BatchProducts",
                "variables": {"country": "MX", "cinema": cinema_id, "products": mod_ids},
                "query": QUERY_BATCH
            }
            r2 = session.post(API_URL, json=payload2, headers=headers, impersonate="chrome124", timeout=30)
            data2 = r2.json()
            for m in data2.get("data", {}).get("batchProducts", []):
                mp = m.get("price", 0)
                print(f"    Opción {m.get('product')}: {m.get('productName')} | price: {mp} (= ${mp/100:.2f})")
