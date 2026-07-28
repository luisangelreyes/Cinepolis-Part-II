import json
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    def on_resp(r):
        if "billboards/graphql" in r.url and r.request.method != "OPTIONS":
            try:
                body = r.json()
                with open("graphql_dump.json", "w", encoding="utf-8") as f:
                    json.dump(body, f, ensure_ascii=False, indent=2)
                print("Dumped GraphQL response.")
            except:
                pass

    page.on("response", on_resp)
    print("Navigating...")
    try:
        page.goto("https://cinepolis.com/mx?cinema=cinepolis-acaya-coatzacoalcos", wait_until="domcontentloaded", timeout=15000)
    except:
        pass
    import time
    time.sleep(5)
    browser.close()
