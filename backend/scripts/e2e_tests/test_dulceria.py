from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
    page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
    
    # We navigate directly to /carrito
    page.goto("http://localhost:5173/carrito")
    page.wait_for_timeout(5000)
    
    print("Done")
    browser.close()
