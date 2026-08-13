from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Listen to console and errors
    page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
    page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
    
    try:
        print("Navigating to http://localhost:5173")
        page.goto("http://localhost:5173")
        page.wait_for_timeout(2000)
        
        # Click the first showtime button. In CarteleraPage, it's an 'a' tag.
        print("Clicking showtime...")
        # We can just evaluate JS to find the first link that contains /funcion/
        page.evaluate("document.querySelector('a[href*=\"/funcion/\"]').click()")
        page.wait_for_timeout(2000)
        
        print("URL is now:", page.url)
        
        # Click an available seat. Available seats are rect elements with fill not equal to the disabled color.
        # Let's just click the first <rect> in the SVG.
        print("Clicking a seat...")
        page.evaluate("document.querySelector('rect').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
        page.wait_for_timeout(2000)
        
        # Click Continuar con dulcería
        print("Clicking Continuar...")
        page.evaluate("Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Continuar con dulcería')).click()")
        page.wait_for_timeout(2000)
        
        print("Final URL:", page.url)
        # Wait a bit to catch any React errors
        page.wait_for_timeout(2000)
    except Exception as e:
        print("Script failed:", e)
    finally:
        browser.close()
