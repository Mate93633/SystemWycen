"""
Test analizy legs z API PTV - sprawdzamy czy legs rozróżnia segmenty drogowe od promowych
"""
import requests
import json
import os
import re

# Pobierz API KEY
API_KEY = os.environ.get('PTV_API_KEY')

if not API_KEY:
    try:
        with open('appGPT.py', 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'PTV_API_KEY\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                API_KEY = match.group(1)
    except:
        pass

if not API_KEY:
    print("BŁĄD: Brak klucza API PTV!")
    exit(1)

# Austria -> Finland (przechodzi przez prom Tallinn-Helsinki)
AUSTRIA = (46.94720458984375, 15.329350471496582)
FINLAND = (60.17463684082031, 24.762514114379883)

def test_legs_with_ferry():
    """Test legs dla trasy z promem"""
    
    base_url = "https://api.myptv.com/routing/v1/routes"
    headers = {"apiKey": API_KEY}
    
    params = [
        ("waypoints", f"{AUSTRIA[0]},{AUSTRIA[1]}"),
        ("waypoints", f"{FINLAND[0]},{FINLAND[1]}"),
        ("results", "LEGS,COMBINED_TRANSPORT_EVENTS"),
        ("options[routingMode]", "FAST"),
        ("options[trafficMode]", "AVERAGE")
    ]
    
    print("="*80)
    print("TEST: Analiza LEGS dla trasy Austria -> Finland (z promem)")
    print("="*80)
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=60)
        
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Sprawdź legs
            if 'legs' in data:
                legs = data['legs']
                print(f"\n{'='*80}")
                print(f"LEGS (znaleziono {len(legs)}):")
                print(f"{'='*80}")
                
                total_distance = 0
                road_distance = 0
                ferry_distance = 0
                
                for i, leg in enumerate(legs):
                    print(f"\n--- Leg {i+1} ---")
                    print(f"  Klucze: {list(leg.keys())}")
                    print(f"  type: {leg.get('type', 'N/A')}")
                    print(f"  distance: {leg.get('distance', 0)} m ({leg.get('distance', 0)/1000:.2f} km)")
                    print(f"  travelTime: {leg.get('travelTime', 0)} s")
                    
                    leg_dist = leg.get('distance', 0)
                    total_distance += leg_dist
                    
                    # Sprawdź czy to combined transport
                    if 'combinedTransport' in leg:
                        print(f"  ⚠️  Ma combinedTransport!")
                        ct = leg['combinedTransport']
                        print(f"     type: {ct.get('type')}")
                        print(f"     name: {ct.get('name')}")
                        ferry_distance += leg_dist
                    else:
                        road_distance += leg_dist
                    
                    # Pokaż wszystkie pola
                    for key, value in leg.items():
                        if key not in ['type', 'distance', 'travelTime', 'polyline']:
                            print(f"  {key}: {value}")
                
                print(f"\n{'='*80}")
                print(f"PODSUMOWANIE:")
                print(f"  Całkowity dystans: {total_distance/1000:.2f} km")
                print(f"  Dystans drogowy: {road_distance/1000:.2f} km")
                print(f"  Dystans promowy: {ferry_distance/1000:.2f} km")
                print(f"{'='*80}")
            else:
                print("\n⚠️ BRAK KLUCZA 'legs' W ODPOWIEDZI!")
            
            # Zapisz do pliku
            filename = "test_legs_output.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\nPełna odpowiedź zapisana do: {filename}")
            
        else:
            print(f"Błąd API: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Wyjątek: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_legs_with_ferry()
