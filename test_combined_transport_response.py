"""
Test COMBINED_TRANSPORT_EVENTS - sprawdza dokładną strukturę odpowiedzi
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

# Test routes: GB -> FR (wymaga promu)
LONDON = (51.5074, -0.1278)
PARIS = (48.8566, 2.3522)

def test_combined_transport():
    """Test z COMBINED_TRANSPORT_EVENTS w results"""
    
    base_url = "https://api.myptv.com/routing/v1/routes"
    headers = {"apiKey": API_KEY}
    
    params = [
        ("waypoints", f"{LONDON[0]},{LONDON[1]}"),
        ("waypoints", f"{PARIS[0]},{PARIS[1]}"),
        # ⚠️ WAŻNE: Dodaj COMBINED_TRANSPORT_EVENTS do results
        ("results", "LEGS,TOLL_COSTS,COMBINED_TRANSPORT_EVENTS"),
        ("options[routingMode]", "FAST"),
        ("options[trafficMode]", "AVERAGE"),
        ("options[avoid]", "RAIL_SHUTTLES")  # Wymuszamy prom
    ]
    
    print("="*70)
    print("TEST: COMBINED_TRANSPORT_EVENTS")
    print("Trasa: London -> Paris (wymuszony prom)")
    print("="*70)
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=60)
        
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n{'='*70}")
            print("KLUCZE NAJWYŻSZEGO POZIOMU:")
            print(f"{'='*70}")
            for key in data.keys():
                print(f"  - {key}")
            
            # Sprawdź czy są eventy
            if 'events' in data:
                events = data['events']
                print(f"\n{'='*70}")
                print(f"EVENTS (znaleziono {len(events)}):")
                print(f"{'='*70}")
                
                for i, event in enumerate(events):
                    print(f"\n--- Event {i+1} ---")
                    print(f"Type: {event.get('type')}")
                    
                    if event.get('type') == 'COMBINED_TRANSPORT':
                        ct = event.get('combinedTransport', {})
                        print(f"\n  combinedTransport:")
                        print(f"    type: {ct.get('type')}")
                        print(f"    name: {ct.get('name')}")
                        print(f"    duration: {ct.get('duration')} s")
                        print(f"    distance: {ct.get('distance')} m")
                        
                        # Start i destination
                        if 'start' in ct:
                            print(f"    start: {ct['start']}")
                        if 'destination' in ct:
                            print(f"    destination: {ct['destination']}")
                        
                        # Koszt (jeśli jest)
                        if 'price' in ct:
                            print(f"    price: {ct['price']}")
                        if 'cost' in ct:
                            print(f"    cost: {ct['cost']}")
                        
                        # Wszystkie klucze
                        print(f"\n    Wszystkie klucze w combinedTransport:")
                        for key in ct.keys():
                            print(f"      - {key}")
                    
                    # Pozycja eventu
                    print(f"  distanceFromStart: {event.get('distanceFromStart')} m")
                    print(f"  travelTimeFromStart: {event.get('travelTimeFromStart')} s")
                    print(f"  latitude: {event.get('latitude')}")
                    print(f"  longitude: {event.get('longitude')}")
                    
            else:
                print("\n⚠️ BRAK KLUCZA 'events' W ODPOWIEDZI!")
                print("API może nie zwracać COMBINED_TRANSPORT_EVENTS dla tej trasy")
            
            # Toll sections - sprawdź czy tam są promy
            if 'toll' in data:
                toll = data['toll']
                sections = toll.get('sections', [])
                print(f"\n{'='*70}")
                print(f"TOLL SECTIONS ({len(sections)}):")
                print(f"{'='*70}")
                
                ferry_sections = [s for s in sections if s.get('tollRoadType') == 'FERRY']
                if ferry_sections:
                    print(f"\nZnaleziono {len(ferry_sections)} sekcji FERRY:")
                    for i, section in enumerate(ferry_sections):
                        print(f"\n  Ferry Section {i+1}:")
                        print(f"    name: {section.get('name')}")
                        print(f"    type: {section.get('tollRoadType')}")
                        print(f"    price: {section.get('convertedPrice', {})}")
                        print(f"    Wszystkie klucze:")
                        for key in section.keys():
                            if key not in ['name', 'tollRoadType']:
                                print(f"      - {key}: {section[key]}")
                else:
                    print("  Brak sekcji typu FERRY")
            
            # Zapisz do pliku
            filename = "test_combined_transport_output.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n{'='*70}")
            print(f"Pełna odpowiedź zapisana do: {filename}")
            print(f"{'='*70}")
            
        else:
            print(f"Błąd API: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Wyjątek: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_combined_transport()
