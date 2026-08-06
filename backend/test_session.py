from curl_cffi import requests

url = "https://cinepolis.com/redesign/MX/menus/tradicional/mordisko_oreo_small.png"

with requests.Session(impersonate="chrome120") as s:
    print("Getting homepage to set cookies...")
    s.get("https://cinepolis.com/")
    print("Cookies:", s.cookies)
    
    print("Fetching image...")
    r = s.get(url, headers={"Referer": "https://cinepolis.com/"}, allow_redirects=False)
    print("Status:", r.status_code)
    print("Content-Type:", r.headers.get("content-type"))
    if r.status_code == 200:
        with open("test_img.png", "wb") as f:
            f.write(r.content)
        print("Image saved!")
