"""
Szybki test API PTV - sprawdzenie COMBINED_TRANSPORT_EVENTS
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
    ("options[avoid]", "RAIL_SHUTTLES")  # Wymusza prom zamiast Eurotunelu
]

print("Wysyłam zapytanie do PTV API...")
print(f"Trasa: Londyn -> Paryż")
print(f"avoid=RAIL_SHUTTLES (wymusza prom)")

response = requests.get(base_url, params=params, headers=headers, timeout=60)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    
    print(f"\n=== WYNIKI ===")
    print(f"Dystans: {data.get('distance', 0)/1000:.2f} km")
    print(f"Czas: {data.get('travelTime', 0)/3600:.2f} h")
    
    # Sprawdź events
    events = data.get('events', [])
    print(f"\nLiczba events: {len(events)}")
    
    combined_transport_found = False
    for event in events:
        if event.get('type') == 'COMBINED_TRANSPORT':
            combined_transport_found = True
            ct = event.get('combinedTransport', {})
            print(f"\n>>> ZNALEZIONO COMBINED_TRANSPORT EVENT!")
            print(f"    Nazwa: {ct.get('name', 'N/A')}")
            print(f"    Typ: {ct.get('type', 'N/A')} (BOAT=prom)")
            print(f"    Czas przeprawy: {ct.get('duration', 0)/60:.0f} min")
            print(f"    Dystans do portu: {event.get('distanceFromStart', 0)/1000:.0f} km")
    
    if not combined_transport_found:
        print("\n>>> Brak COMBINED_TRANSPORT events w odpowiedzi")
        print("    (API może nie zwrócić szczegółów dla niektórych połączeń)")
    
    # Sprawdź kraje
    toll = data.get('toll', {})
    costs = toll.get('costs', {})
    countries = [c.get('countryCode') for c in costs.get('countries', [])]
    print(f"\nKraje na trasie: {countries}")
    
    # Zapisz do pliku
    with open("test_ferry_quick_result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nZapisano do: test_ferry_quick_result.json")
    
else:
    print(f"Błąd: {response.text[:500]}")
