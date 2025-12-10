"""
Test API PTV - oficjalne rozwiązanie dla przepraw promowych
Wykorzystuje parametr COMBINED_TRANSPORT_EVENTS z oficjalnej dokumentacji PTV

Dokumentacja: https://developer.myptv.com/en/documentation/routing-api/concepts/events
"""
import requests
import json
import os
import re

# Pobierz klucz API
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

# Trasy testowe
LONDON = (51.5074, -0.1278)
PARIS = (48.8566, 2.3522)
MANCHESTER = (53.4808, -2.2426)
BRUSSELS = (50.8503, 4.3517)


def test_combined_transport_events(coord_from, coord_to, name="Test"):
    """
    Testuje trasę z parametrem COMBINED_TRANSPORT_EVENTS
    zgodnie z oficjalną dokumentacją PTV Developer API
    """
    
    base_url = "https://api.myptv.com/routing/v1/routes"
    headers = {"apiKey": API_KEY}
    
    # Używamy COMBINED_TRANSPORT_EVENTS zgodnie z dokumentacją PTV
    params = [
        ("waypoints", f"{coord_from[0]},{coord_from[1]}"),
        ("waypoints", f"{coord_to[0]},{coord_to[1]}"),
        # Kluczowy parametr - dodajemy COMBINED_TRANSPORT_EVENTS
        ("results", "LEGS,POLYLINE,TOLL_COSTS,TOLL_SECTIONS,TOLL_SYSTEMS,COMBINED_TRANSPORT_EVENTS"),
        ("options[routingMode]", "FAST"),
        ("options[trafficMode]", "AVERAGE"),
        ("options[avoid]", "RAIL_SHUTTLES")  # Wymuszamy prom zamiast Eurotunelu
    ]
    
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"Trasa: {coord_from} -> {coord_to}")
    print(f"Parametr results zawiera: COMBINED_TRANSPORT_EVENTS")
    print(f"{'='*70}")
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=60)
        
        print(f"\nStatus HTTP: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Podstawowe info o trasie
            total_distance_m = data.get('distance', 0)
            total_time_s = data.get('travelTime', 0)
            
            print(f"\n--- PODSTAWOWE INFO ---")
            print(f"Całkowity dystans: {total_distance_m} m ({total_distance_m/1000:.2f} km)")
            print(f"Całkowity czas: {total_time_s} s ({total_time_s/3600:.2f} h)")
            
            # Analiza legs
            legs = data.get('legs', [])
            print(f"\n--- LEGS ({len(legs)}) ---")
            
            land_distance = 0
            ferry_distance = 0
            
            for i, leg in enumerate(legs):
                leg_distance = leg.get('distance', 0)
                leg_time = leg.get('travelTime', 0)
                leg_type = leg.get('type', 'UNKNOWN')
                
                print(f"  Leg {i}: type={leg_type}, distance={leg_distance}m, time={leg_time}s")
                
                # Sprawdź combinedTransport w leg
                if 'combinedTransport' in leg:
                    ct = leg['combinedTransport']
                    print(f"    >>> COMBINED TRANSPORT WYKRYTY!")
                    print(f"        name: {ct.get('name', 'N/A')}")
                    print(f"        type: {ct.get('type', 'N/A')} (1=ferry, 2=piggyback)")
                    print(f"        duration: {ct.get('duration', 'N/A')} s")
                    ferry_distance += leg_distance
                else:
                    land_distance += leg_distance
                
                # Wypisz wszystkie nietypowe pola
                for key in leg.keys():
                    if key not in ['distance', 'travelTime', 'trafficDelay', 'violated', 'polyline', 'tollCosts', 'type']:
                        print(f"    {key}: {leg[key]}")
            
            # Analiza events - KLUCZOWE dla COMBINED_TRANSPORT_EVENTS
            events = data.get('events', [])
            print(f"\n--- EVENTS ({len(events)}) ---")
            
            combined_transport_events = []
            for event in events:
                event_type = event.get('type', 'UNKNOWN')
                print(f"  Event: type={event_type}")
                
                if event_type == 'COMBINED_TRANSPORT':
                    combined_transport_events.append(event)
                    print(f"    >>> COMBINED_TRANSPORT EVENT!")
                    print(f"        latitude: {event.get('latitude')}")
                    print(f"        longitude: {event.get('longitude')}")
                    print(f"        distanceFromStart: {event.get('distanceFromStart')} m")
                    print(f"        travelTimeFromStart: {event.get('travelTimeFromStart')} s")
                    
                    # Szczegóły combined transport
                    ct_details = event.get('combinedTransport', {})
                    if ct_details:
                        print(f"        --- Szczegóły przeprawy ---")
                        print(f"        name: {ct_details.get('name', 'N/A')}")
                        print(f"        type: {ct_details.get('type', 'N/A')} (1=ferry, 2=piggyback)")
                        print(f"        duration: {ct_details.get('duration', 'N/A')} s")
                        print(f"        distance: {ct_details.get('distance', 'N/A')} m")
                        
                        # Start i destination
                        start = ct_details.get('start', {})
                        dest = ct_details.get('destination', {})
                        print(f"        start: {start}")
                        print(f"        destination: {dest}")
            
            # Podsumowanie
            print(f"\n--- PODSUMOWANIE ---")
            print(f"Znalezione COMBINED_TRANSPORT events: {len(combined_transport_events)}")
            
            if combined_transport_events:
                print(f"\n>>> OFICJALNIE WYKRYTO PRZEPRAWĘ PROMOWĄ!")
                for i, ct_event in enumerate(combined_transport_events):
                    ct = ct_event.get('combinedTransport', {})
                    ct_type = ct.get('type', 0)
                    ct_type_name = 'FERRY' if ct_type == 1 else 'PIGGYBACK' if ct_type == 2 else 'UNKNOWN'
                    print(f"    Przeprawa {i+1}: {ct.get('name', 'N/A')} ({ct_type_name})")
                    print(f"    - Dystans przeprawy: {ct.get('distance', 0)} m")
                    print(f"    - Czas przeprawy: {ct.get('duration', 0)} s")
            else:
                print(f"\n>>> Brak wykrytych przepraw promowych w events")
                print(f"    (API może nie zwrócić szczegółów dla niektórych połączeń)")
            
            # Zapisz odpowiedź do pliku
            filename = f"api_combined_transport_{name.replace(' ', '_').lower()}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n>>> Pełna odpowiedź zapisana do: {filename}")
            
            return data
            
        else:
            print(f"Błąd API: {response.text}")
            return None
            
    except Exception as e:
        print(f"Wyjątek: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_with_explicit_ferry():
    """
    Test z jawnym wymuszeniem przeprawy promowej poprzez combinedTransport waypoint
    Zgodnie z dokumentacją: https://developer.myptv.com/en/documentation/routing-api/concepts/waypoints
    """
    
    base_url = "https://api.myptv.com/routing/v1/routes"
    headers = {"apiKey": API_KEY}
    
    # Dover i Calais - wymuszamy konkretny prom
    DOVER = (51.1279, 1.3134)
    CALAIS = (50.9513, 1.8587)
    
    print(f"\n{'='*70}")
    print(f"TEST: Jawne wymuszenie przeprawy Dover-Calais")
    print(f"Używamy combinedTransport waypoint zgodnie z dokumentacją PTV")
    print(f"{'='*70}")
    
    # Format waypoint dla combinedTransport:
    # waypoints=<lat>,<lon>!type=combinedTransport&destination=<lat>,<lon>
    params = [
        ("waypoints", f"{LONDON[0]},{LONDON[1]}"),
        # Combined transport waypoint - jawnie wymuszamy prom Dover-Calais
        ("waypoints", f"{DOVER[0]},{DOVER[1]}!type=combinedTransport&destination={CALAIS[0]},{CALAIS[1]}"),
        ("waypoints", f"{PARIS[0]},{PARIS[1]}"),
        ("results", "LEGS,COMBINED_TRANSPORT_EVENTS,TOLL_COSTS"),
        ("options[routingMode]", "FAST"),
    ]
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=60)
        
        print(f"\nStatus HTTP: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nCałkowity dystans: {data.get('distance', 0)/1000:.2f} km")
            print(f"Legs: {len(data.get('legs', []))}")
            print(f"Events: {len(data.get('events', []))}")
            
            # Szukaj combined transport events
            for event in data.get('events', []):
                if event.get('type') == 'COMBINED_TRANSPORT':
                    ct = event.get('combinedTransport', {})
                    print(f"\n>>> COMBINED TRANSPORT EVENT:")
                    print(f"    name: {ct.get('name')}")
                    print(f"    type: {ct.get('type')} (1=ferry)")
                    print(f"    distance: {ct.get('distance')} m")
                    print(f"    duration: {ct.get('duration')} s")
            
            # Zapisz
            with open('api_explicit_ferry_test.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\n>>> Zapisano do: api_explicit_ferry_test.json")
            
        else:
            error_detail = response.text[:500] if response.text else "Brak szczegółów"
            print(f"Błąd API: {response.status_code}")
            print(f"Szczegóły: {error_detail}")
            
    except Exception as e:
        print(f"Wyjątek: {e}")


if __name__ == "__main__":
    print("="*70)
    print("Test API PTV - COMBINED_TRANSPORT_EVENTS")
    print("Oficjalne rozwiązanie z dokumentacji PTV Developer")
    print("="*70)
    print(f"API KEY: {API_KEY[:10]}..." if API_KEY else "BRAK")
    
    # Test 1: Londyn -> Paryż z COMBINED_TRANSPORT_EVENTS
    test_combined_transport_events(LONDON, PARIS, "Londyn-Paryz")
    
    # Test 2: Manchester -> Bruksela
    test_combined_transport_events(MANCHESTER, BRUSSELS, "Manchester-Bruksela")
    
    # Test 3: Jawne wymuszenie promu
    test_with_explicit_ferry()
