from curl_cffi import requests

headers = {"Referer": "https://cinepolis.com/"}
urls = [
    "https://cinepolis.com/MX/menus/tradicional/mordisko_oreo_small.png",
    "https://static.cinepolis.com/img/menus/tradicional/mordisko_oreo_small.png",
    "https://static.cinepolis.com/resources/MX/menus/tradicional/mordisko_oreo_small.png",
    "https://cdn.cinepolis.com/redesign/MX/menus/tradicional/mordisko_oreo_small.png",
]
for u in urls:
    r = requests.get(u, impersonate="chrome120", headers=headers, allow_redirects=False)
    print(f"URL: {u} -> Status: {r.status_code}")
