import json
from curl_cffi import requests

api_key = 'lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo'
url = 'https://api-g.cinepolis.com/v1/ticket/graphql'
query = '''query Tickets($countryId: String!, $sessionId: String!, $cinemaVistaId: String!) {
  tickets(countryId: $countryId, cinemaVistaId: $cinemaVistaId, sessionId: $sessionId) {
    areaCategoryCode
    tickets {
      id
      ticketTypeCode
      description
      priceInCents
      bookingFee
      type
      isPackageTicket
      packageContent {
        concessions { charge displayName }
      }
    }
  }
}'''
payload = {
    'query': query,
    'variables': {'countryId': 'MX', 'cinemaVistaId': '484', 'sessionId': '94279'}
}
headers = {'x-apikey': api_key, 'Content-Type': 'application/json', 'Origin': 'https://www.cinepolis.com'}

resp = requests.post(url, json=payload, headers=headers, impersonate='chrome')
print('Status:', resp.status_code)
print('Response:', resp.text[:1000])
