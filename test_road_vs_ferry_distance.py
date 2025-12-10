"""
Test rozróżnienia dystansu drogowego od dystansu promowego
Sprawdza czy nowa funkcjonalność poprawnie oddziela dystans "na kołach" od dystansu morskiego
"""
import os
import re
import logging
from ptv_api_manager import PTVRouteManager

# Konfiguracja loggera na INFO
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    force=True
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
    print("BŁĄD: Brak klucza API PTV!", flush=True)
    exit(1)

# Inicjalizuj manager
ptv_manager = PTVRouteManager(API_KEY)

print("="*80, flush=True)
print("TEST 1: Londyn → Paryż (Dover-Calais ferry ~42km morza)", flush=True)
print("="*80, flush=True)

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
    print(f"\n✅ WYNIK:", flush=True)
    print(f"   {'─'*70}", flush=True)
    print(f"   📏 DYSTANSE:", flush=True)
    print(f"      Całkowity dystans:        {result['total_distance_km']:.2f} km", flush=True)
    print(f"      Dystans DROGOWY:          {result['road_distance_km']:.2f} km", flush=True)
    print(f"      Dystans PROMOWY (morski): {result['ferry_distance_km']:.2f} km", flush=True)
    print(f"   {'─'*70}", flush=True)
    print(f"   💰 KOSZTY:", flush=True)
    print(f"      Koszt TOTAL:  {result['toll_cost']:.2f} EUR", flush=True)
    print(f"      Koszt drogi:  {result['road_toll']:.2f} EUR", flush=True)
    print(f"      Koszt inne:   {result['other_toll']:.2f} EUR", flush=True)
    print(f"   {'─'*70}", flush=True)
    
    if result.get('ferry_segments'):
        print(f"   🚢 PROMY ({len(result['ferry_segments'])}):", flush=True)
        for seg in result['ferry_segments']:
            print(f"      - {seg['name']}: {seg['distance_km']:.1f} km, {seg['duration_hours']:.1f}h", flush=True)
    
    print(f"   {'─'*70}", flush=True)
    
    # Walidacja
    expected_ferry_distance = 42  # Dover-Calais
    if abs(result['ferry_distance_km'] - expected_ferry_distance) < 5:
        print(f"   ✅ Dystans promowy OK (oczekiwano ~{expected_ferry_distance}km)", flush=True)
    else:
        print(f"   ⚠️  Dystans promowy niezgodny: {result['ferry_distance_km']:.1f}km (oczekiwano ~{expected_ferry_distance}km)", flush=True)
    
    if result['road_distance_km'] + result['ferry_distance_km'] == result['total_distance_km']:
        print(f"   ✅ Suma dystansów się zgadza", flush=True)
    else:
        print(f"   ⚠️  BŁĄD: suma dystansów nie zgadza się!", flush=True)
else:
    print("❌ Błąd: Brak wyniku", flush=True)

print("\n" + "="*80, flush=True)
print("TEST 2: Tallinn → Helsinki (Bałtyk ~85km morza)", flush=True)
print("="*80, flush=True)

TALLINN = (59.4370, 24.7536)
HELSINKI = (60.1699, 24.9384)

result2 = ptv_manager.get_route_distance(
    TALLINN,
    HELSINKI,
    avoid_switzerland=False,
    avoid_eurotunnel=False,
    routing_mode="FAST",
    country_from="EE",
    country_to="FI",
    avoid_serbia=True
)

if result2:
    print(f"\n✅ WYNIK:", flush=True)
    print(f"   {'─'*70}", flush=True)
    print(f"   📏 DYSTANSE:", flush=True)
    print(f"      Całkowity dystans:        {result2['total_distance_km']:.2f} km", flush=True)
    print(f"      Dystans DROGOWY:          {result2['road_distance_km']:.2f} km", flush=True)
    print(f"      Dystans PROMOWY (morski): {result2['ferry_distance_km']:.2f} km", flush=True)
    print(f"   {'─'*70}", flush=True)
    print(f"   💰 KOSZTY:", flush=True)
    print(f"      Koszt TOTAL:  {result2['toll_cost']:.2f} EUR", flush=True)
    
    if result2.get('ferry_segments'):
        print(f"   {'─'*70}", flush=True)
        print(f"   🚢 PROMY ({len(result2['ferry_segments'])}):", flush=True)
        for seg in result2['ferry_segments']:
            print(f"      - {seg['name']}: {seg['distance_km']:.1f} km, {seg['duration_hours']:.1f}h", flush=True)
    
    print(f"   {'─'*70}", flush=True)
    
    # Walidacja
    expected_ferry_distance = 85  # Tallinn-Helsinki
    if abs(result2['ferry_distance_km'] - expected_ferry_distance) < 10:
        print(f"   ✅ Dystans promowy OK (oczekiwano ~{expected_ferry_distance}km)", flush=True)
    else:
        print(f"   ⚠️  Dystans promowy niezgodny: {result2['ferry_distance_km']:.1f}km (oczekiwano ~{expected_ferry_distance}km)", flush=True)
    
    if abs((result2['road_distance_km'] + result2['ferry_distance_km']) - result2['total_distance_km']) < 0.01:
        print(f"   ✅ Suma dystansów się zgadza", flush=True)
    else:
        print(f"   ⚠️  BŁĄD: suma dystansów nie zgadza się!", flush=True)
else:
    print("❌ Błąd: Brak wyniku", flush=True)

print("\n" + "="*80, flush=True)
print("TEST 3: Warszawa → Berlin (brak promu)", flush=True)
print("="*80, flush=True)

WARSAW = (52.2297, 21.0122)
BERLIN = (52.5200, 13.4050)

result3 = ptv_manager.get_route_distance(
    WARSAW,
    BERLIN,
    avoid_switzerland=False,
    avoid_eurotunnel=False,
    routing_mode="FAST",
    country_from="PL",
    country_to="DE",
    avoid_serbia=True
)

if result3:
    print(f"\n✅ WYNIK:", flush=True)
    print(f"   {'─'*70}", flush=True)
    print(f"   📏 DYSTANSE:", flush=True)
    print(f"      Całkowity dystans:        {result3['total_distance_km']:.2f} km", flush=True)
    print(f"      Dystans DROGOWY:          {result3['road_distance_km']:.2f} km", flush=True)
    print(f"      Dystans PROMOWY (morski): {result3['ferry_distance_km']:.2f} km", flush=True)
    print(f"   {'─'*70}", flush=True)
    
    # Walidacja - nie powinno być promu
    if result3['ferry_distance_km'] == 0:
        print(f"   ✅ Brak promu - OK", flush=True)
    else:
        print(f"   ⚠️  BŁĄD: wykryto prom tam gdzie go nie ma!", flush=True)
    
    if result3['road_distance_km'] == result3['total_distance_km']:
        print(f"   ✅ Dystans drogowy = dystans całkowity (brak promu) - OK", flush=True)
    else:
        print(f"   ⚠️  BŁĄD: dystanse nie zgadzają się dla trasy bez promu!", flush=True)
else:
    print("❌ Błąd: Brak wyniku", flush=True)

print("\n" + "="*80, flush=True)
print("TESTY ZAKOŃCZONE", flush=True)
print("="*80, flush=True)
