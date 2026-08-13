import requests
url = "http://localhost:8000/api/dulceria/cinepolis-el-dorado-veracruz"
resp = requests.get(url)
print(resp.json())
