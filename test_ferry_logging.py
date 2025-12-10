"""
Test ulepszonych logów dla promów
Sprawdza czy nowe logi poprawnie wyświetlają informacje o promach
"""
import os
import re
import logging
from ptv_api_manager import PTVRouteManager

# Konfiguracja loggera na INFO
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

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

# Inicjalizuj manager
ptv_manager = PTVRouteManager(API_KEY)

print("="*80)
print("TEST 1: Londyn → Paryż (1 prom: Dover-Calais)")
print("="*80)

LONDON = (51.5074, -0.1278)
PARIS = (48.8566, 2.3522)

result = ptv_manager.get_route_distance(
    LONDON, 
    PARIS,
    avoid_switzerland=False,
    avoid_eurotunnel=True,  # Wymuszamy prom
    routing_mode="FAST",
    country_from="GB",
    country_to="FR",
    avoid_serbia=True
)

if result:
    print(f"\n✅ WYNIK:")
    print(f"   Dystans: {result['distance']:.1f} km")
    print(f"   Koszt total: {result['toll_cost']:.2f} EUR")
    print(f"   Koszt dróg: {result['road_toll']:.2f} EUR")
    print(f"   Koszt inne: {result['other_toll']:.2f} EUR")
    print(f"   Special systems: {len(result['special_systems'])}")
    for sys in result['special_systems']:
        print(f"      - {sys['name']} ({sys['type']}): {sys['cost']:.2f} EUR")
else:
    print("❌ Błąd: Brak wyniku")

print("\n" + "="*80)
print("TEST 2: Manchester → Bruksela (1 prom)")
print("="*80)

MANCHESTER = (53.4808, -2.2426)
BRUSSELS = (50.8503, 4.3517)

result2 = ptv_manager.get_route_distance(
    MANCHESTER,
    BRUSSELS,
    avoid_switzerland=False,
    avoid_eurotunnel=True,  # Wymuszamy prom
    routing_mode="FAST",
    country_from="GB",
    country_to="BE",
    avoid_serbia=True
)

if result2:
    print(f"\n✅ WYNIK:")
    print(f"   Dystans: {result2['distance']:.1f} km")
    print(f"   Koszt total: {result2['toll_cost']:.2f} EUR")
    print(f"   Special systems: {len(result2['special_systems'])}")
    for sys in result2['special_systems']:
        print(f"      - {sys['name']} ({sys['type']}): {sys['cost']:.2f} EUR")
else:
    print("❌ Błąd: Brak wyniku")

print("\n" + "="*80)
print("TEST zakończony - sprawdź logi powyżej!")
print("="*80)
