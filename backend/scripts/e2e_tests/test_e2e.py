from playwright.sync_api import sync_playwright
import requests

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
    page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
    
    try:
        # First go to / to initialize domain and allow setting localStorage
        page.goto("http://localhost:5173")
        page.wait_for_timeout(1000)
        
        # Click a showtime to go to SeatSelectionPage (this works because it has a cart flow)
        print("Clicking showtime")
        # Showtimes are buttons containing a colon like "1:15 PM"
        page.evaluate("Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes(':')).click()")
        page.wait_for_timeout(3000)
        print("At:", page.url)
        
        # Now click a seat
        print("Clicking seat")
        # Seat selection map uses SVG rects.
        page.click("rect:not([fill='#3f3f46'])")
        page.wait_for_timeout(2000)
        
        # Click Continuar con dulcería
        print("Clicking Continuar")
        page.click("button:has-text('Continuar con dulcería')")
        page.wait_for_timeout(3000)
        
        print("Final URL:", page.url)
        page.screenshot(path="cart_final.png")
        print("Done")
    except Exception as e:
        print("Error:", e)
    finally:
        browser.close()
