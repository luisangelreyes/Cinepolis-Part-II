from curl_cffi import requests

url = "https://tickets-static-content.cinepolis.com/pimcore/20519/assets/Mexico/Tickets/Movies/BackroomsSinSalidaVersionExtendida/Es/720x1022_21/resource.jpg"
r = requests.get(url, impersonate="chrome120")
print("Content-Type:", r.headers.get("content-type"))
print("Size:", len(r.content))

with open("test_poster.jpg", "wb") as f:
    f.write(r.content)
