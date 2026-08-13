from curl_cffi import requests
import json

API_URL = "https://api-g.cinepolis.com/v1/billboards/graphql"
API_HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "country-id": "MX",
    "language": "ES",
    "origin": "https://cinepolis.com",
    "referer": "https://cinepolis.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "x-apikey": "lQM6Mkvri1iHksKKCfpAiwGXq0YUZA7Nn6XAXRPr4i13LwXo"
}

GRAPHQL_QUERY = """
query Billboard($countryId: String!, $movieId: String!, $cinemas: String!, $timezone: String) {
  billboard(
    countryId: $countryId
    movieId: $movieId
    cinemas: $cinemas
    timezone: $timezone
  ) {
    schedules {
      dates {
        date
        languages {
          showtimes {
            datetime
            screen
            format { name }
            experience { name }
          }
        }
      }
    }
  }
}
"""

payload = {
    "operationName": "Billboard",
    "variables": {
        "movieId": "hasta-el-fin-del-mundo",
        "cinemas": "cinepolis-la-florida-acayucan",
        "countryId": "MX",
        "timezone": "America/Mexico_City",
    },
    "query": GRAPHQL_QUERY,
}

try:
    response = requests.post(API_URL, json=payload, headers=API_HEADERS, impersonate="chrome110", timeout=15)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2)[:500])
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
