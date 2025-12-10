"""
Test API PTV dla trasy z promem (GB -> FR)
Sprawdza co dokładnie zwraca API dla przeprawy promowej
"""
import requests
import json
import os

# Pobierz klucz API z zmiennej środowiskowej lub pliku
API_KEY = os.environ.get('PTV_API_KEY')

if not API_KEY:
    # Spróbuj odczytać z pliku .env lub appGPT.py
    try:
        with open('appGPT.py', 'r', encoding='utf-8') as f:
            content = f.read()
            # Szukaj PTV_API_KEY
            import re
            match = re.search(r'PTV_API_KEY\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                API_KEY = match.group(1)
    except:
        pass

if not API_KEY:
    print("BŁĄD: Brak klucza API PTV!")
    print("Ustaw zmienną środowiskową PTV_API_KEY lub wpisz ręcznie w skrypcie")
    exit(1)

# Współrzędne testowe: Dover (GB) -> Calais (FR)
# Dover: 51.1279, 1.3134
# Calais: 50.9513, 1.8587

# Alternatywnie: Londyn -> Paryż
LONDON = (51.5074, -0.1278)
PARIS = (48.8566, 2.3522)

# Lub: Manchester -> Bruksela
MANCHESTER = (53.4808, -2.2426)
BRUSSELS = (50.8503, 4.3517)

def test_route(coord_from, coord_to, name="Test"):
    """Testuje trasę i wyświetla surową odpowiedź API"""
    
    base_url = "https://api.myptv.com/routing/v1/routes"
    headers = {"apiKey": API_KEY}
    
    params = [
        ("waypoints", f"{coord_from[0]},{coord_from[1]}"),
        ("waypoints", f"{coord_to[0]},{coord_to[1]}"),
        ("results", "LEGS,POLYLINE,TOLL_COSTS,TOLL_SECTIONS,TOLL_SYSTEMS"),
        ("options[routingMode]", "FAST"),
        ("options[trafficMode]", "AVERAGE"),
        ("options[avoid]", "RAIL_SHUTTLES")  # Unikamy Eurotunelu - wymuszamy prom
    ]
    
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"Trasa: {coord_from} -> {coord_to}")
    print(f"Parametry: avoid=RAIL_SHUTTLES (wymuszenie promu)")
    print(f"{'='*60}")
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=60)
        
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Podstawowe info
            print(f"\n--- PODSTAWOWE INFO ---")
            print(f"Dystans: {data.get('distance', 'N/A')} m")
            print(f"Czas podróży: {data.get('travelTime', 'N/A')} s")
            
            # Legs info
            legs = data.get('legs', [])
            print(f"\n--- LEGS ({len(legs)}) ---")
            for i, leg in enumerate(legs):
                print(f"  Leg {i}:")
                print(f"    type: {leg.get('type', 'N/A')}")
                print(f"    distance: {leg.get('distance', 'N/A')} m")
                print(f"    travelTime: {leg.get('travelTime', 'N/A')} s")
                # Sprawdź czy jest combinedTransport
                if 'combinedTransport' in leg:
                    print(f"    combinedTransport: {leg['combinedTransport']}")
                # Sprawdź inne pola
                for key in leg.keys():
                    if key not in ['type', 'distance', 'travelTime', 'polyline']:
                        print(f"    {key}: {leg[key]}")
            
            # Toll info
            toll = data.get('toll', {})
            print(f"\n--- TOLL DATA ---")
            print(f"Klucze toll: {toll.keys() if toll else 'Brak danych toll'}")
            
            if toll:
                # Costs
                costs = toll.get('costs', {})
                print(f"\nCosts:")
                print(f"  convertedPrice: {costs.get('convertedPrice', {})}")
                print(f"  Kraje: {[c.get('countryCode') for c in costs.get('countries', [])]}")
                
                # Sections
                sections = toll.get('sections', [])
                print(f"\nSekcje toll ({len(sections)}):")
                section_types = {}
                for section in sections:
                    st = section.get('tollRoadType', 'UNKNOWN')
                    section_types[st] = section_types.get(st, 0) + 1
                    if st in ['FERRY', 'TUNNEL', 'BRIDGE']:
                        print(f"  SPECJALNA SEKCJA: {section}")
                print(f"  Typy sekcji: {section_types}")
                
                # Systems
                systems = toll.get('systems', [])
                print(f"\nSystemy toll ({len(systems)}):")
                for system in systems:
                    print(f"  - {system.get('name', 'N/A')} (type={system.get('type', 'N/A')})")
            
            # Zapisz pełną odpowiedź do pliku
            filename = f"api_response_{name.replace(' ', '_').lower()}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n>>> Pełna odpowiedź zapisana do: {filename}")
            
        else:
            print(f"Błąd API: {response.text}")
            
    except Exception as e:
        print(f"Wyjątek: {e}")

if __name__ == "__main__":
    print("Test API PTV - wykrywanie promów")
    print("API KEY:", API_KEY[:10] + "..." if API_KEY else "BRAK")
    
    # Test 1: Londyn -> Paryż (powinien użyć promu Dover-Calais)
    test_route(LONDON, PARIS, "Londyn-Paryz")
    
    # Test 2: Manchester -> Bruksela
    test_route(MANCHESTER, BRUSSELS, "Manchester-Bruksela")
