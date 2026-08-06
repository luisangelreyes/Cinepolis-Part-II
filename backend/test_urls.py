from curl_cffi import requests

urls = [
    "https://static.cinepolis.com/img/front/mx/desktop/header/btn-alimentos-2.png",
    "https://static.cinepolis.com/img/menus/tradicional/mordisko_oreo_small.png",
    "https://static.cinepolis.com/resources/MX/menus/tradicional/mordisko_oreo_small.png",
]
for u in urls:
    r = requests.get(u, impersonate="chrome120", allow_redirects=False)
    print(f"{u} -> {r.status_code}")
