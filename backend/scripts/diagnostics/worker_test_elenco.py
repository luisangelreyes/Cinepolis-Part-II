"""
Diagnóstico: ¿Qué peticiones de red hace la página de detalle de película?
"""
import time, json
from playwright.sync_api import sync_playwright

peticiones = []

def capturar(r):
    url = r.url
    if any(k in url for k in ["graphql", "api", "movie", "pelicula", "cast", "crew"]):
        peticiones.append(url)
        try:
            body = r.json()
            if body:
                fname = url.split("/")[-1].split("?")[0] or "resp"
                fname = fname[:40].replace("/","_")
                with open(f"resp_{fname}.json", "w", encoding="utf-8") as f:
                    json.dump(body, f, ensure_ascii=False, indent=2)
                print(f"  [JSON] Guardado: resp_{fname}.json  ← {url[:80]}")
        except:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    )
    page = ctx.new_page()
    page.on("response", capturar)
    
    print("Navegando a la página de detalle de La Odisea...")
    try:
        page.goto("https://cinepolis.com/mx/pelicula/la-odisea", wait_until="networkidle", timeout=25000)
    except:
        pass
    time.sleep(5)
    
    print("\n=== TODAS LAS PETICIONES CAPTURADAS ===")
    for url in peticiones:
        print(" ", url)
    
    browser.close()
