import requests

url = "https://static.cinepolis.com/redesign/MX/menus/tradicional/mordisko_oreo_small.png"

# 1. No headers
r1 = requests.get(url, allow_redirects=False)
print("No headers:", r1.status_code, r1.headers.get("Location"))

# 2. Chrome UA
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36"}
r2 = requests.get(url, headers=headers, allow_redirects=False)
print("With UA:", r2.status_code, r2.headers.get("Location"))

# 3. UA + Referer + Cookie
headers["Referer"] = "https://cinepolis.com/"
cookies = {"cnpls-redirect": "mx_redesign"}
r3 = requests.get(url, headers=headers, cookies=cookies, allow_redirects=False)
print("With Cookie:", r3.status_code, r3.headers.get("Location"))

