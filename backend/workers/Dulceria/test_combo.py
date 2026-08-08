import json
from curl_cffi import requests

headers = {
    "content-type": "application/json",
    "country-id": "MX",
    "x-apikey": "lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo"
}

query = """
query BatchProducts($country: String!, $cinema: String!, $products: [String]!) {
  batchProducts(countryId: $country, cinemaId: $cinema, productIds: $products) {
    id
    name
    structure
    price
    settings {
      title
      modifierList {
        title
        type
        modifierProductList {
          id
          name
          price
        }
      }
    }
  }
}
"""

res = requests.post("https://api-g.cinepolis.com/v1/fab-struct-concession/graphql", json={"query": query, "variables": {"country": "MX", "cinema": "658", "products": ["28729"]}}, headers=headers, impersonate="chrome120").json()

combos = res.get("data", {}).get("batchProducts", [])
if combos:
    print(json.dumps(combos[0], indent=2))
else:
    print("No combos found")
