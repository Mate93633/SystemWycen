"""
Prosty test API PTV z COMBINED_TRANSPORT_EVENTS
"""
import requests
import json

API_KEY = "RVVfZmQ1YTcyY2E4ZjNiNDhmOTlhYjE5NjRmNGZhYTdlNTc6NGUyM2VhMmEtZTc2YS00YmVkLWIyMTMtZDc2YjE0NWZjZjE1"

# Londyn -> Paryz
LONDON = (51.5074, -0.1278)
PARIS = (48.8566, 2.3522)

base_url = "https://api.myptv.com/routing/v1/routes"
headers = {"apiKey": API_KEY}

params = [
    ("waypoints", f"{LONDON[0]},{LONDON[1]}"),
    ("waypoints", f"{PARIS[0]},{PARIS[1]}"),
    ("results", "LEGS,TOLL_COSTS,COMBINED_TRANSPORT_EVENTS"),
    ("options[routingMode]", "FAST"),
    ("options[trafficMode]", "AVERAGE"),
    ("options[avoid]", "RAIL_SHUTTLES")
]

response = requests.get(base_url, params=params, headers=headers, timeout=60)

result = {
    "status_code": response.status_code,
    "data": response.json() if response.status_code == 200 else response.text
}

with open("test_ferry_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
