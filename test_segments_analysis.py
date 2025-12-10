"""
Test analizy SEGMENTS z API PTV - prawdziwy sposób na rozróżnienie road vs ferry
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

def test_segments_with_ferry():
    """Test SEGMENTS dla trasy z promem"""
    
    base_url = "https://api.myptv.com/routing/v1/routes"
    headers = {"apiKey": API_KEY}
    
    params = [
        ("waypoints", f"{AUSTRIA[0]},{AUSTRIA[1]}"),
        ("waypoints", f"{FINLAND[0]},{FINLAND[1]}"),
        ("results", "SEGMENTS,COMBINED_TRANSPORT_EVENTS"),  # SEGMENTS zamiast LEGS!
        ("options[routingMode]", "FAST"),
        ("options[trafficMode]", "AVERAGE")
    ]
    
    print("="*80)
    print("TEST: Analiza SEGMENTS dla trasy Austria -> Finland (z promem)")
    print("="*80)
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=60)
        
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Sprawdź segments
            if 'segments' in data:
                segments = data['segments']
                print(f"\n{'='*80}")
                print(f"SEGMENTS (znaleziono {len(segments)}):")
                print(f"{'='*80}")
                
                total_distance = 0
                road_distance = 0
                ferry_distance = 0
                combined_transport_count = 0
                
                for i, seg in enumerate(segments):
                    seg_type = seg.get('type', 'UNKNOWN')
                    seg_dist = seg.get('distance', 0)
                    total_distance += seg_dist
                    
                    # Pokaż tylko nietypowe segmenty lub co 100-ty
                    if seg_type == 'COMBINED_TRANSPORT' or i % 100 == 0 or i < 5 or i >= len(segments) - 5:
                        print(f"\n--- Segment {i+1}/{len(segments)} ---")
                        print(f"  type: {seg_type}")
                        print(f"  distance: {seg_dist} m ({seg_dist/1000:.2f} km)")
                        print(f"  travelTime: {seg.get('travelTime', 0)} s")
                    
                    # Klasyfikuj dystans
                    if seg_type == 'COMBINED_TRANSPORT':
                        ferry_distance += seg_dist
                        combined_transport_count += 1
                        print(f"  🚢 COMBINED TRANSPORT!")
                        if 'combinedTransport' in seg:
                            ct = seg['combinedTransport']
                            print(f"     name: {ct.get('name')}")
                            print(f"     type: {ct.get('type')}")
                    elif seg_type in ['NETWORK_SEGMENT', 'LINK_SEGMENT']:
                        road_distance += seg_dist
                    else:
                        # Inne typy (NOT_DRIVING itp.)
                        print(f"  ⚠️  Inny typ: {seg_type}")
                
                print(f"\n{'='*80}")
                print(f"PODSUMOWANIE:")
                print(f"  Liczba segmentów: {len(segments)}")
                print(f"  Combined transport segments: {combined_transport_count}")
                print(f"  Całkowity dystans: {total_distance/1000:.2f} km")
                print(f"  Dystans drogowy (NETWORK+LINK): {road_distance/1000:.2f} km")
                print(f"  Dystans promowy (COMBINED_TRANSPORT): {ferry_distance/1000:.2f} km")
                print(f"  Różnica: {(total_distance - road_distance - ferry_distance)/1000:.2f} km")
                print(f"{'='*80}")
            else:
                print("\n⚠️ BRAK KLUCZA 'segments' W ODPOWIEDZI!")
                print(f"Dostępne klucze: {list(data.keys())}")
            
            # Zapisz do pliku
            filename = "test_segments_output.json"
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
    test_segments_with_ferry()
