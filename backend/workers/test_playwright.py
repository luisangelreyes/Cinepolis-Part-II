import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    def on_request(req):
        if "billboards/graphql" in req.url:
            print("GRAPHQL REQUEST PAYLOAD:")
            print(req.post_data)
            
    page.on("request", on_request)
    print("Navigating...")
    page.goto("https://cinepolis.com/mx?cinema=cinepolis-vip-el-dorado-veracruz", wait_until="networkidle")
    time.sleep(3)
    browser.close()
