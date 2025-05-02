import pandas as pd
from flask import Flask, request, send_file, jsonify
import io
import time
import requests
from geopy.geocoders import Nominatim
import math
import threading
import concurrent.futures
from diskcache import Cache
import logging
import os
import joblib

# Globalne zmienne
PTV_API_KEY = "RVVfZmQ1YTcyY2E4ZjNiNDhmOTlhYjE5NjRmNGZhYTdlNTc6NGUyM2VhMmEtZTc2YS00YmVkLWIyMTMtZDc2YjE0NWZjZjE1"
DEFAULT_ROUTING_MODE = "MONETARY"  # Stały tryb wyznaczania trasy

# Inicjalizacja pamięci podręcznych
geo_cache = Cache("geo_cache")
route_cache = Cache("route_cache")

# Wczytywanie danych historycznych
try:
    historical_rates_df = pd.read_excel("historical_rates.xlsx",
                                        dtype={'kod pocztowy zaladunku': str, 'kod pocztowy rozladunku': str})
    historical_rates_gielda_df = pd.read_excel("historical_rates_gielda.xlsx",
                                               dtype={'kod pocztowy zaladunku': str, 'kod pocztowy rozladunku': str})
except Exception as e:
    print(f"Błąd wczytywania danych historycznych: {e}")
    historical_rates_df = pd.DataFrame()
    historical_rates_gielda_df = pd.DataFrame()

# Zmienne globalne do śledzenia postępu
PROGRESS = 0
RESULT_EXCEL = None
CURRENT_ROW = 0
TOTAL_ROWS = 0

# Mapowanie krajów
COUNTRY_MAPPING = {
    'PL': 'Poland', 'Polska': 'Poland',
    'DE': 'Germany', 'Niemcy': 'Germany',
    'FR': 'France', 'Francja': 'France',
    'IT': 'Italy', 'Włochy': 'Italy',
    'ES': 'Spain', 'Hiszpania': 'Spain',
    'NL': 'Netherlands', 'Holandia': 'Netherlands',
    'BE': 'Belgium', 'Belgia': 'Belgium',
    'CZ': 'Czech Republic', 'Czechy': 'Czech Republic',
    'AT': 'Austria', 'Austria': 'Austria',
    'SK': 'Slovakia', 'Słowacja': 'Slovakia',
    'SI': 'Slovenia', 'Słowenia': 'Slovenia',
    'HU': 'Hungary', 'Węgry': 'Hungary',
    'PT': 'Portugal', 'Portugalia': 'Portugal',
    'GR': 'Greece', 'Grecja': 'Greece',
    'CH': 'Switzerland', 'Szwajcaria': 'Switzerland',
    'SE': 'Sweden', 'Szwecja': 'Sweden',
    'FI': 'Finland', 'Finlandia': 'Finland',
    'NO': 'Norway', 'Norwegia': 'Norway',
    'DK': 'Denmark', 'Dania': 'Denmark'
}

# Inicjalizacja geolokatora z większym timeoutem
geolocator = Nominatim(user_agent="wycena_transportu", timeout=15)


def normalize_country(country):
    """Normalizuje nazwę kraju do standardowego formatu."""
    return COUNTRY_MAPPING.get(str(country).strip(), str(country).strip())


def haversine(coord1, coord2):
    """
    Oblicza odległość w linii prostej między dwoma punktami (w km).
    """
    if None in coord1 or None in coord2:
        return None

    R = 6371  # Promień Ziemi w km
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def get_coordinates(country, postal_code, city=None):
    """
    Pobiera współrzędne geograficzne na podstawie kraju, kodu pocztowego i opcjonalnie miasta.
    Priorytetyzuje wyszukiwanie według miasta, jeśli jest dostępne.
    Wykorzystuje cache do przyspieszenia operacji.
    """
    norm_country = normalize_country(country)
    norm_postal = str(postal_code).strip()

    # Jeśli podano miasto, preferuj wyszukiwanie według miasta
    if city and city.strip():
        norm_city = city.strip()
        query_string = f"{norm_city}, {norm_postal}, {norm_country}"
        key = f"{norm_country}_{norm_city}_{norm_postal}"
    else:
        # Jeśli nie podano miasta, wyszukaj według kodu pocztowego
        query_string = f"{norm_postal}, {norm_country}"
        key = f"{norm_country}_{norm_postal}"

    # Sprawdź, czy wynik jest w cache
    if key in geo_cache:
        cached = geo_cache[key]
        if isinstance(cached, tuple) and len(cached) == 2:  # kompatybilność ze starym cache
            return (*cached, 'cache', 'cache')
        return cached

    try:
        # Wywołaj API geokodowania z odpowiednim zapytaniem
        location = geolocator.geocode(query_string, exactly_one=True)
        time.sleep(0.1)  # Minimalny rate limiting

        if location:
            if hasattr(location, 'raw'):
                if 'boundingbox' in location.raw:
                    bb = location.raw['boundingbox']
                    lat = (float(bb[0]) + float(bb[1])) / 2
                    lon = (float(bb[2]) + float(bb[3])) / 2
                    jakosc = 'przybliżone (bounding box)'
                else:
                    lat, lon = location.latitude, location.longitude
                    jakosc = 'dokładne'

                zrodlo = location.raw.get('osm_type', 'API Nominatim')
                if 'display_name' in location.raw and 'Poland' in location.raw['display_name']:
                    zrodlo = 'Polska (Nominatim)'

                result = (lat, lon, jakosc, zrodlo)
                geo_cache[key] = result
                return result
    except Exception as e:
        print(f"Błąd geokodowania: {e}")

    result = (None, None, 'nieznane', 'brak danych')
    geo_cache[key] = result
    return result


def batch_get_coordinates(location_data):
    """
    Pobiera współrzędne geograficzne dla wielu lokalizacji jednocześnie.
    Wykorzystuje równoległe przetwarzanie dla przyspieszenia.

    Args:
        location_data: Lista krotek (country, postal_code, city)

    Returns:
        Słownik {location_key: coordinates}
    """
    results = {}
    to_geocode = []

    # Przygotuj klucze i sprawdź cache
    for loc in location_data:
        country, postal_code, city = loc
        norm_country = normalize_country(country)
        norm_postal = str(postal_code).strip()

        if city and city.strip():
            norm_city = city.strip()
            key = f"{norm_country}_{norm_city}_{norm_postal}"
        else:
            key = f"{norm_country}_{norm_postal}"

        if key in geo_cache:
            results[loc] = geo_cache[key]
        else:
            to_geocode.append((loc, key))

    # Jeśli wszystko było w cache, zwróć wyniki
    if not to_geocode:
        return results

    # Geokoduj pozostałe lokalizacje w grupach po 5
    batch_size = 5
    for i in range(0, len(to_geocode), batch_size):
        batch = to_geocode[i:i + batch_size]
        for loc_data, key in batch:
            country, postal_code, city = loc_data
            results[loc_data] = get_coordinates(country, postal_code, city)
            time.sleep(0.1)  # Minimalny rate limiting

    return results


def get_route_distance(coord_from, coord_to, avoid_switzerland=False, routing_mode=DEFAULT_ROUTING_MODE):
    """
    Oblicza dystans trasy między dwoma punktami przy użyciu API PTV.
    Wykorzystuje cache do przyspieszenia operacji.

    Args:
        coord_from (tuple): Współrzędne punktu początkowego (lat, lon)
        coord_to (tuple): Współrzędne punktu końcowego (lat, lon)
        avoid_switzerland (bool): Czy omijać Szwajcarię
        routing_mode (str): Tryb wyznaczania trasy (SHORTEST, FASTEST, SHORT, MONETARY)

    Returns:
        float or None: Dystans w kilometrach lub None w przypadku błędu
    """
    if None in coord_from or None in coord_to:
        return None

    # Klucz cache
    cache_key = f"{coord_from[0]:.6f},{coord_from[1]:.6f}_{coord_to[0]:.6f},{coord_to[1]:.6f}_{avoid_switzerland}_{routing_mode}"

    # Sprawdź czy wynik jest w cache
    if cache_key in route_cache:
        return route_cache[cache_key]

    base_url = "https://api.myptv.com/routing/v1/routes"

    # Parametry zgodne z API PTV
    params = {
        "waypoints": [f"{coord_from[0]},{coord_from[1]}", f"{coord_to[0]},{coord_to[1]}"],
        "results": "BORDER_EVENTS,POLYLINE",
        "options[routingMode]": routing_mode,
        "options[trafficMode]": "AVERAGE"
    }

    if avoid_switzerland:
        params["options[prohibitedCountries]"] = "CH"

    headers = {
        "apiKey": PTV_API_KEY
    }

    try:
        response = requests.get(base_url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "distance" in data:
                distance = data["distance"] / 1000  # konwersja z metrów na kilometry
                route_cache[cache_key] = distance
                return distance
            else:
                print(f"Brak informacji o dystansie w odpowiedzi API: {data}")
        else:
            print(f"Błąd API PTV: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Wyjątek PTV API: {e}")

    route_cache[cache_key] = None
    return None


def batch_get_routes(routes_data, max_workers=10):
    """
    Oblicza dystanse dla wielu tras jednocześnie.
    Wykorzystuje równoległe przetwarzanie dla przyspieszenia.

    Args:
        routes_data: Lista krotek ((lat1, lon1), (lat2, lon2), avoid_switzerland)
        max_workers: Maksymalna liczba równoległych wątków

    Returns:
        Słownik {route_key: distance}
    """
    results = {}
    to_calculate = []

    # Sprawdź cache dla każdej trasy
    for route in routes_data:
        coord_from, coord_to, avoid_switzerland = route
        cache_key = f"{coord_from[0]:.6f},{coord_from[1]:.6f}_{coord_to[0]:.6f},{coord_to[1]:.6f}_{avoid_switzerland}_{DEFAULT_ROUTING_MODE}"

        if cache_key in route_cache:
            results[route] = route_cache[cache_key]
        else:
            to_calculate.append(route)

    # Jeśli wszystko było w cache, zwróć wyniki
    if not to_calculate:
        return results

    # Oblicz dystanse dla pozostałych tras równolegle
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_route = {
            executor.submit(
                get_route_distance,
                route[0], route[1], route[2], DEFAULT_ROUTING_MODE
            ): route for route in to_calculate
        }

        for future in concurrent.futures.as_completed(future_to_route):
            route = future_to_route[future]
            try:
                results[route] = future.result()
            except Exception as e:
                print(f"Błąd obliczania trasy: {e}")
                results[route] = None

    return results


def get_all_rates(lc, lp, uc, up, lc_coords, uc_coords):
    """
    Pobiera historyczne stawki dla danej relacji.

    Args:
        lc, lp: Kraj i kod pocztowy załadunku
        uc, up: Kraj i kod pocztowy rozładunku
        lc_coords, uc_coords: Współrzędne załadunku i rozładunku

    Returns:
        Słownik z historycznymi stawkami
    """
    norm_lc = normalize_country(lc).strip()
    norm_uc = normalize_country(uc).strip()
    norm_lp = str(lp).strip()[:2].zfill(2)
    norm_up = str(up).strip()[:2].zfill(2)

    # Szukamy w obu źródłach równolegle
    exact_hist = historical_rates_df[
        (historical_rates_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
        (historical_rates_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
        (historical_rates_df['kod pocztowy zaladunku'].astype(str).str.zfill(2) == norm_lp) &
        (historical_rates_df['kod pocztowy rozladunku'].astype(str).str.zfill(2) == norm_up)
        ]

    exact_gielda = historical_rates_gielda_df[
        (historical_rates_gielda_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
        (historical_rates_gielda_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
        (historical_rates_gielda_df['kod pocztowy zaladunku'].astype(str).str.zfill(2) == norm_lp) &
        (historical_rates_gielda_df['kod pocztowy rozladunku'].astype(str).str.zfill(2) == norm_up)
        ]

    # Przygotowanie wyników - domyślnie puste
    result = {
        'hist_stawka_3m': None,
        'hist_stawka_6m': None,
        'hist_stawka_12m': None,
        'hist_stawka_48m': None,
        'hist_fracht_3m': None,
        'gielda_stawka_3m': None,
        'gielda_stawka_6m': None,
        'gielda_stawka_12m': None,
        'gielda_stawka_48m': None,
        'gielda_fracht_3m': None,
        'dystans': None,
        'relacja': f"{norm_lc} {norm_lp} - {norm_uc} {norm_up}"
    }

    # Uzupełniamy dane historyczne jeśli znalezione
    if not exact_hist.empty:
        row = exact_hist.iloc[0]
        result.update({
            'hist_stawka_3m': row['stawka_3m'],
            'hist_stawka_6m': row['stawka_6m'],
            'hist_stawka_12m': row['stawka_12m'],
            'hist_stawka_48m': row['stawka_24m'],
            'hist_fracht_3m': row.get('fracht_3m', None),
            'dystans': row['dystans']
        })

    # Uzupełniamy dane giełdowe jeśli znalezione
    if not exact_gielda.empty:
        row = exact_gielda.iloc[0]
        result.update({
            'gielda_stawka_3m': row['stawka_3m'],
            'gielda_stawka_6m': row['stawka_6m'],
            'gielda_stawka_12m': row['stawka_12m'],
            'gielda_stawka_48m': row['stawka_24m'],
            'gielda_fracht_3m': row.get('fracht_3m', None),
            # Dystans bierzemy z danych historycznych jeśli nie ma w giełdzie
            'dystans': result['dystans'] if result['dystans'] else row['dystans']
        })

    return result


def process_przetargi(df):
    """
    Główna funkcja przetwarzająca dane przetargów.
    Wykorzystuje równoległe przetwarzanie i optymalizacje pamięci podręcznej.

    Args:
        df (DataFrame): DataFrame z danymi przetargowymi
    """
    global PROGRESS, RESULT_EXCEL, CURRENT_ROW, TOTAL_ROWS
    TOTAL_ROWS = len(df)
    CURRENT_ROW = 0

    print(f"Rozpoczynam przetwarzanie {TOTAL_ROWS} wierszy...")

    # Przygotowanie pomocniczych danych
    def safe_float(value):
        if pd.isna(value) or str(value).strip().lower() in ['nan', 'none', '']:
            return None
        try:
            clean_value = str(value).strip().replace(',', '.')
            return float(clean_value)
        except (ValueError, TypeError):
            return None

    def format_currency(value):
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def select_best_rate(row, rate_columns):
        """Wybiera pierwszą dostępną stawkę z listy"""
        for col in rate_columns:
            rate = safe_float(row.get(col))
            if rate is not None:
                return rate
        return None

    def calculate_fracht(distance, rate):
        if distance is None or rate is None:
            return None
        try:
            return distance * rate
        except TypeError:
            return None

    # Zbierz wszystkie unikalne lokalizacje
    print("Zbieranie unikalnych lokalizacji...")
    all_locations = set()
    for _, row in df.iterrows():
        lc = row['kraj zaladunku']
        lp = str(row['kod pocztowy zaladunku']).strip()
        uc = row['kraj rozladunku']
        up = str(row['kod pocztowy rozladunku']).strip()
        lc_city = row.get("miasto zaladunku", "")
        uc_city = row.get("miasto rozladunku", "")

        all_locations.add((lc, lp, lc_city if lc_city and isinstance(lc_city, str) else None))
        all_locations.add((uc, up, uc_city if uc_city and isinstance(uc_city, str) else None))

    # Pobierz współrzędne dla wszystkich lokalizacji
    print(f"Geokodowanie {len(all_locations)} unikalnych lokalizacji...")
    location_coords = batch_get_coordinates(all_locations)

    # Zbierz wszystkie unikalne trasy
    print("Zbieranie unikalnych tras...")
    all_routes = set()
    for _, row in df.iterrows():
        lc = row['kraj zaladunku']
        lp = str(row['kod pocztowy zaladunku']).strip()
        uc = row['kraj rozladunku']
        up = str(row['kod pocztowy rozladunku']).strip()
        lc_city = row.get("miasto zaladunku", "")
        uc_city = row.get("miasto rozladunku", "")

        # Pobierz współrzędne z wcześniej obliczonego zbioru
        coords_zl = location_coords.get((lc, lp, lc_city if lc_city and isinstance(lc_city, str) else None))
        coords_roz = location_coords.get((uc, up, uc_city if uc_city and isinstance(uc_city, str) else None))

        # Dodaj trasę tylko jeśli mamy poprawne współrzędne
        if coords_zl and coords_roz and None not in coords_zl[:2] and None not in coords_roz[:2]:
            norm_lc = normalize_country(lc)
            norm_uc = normalize_country(uc)
            avoid_switzerland = (norm_lc != "Switzerland" and norm_uc != "Switzerland")
            all_routes.add((coords_zl[:2], coords_roz[:2], avoid_switzerland))

    # Oblicz dystanse dla wszystkich unikalnych tras
    print(f"Obliczanie dystansów dla {len(all_routes)} unikalnych tras...")
    route_distances = batch_get_routes(all_routes)

    # Przetwarzanie wierszy
    print("Przetwarzanie wierszy...")
    results = []

    for i, (_, row) in enumerate(df.iterrows()):
        try:
            CURRENT_ROW = i + 1
            lc = row['kraj zaladunku']
            lp = str(row['kod pocztowy zaladunku']).strip()
            uc = row['kraj rozladunku']
            up = str(row['kod pocztowy rozladunku']).strip()
            lc_city = row.get("miasto zaladunku", "")
            uc_city = row.get("miasto rozladunku", "")

            norm_lc = normalize_country(lc)
            norm_uc = normalize_country(uc)
            avoid_switzerland = (norm_lc != "Switzerland" and norm_uc != "Switzerland")

            # Pobierz współrzędne z wcześniej obliczonego zbioru
            coords_zl = location_coords.get((lc, lp, lc_city if lc_city and isinstance(lc_city, str) else None))
            coords_roz = location_coords.get((uc, up, uc_city if uc_city and isinstance(uc_city, str) else None))

            # Pobierz dystans z wcześniej obliczonego zbioru
            if coords_zl and coords_roz and None not in coords_zl[:2] and None not in coords_roz[:2]:
                route_key = (coords_zl[:2], coords_roz[:2], avoid_switzerland)
                dist_ptv = route_distances.get(route_key)
            else:
                dist_ptv = None

            # Pobranie historycznych stawek
            rates = get_all_rates(lc, lp, uc, up, coords_zl, coords_roz)
            dist_hist = safe_float(rates['dystans'])

            # Formatowanie współrzędnych do wynikowego pliku
            lc_lat, lc_lon, lc_jakosc, lc_zrodlo = coords_zl if coords_zl else (None, None, 'nieznane', 'brak danych')
            uc_lat, uc_lon, uc_jakosc, uc_zrodlo = coords_roz if coords_roz else (None, None, 'nieznane', 'brak danych')
            lc_coords_str = f"{lc_lat:.6f}, {lc_lon:.6f}" if None not in (lc_lat, lc_lon) else "Brak danych"
            uc_coords_str = f"{uc_lat:.6f}, {uc_lon:.6f}" if None not in (uc_lat, uc_lon) else "Brak danych"

            # Obliczenie odległości w linii prostej
            dist_haversine = haversine(coords_zl[:2] if coords_zl else (None, None),
                                       coords_roz[:2] if coords_roz else (None, None))

            # Wybór najlepszych stawek z dostępnych danych
            gielda_rate = select_best_rate(rates, [
                'gielda_stawka_3m',
                'gielda_stawka_6m',
                'gielda_stawka_12m',
                'gielda_stawka_48m'
            ])
            hist_rate = select_best_rate(rates, [
                'hist_stawka_3m',
                'hist_stawka_6m',
                'hist_stawka_12m',
                'hist_stawka_48m'
            ])

            # Obliczenia frachtu – osobno dla km PTV oraz historycznych
            gielda_fracht_km_ptv = calculate_fracht(dist_ptv, gielda_rate)
            gielda_fracht_km_hist = calculate_fracht(dist_hist, gielda_rate)
            klient_fracht_km_ptv = calculate_fracht(dist_ptv, hist_rate)
            klient_fracht_km_hist = calculate_fracht(dist_hist, hist_rate)

            results.append({
                "Kraj zaladunku": lc,
                "Kod zaladunku": lp,
                "Miasto zaladunku": lc_city if lc_city else "",
                "Współrzędne zaladunku": lc_coords_str,
                "Jakość geokodowania (zał.)": lc_jakosc,
                "Źródło geokodowania (zał.)": lc_zrodlo,
                "Kraj rozladunku": uc,
                "Kod rozladunku": up,
                "Miasto rozladunku": uc_city if uc_city else "",
                "Współrzędne rozladunku": uc_coords_str,
                "Jakość geokodowania (rozł.)": uc_jakosc,
                "Źródło geokodowania (rozł.)": uc_zrodlo,
                "km PTV (tylko ładowne)": format_currency(dist_ptv),
                "km historyczne z podlotem": format_currency(dist_hist),
                "km w linii prostej": format_currency(dist_haversine),
                "Giełda_stawka_3m": format_currency(safe_float(rates.get('gielda_stawka_3m'))),
                "Giełda_stawka_6m": format_currency(safe_float(rates.get('gielda_stawka_6m'))),
                "Giełda_stawka_12m": format_currency(safe_float(rates.get('gielda_stawka_12m'))),
                "Giełda_stawka_48m": format_currency(safe_float(rates.get('gielda_stawka_48m'))),
                "Giełda - fracht km ładowne": format_currency(gielda_fracht_km_ptv),
                "Giełda - fracht km z podlotem": format_currency(gielda_fracht_km_hist),
                "Klient_stawka_3m": format_currency(safe_float(rates.get('hist_stawka_3m'))),
                "Klient_stawka_6m": format_currency(safe_float(rates.get('hist_stawka_6m'))),
                "Klient_stawka_12m": format_currency(safe_float(rates.get('hist_stawka_12m'))),
                "Klient_stawka_48m": format_currency(safe_float(rates.get('hist_stawka_48m'))),
                "Klient - fracht km ładowne": format_currency(klient_fracht_km_ptv),
                "Klient - fracht km z podlotem": format_currency(klient_fracht_km_hist),
                "Relacja": rates.get('relacja'),
                "Tryb wyznaczania trasy": DEFAULT_ROUTING_MODE
            })

            # Aktualizuj postęp co 10 wierszy dla płynniejszego działania
            if i % 10 == 0 or i == len(df) - 1:
                PROGRESS = int((i + 1) / TOTAL_ROWS * 100)
        except Exception as e:
            print(f"Błąd przetwarzania wiersza {i}: {e}")

    print("Tworzenie pliku wynikowego...")

    columns_order = [
        "Kraj zaladunku", "Kod zaladunku", "Miasto zaladunku", "Współrzędne zaladunku",
        "Jakość geokodowania (zał.)", "Źródło geokodowania (zał.)",
        "Kraj rozladunku", "Kod rozladunku", "Miasto rozladunku", "Współrzędne rozladunku",
        "Jakość geokodowania (rozł.)", "Źródło geokodowania (rozł.)",
        "km PTV (tylko ładowne)", "km historyczne z podlotem", "km w linii prostej",
        "Giełda_stawka_3m", "Giełda_stawka_6m", "Giełda_stawka_12m", "Giełda_stawka_48m",
        "Giełda - fracht km ładowne", "Giełda - fracht km z podlotem",
        "Klient_stawka_3m", "Klient_stawka_6m", "Klient_stawka_12m", "Klient_stawka_48m",
        "Klient - fracht km ładowne", "Klient - fracht km z podlotem",
        "Relacja", "Tryb wyznaczania trasy"
    ]

    df_out = pd.DataFrame(results)
    # Upewnij się, że wszystkie kolumny są w DataFrame, nawet jeśli nie ma ich w wynikach
    for col in columns_order:
        if col not in df_out.columns:
            df_out[col] = None

    # Ustaw kolejność kolumn
    df_out = df_out[columns_order]

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
        df_out.to_excel(writer, index=False, sheet_name='Wyniki')
        workbook = writer.book
        worksheet = writer.sheets['Wyniki']

        # Definicja stylów z obramowaniem
        border_format = {
            'border': 1,
            'border_color': '#000000'
        }

        format_gielda = workbook.add_format({
            'num_format': '#,##0.00',
            'bg_color': '#FFEB9C',
            'align': 'right',
            **border_format
        })

        format_hist = workbook.add_format({
            'num_format': '#,##0.00',
            'bg_color': '#C6EFCE',
            'align': 'right',
            **border_format
        })

        format_default = workbook.add_format({
            'num_format': '#,##0',
            'align': 'right',
            **border_format
        })

        format_fracht_gielda = workbook.add_format({
            'num_format': '#,##0',
            'bg_color': '#FFEB9C',
            'align': 'right',
            **border_format
        })

        format_fracht_klient = workbook.add_format({
            'num_format': '#,##0',
            'bg_color': '#C6EFCE',
            'align': 'right',
            **border_format
        })

        text_format = workbook.add_format({
            'num_format': '@',
            'align': 'left',
            **border_format
        })

        coord_format = workbook.add_format({
            'num_format': '@',  # Format tekstowy
            'align': 'left',
            'border': 1,
            'border_color': '#000000'
        })

        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#000000',
            'bg_color': '#D9D9D9'
        })

        # Nagłówki kolumn
        for col_num, value in enumerate(df_out.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Zapis danych z odpowiednim formatowaniem
        for row_num in range(1, len(df_out) + 1):
            for col_num, col_name in enumerate(df_out.columns):
                value = df_out.iloc[row_num - 1, col_num]
                if pd.isna(value) or value is None:
                    value = ''
                if 'Giełda_stawka' in col_name and isinstance(value, (int, float)):
                    worksheet.write(row_num, col_num, value, format_gielda)
                elif 'Klient_stawka' in col_name and isinstance(value, (int, float)):
                    worksheet.write(row_num, col_num, value, format_hist)
                elif 'Giełda' in col_name and isinstance(value, (int, float)):
                    worksheet.write(row_num, col_num, value, format_fracht_gielda)
                elif 'Klient' in col_name and isinstance(value, (int, float)):
                    worksheet.write(row_num, col_num, value, format_fracht_klient)
                elif any(x in col_name for x in ['Kod', 'Relacja', 'Miasto']):
                    worksheet.write(row_num, col_num, value, text_format)
                elif any(x in col_name for x in ['km', 'stawka', 'fracht']) and isinstance(value, (int, float)):
                    worksheet.write(row_num, col_num, value, format_default)
                else:
                    worksheet.write(row_num, col_num, value, text_format)

        worksheet.set_column(0, len(df_out.columns) - 1, 10)

    buffer.seek(0)
    RESULT_EXCEL = buffer.read()
    PROGRESS = 100


def test_truck_routes():
    """
    Testuje obliczanie tras dla pojazdów przy użyciu API PTV.
    """
    # Punkty testowe
    start = (50.433792, 7.466426)  # Niemcy
    end = (48.237324, 13.824039)  # Austria

    print(f"Test trasy: Niemcy ({start}) -> Austria ({end})")

    # Test dla różnych trybów wyznaczania trasy
    routing_modes = ["SHORTEST", "FASTEST", "SHORT", "MONETARY"]

    for mode in routing_modes:
        dist = get_route_distance(start, end, avoid_switzerland=False, routing_mode=mode)
        print(f"Tryb {mode}: {dist:.2f} km" if dist else f"Tryb {mode}: błąd")


def save_caches():
    """Zapisuje pamięci podręczne do plików."""
    try:
        # Konwertuj cache na słownik element po elemencie
        geo_dict = {}
        for key in geo_cache:
            geo_dict[key] = geo_cache[key]

        route_dict = {}
        for key in route_cache:
            route_dict[key] = route_cache[key]

        # Zapisz słowniki
        joblib.dump(geo_dict, 'geo_cache_backup.joblib')
        joblib.dump(route_dict, 'route_cache_backup.joblib')
        print("Zapisano pamięci podręczne.")
    except Exception as e:
        print(f"Błąd zapisywania pamięci podręcznych: {e}")


def load_caches():
    """Wczytuje pamięci podręczne z plików."""
    try:
        if os.path.exists('geo_cache_backup.joblib'):
            geo_cache_data = joblib.load('geo_cache_backup.joblib')
            for k, v in geo_cache_data.items():
                geo_cache[k] = v
            print(f"Wczytano {len(geo_cache_data)} elementów geo_cache.")

        if os.path.exists('route_cache_backup.joblib'):
            route_cache_data = joblib.load('route_cache_backup.joblib')
            for k, v in route_cache_data.items():
                route_cache[k] = v
            print(f"Wczytano {len(route_cache_data)} elementów route_cache.")
    except Exception as e:
        print(f"Błąd wczytywania pamięci podręcznych: {e}")


# Inicjalizacja aplikacji Flask
app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def upload_file():
    """Główny endpoint aplikacji."""
    if request.method == "POST":
        file = request.files["file"]
        if file:
            global PROGRESS, RESULT_EXCEL
            PROGRESS = 0
            RESULT_EXCEL = None
            file_bytes = io.BytesIO(file.read())
            file_bytes.seek(0)
            threading.Thread(target=background_processing, args=(file_bytes,)).start()
            return '''<html><body><h2>Plik przesłany i przetwarzany.</h2>
                      <p id="postep">Trwa przetwarzanie...</p>
                      <div id="download-link" style="display:none;">
                        <a href="/download">📥 Pobierz wynikowy plik Excel</a>
                      </div>
                      <div>
                        <p><a href="/test_route_form">🧪 Testuj trasę</a></p>
                      </div>
                      <script>
                      function checkProgress() {
                        fetch('/progress')
                          .then(response => response.json())
                          .then(data => {
                            document.getElementById("postep").innerText = 
                              `⏳ Przeliczanie: ${data.current} z ${data.total} (${data.progress}%)`;
                            if (data.progress >= 100) {
                              document.getElementById("postep").innerText = 
                                "✅ Gotowe! Możesz pobrać wynik.";
                              document.getElementById("download-link").style.display = "block";
                              clearInterval(timer);
                            }
                          });
                      }
                      let timer = setInterval(checkProgress, 1000);
                      </script>
                      </body></html>'''
    return '''<html><body><h1>Wgraj plik Excel z przetargami</h1>
              <form method="post" enctype="multipart/form-data">
              <input type="file" name="file">
              <input type="submit" value="Prześlij">
              </form>
              <p><a href="/test_route_form">🧪 Testuj trasę</a></p>
              <p><a href="/save_cache">💾 Zapisz pamięć podręczną</a></p>
              </body></html>'''


@app.route("/download")
def download():
    """Endpoint do pobierania wynikowego pliku."""
    if RESULT_EXCEL and len(RESULT_EXCEL) > 100:
        return send_file(io.BytesIO(RESULT_EXCEL), download_name="wycena.xlsx", as_attachment=True)
    return "Jeszcze nie gotowe."


@app.route("/progress")
def progress():
    """Endpoint zwracający postęp przetwarzania."""
    return jsonify(
        progress=PROGRESS,
        current=CURRENT_ROW,
        total=TOTAL_ROWS,
        error=PROGRESS == -1
    )


@app.route("/save_cache")
def save_cache_endpoint():
    """Endpoint do ręcznego zapisywania pamięci podręcznej."""
    save_caches()
    return "Zapisano pamięć podręczną."


@app.route("/test_route_form")
def test_route_form():
    """Formularz do testowania trasy."""
    return '''<html>
    <head>
        <title>Test trasy</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input[type="text"] { width: 300px; padding: 8px; }
            button { padding: 10px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
            #result { margin-top: 20px; border: 1px solid #ddd; padding: 15px; display: none; }
            .back-link { margin-top: 20px; }
            select { width: 315px; padding: 8px; }
        </style>
    </head>
    <body>
        <h1>Test trasy</h1>
        <div class="form-group">
            <label for="from">Punkt początkowy (szerokość,długość):</label>
            <input type="text" id="from" name="from" value="50.433792,7.466426" placeholder="np. 50.433792,7.466426">
        </div>
        <div class="form-group">
            <label for="to">Punkt końcowy (szerokość,długość):</label>
            <input type="text" id="to" name="to" value="48.237324,13.824039" placeholder="np. 48.237324,13.824039">
        </div>
        <div class="form-group">
            <label for="routingMode">Tryb wyznaczania trasy:</label>
            <select id="routingMode" name="routingMode">
                <option value="MONETARY" selected>Ekonomiczna (MONETARY)</option>
                <option value="SHORTEST">Najkrótsza (SHORTEST)</option>
                <option value="FASTEST">Najszybsza (FASTEST)</option>
                <option value="SHORT">Krótka (SHORT)</option>
            </select>
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" id="avoid_switzerland"> Omijaj Szwajcarię
            </label>
        </div>
        <button onclick="testRoute()">Testuj trasę</button>

        <div id="result"></div>

        <div class="back-link">
            <a href="/">« Powrót do strony głównej</a>
        </div>

        <script>
        function testRoute() {
            const from = document.getElementById('from').value;
            const to = document.getElementById('to').value;
            const mode = document.getElementById('routingMode').value;
            const avoid = document.getElementById('avoid_switzerland').checked;

            document.getElementById('result').style.display = 'block';
            document.getElementById('result').innerHTML = '<p>Obliczanie trasy...</p>';

            fetch(`/test_truck_route?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&mode=${encodeURIComponent(mode)}&avoid=${avoid}`)
                .then(response => response.json())
                .then(data => {
                    let resultHtml = '';

                    if (data.status === 'success') {
                        resultHtml = `
                            <h3>Wyniki:</h3>
                            <p><strong>Dystans:</strong> ${data.dystans_km.toFixed(2)} km</p>
                            <p><strong>Czas przejazdu:</strong> ${data.czas_min.toFixed(2)} min (${(data.czas_min/60).toFixed(2)} godz.)</p>
                        `;

                        if (data.kraje && data.kraje.length > 0) {
                            resultHtml += `<p><strong>Kraje na trasie:</strong> ${data.kraje.join(', ')}</p>`;
                        }
                    } else {
                        resultHtml = `<p><strong>Błąd:</strong> ${data.message}</p>`;
                    }

                    document.getElementById('result').innerHTML = resultHtml;
                })
                .catch(error => {
                    document.getElementById('result').innerHTML = `<p><strong>Błąd:</strong> ${error}</p>`;
                });
        }
        </script>
    </body>
    </html>'''


@app.route("/test_truck_route")
def test_truck_route():
    """Endpoint do testowania obliczania tras."""
    coord_from = request.args.get('from', '50.433792,7.466426')
    coord_to = request.args.get('to', '48.237324,13.824039')
    routing_mode = request.args.get('mode', DEFAULT_ROUTING_MODE)
    avoid_switzerland = request.args.get('avoid', 'false').lower() in ('true', 'yes', '1')

    try:
        lat1, lon1 = map(float, coord_from.split(','))
        lat2, lon2 = map(float, coord_to.split(','))

        # Sprawdź cache
        cache_key = f"{lat1:.6f},{lon1:.6f}_{lat2:.6f},{lon2:.6f}_{avoid_switzerland}_{routing_mode}"
        if cache_key in route_cache:
            dist = route_cache[cache_key]
            # Symuluj czas przejazdu (prędkość średnia 80 km/h)
            travel_time = (dist / 80) * 60 if dist else 0
            return jsonify({
                'status': 'success',
                'dystans_km': dist,
                'czas_min': travel_time,
                'kraje': ["Z cache - brak informacji o krajach"]
            })

        # Wykonaj zapytanie do API PTV
        base_url = "https://api.myptv.com/routing/v1/routes"
        params = {
            "waypoints": [f"{lat1},{lon1}", f"{lat2},{lon2}"],
            "results": "BORDER_EVENTS,POLYLINE",
            "options[routingMode]": routing_mode,
            "options[trafficMode]": "AVERAGE"
        }

        if avoid_switzerland:
            params["options[prohibitedCountries]"] = "CH"

        headers = {
            "apiKey": PTV_API_KEY
        }

        print(f"Wysyłanie zapytania do API PTV z parametrami: {params}")
        response = requests.get(base_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()

            # Zapisz wynik w cache
            dist = data.get("distance", 0) / 1000
            route_cache[cache_key] = dist

            return jsonify({
                'status': 'success',
                'dystans_km': dist,
                'czas_min': data.get("travelTime", 0) / 60,
                'kraje': [event.get("country") for event in data.get("borderEvents", [])]
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Błąd API: {response.status_code} - {response.text}"
            })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"Błąd: {str(e)}"
        })


def background_processing(file_stream):
    """Funkcja do przetwarzania w tle."""
    global RESULT_EXCEL, PROGRESS
    try:
        print("Rozpoczynam przetwarzanie pliku...")
        df = pd.read_excel(file_stream, dtype=str)
        process_przetargi(df)
        save_caches()  # Zapisz cache po zakończeniu
        print("Przetwarzanie zakończone.")
    except Exception as e:
        print(f"Błąd przetwarzania: {e}")
        PROGRESS = -1


if __name__ == '__main__':
    # Wczytaj cache na starcie
    load_caches()

    # Konfiguracja logowania
    log = logging.getLogger('werkzeug')


    class FilterProgress(logging.Filter):
        def filter(self, record):
            return "/progress" not in record.getMessage()


    log.addFilter(FilterProgress())

    # Uruchom aplikację
    app.run(debug=True)