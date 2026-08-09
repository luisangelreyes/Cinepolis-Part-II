import os
import sys
from dotenv import load_dotenv
load_dotenv(os.path.join('backend', '.env'))

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    print('Instala curl_cffi: pip install curl_cffi')
    sys.exit(1)

API_KEY = 'lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo'
API_URL = 'https://api-g.cinepolis.com/v1/fab-struct-concession/graphql'
QUERY_BATCH = '''
query BatchProducts($cinema: String!, $country: String!, $products: [String]!) {
  batchProducts(cinema: $cinema, country: $country, products: $products) {
    product price productName productStructure
    settings {
      title order
      modifierList {
        title type order
        rules { max min }
      }
    }
  }
}
'''
headers = {
    'accept': '*/*', 'content-type': 'application/json',
    'country-id': 'MX', 'origin': 'https://cinepolis.com',
    'x-apikey': API_KEY,
}
session = cffi_requests.Session()
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    res = conn.execute(text('''SELECT api_id FROM PRODUCTO_DULCERIA WHERE producto_id = 6731''')).first()
    api_id = res[0]

payload = {
    'operationName': 'BatchProducts',
    'variables': {'country': 'MX', 'cinema': '484', 'products': [api_id]},
    'query': QUERY_BATCH
}
r = session.post(API_URL, json=payload, headers=headers, impersonate='chrome124', timeout=30)
print(r.json())
