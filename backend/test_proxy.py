import requests

url = "http://localhost:8000/api/proxy-image?url=https://tickets-static-content.cinepolis.com/pimcore/20519/assets/Mexico/Tickets/Movies/BackroomsSinSalidaVersionExtendida/Es/720x1022_21/resource.jpg"
r = requests.get(url)
print("Proxy Status:", r.status_code)
print("Proxy Content-Type:", r.headers.get("content-type"))
