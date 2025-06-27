from queue import Queue
from threading import Thread, Lock
import time
from datetime import datetime, timedelta
import requests
import logging
import traceback

# Konfiguracja loggera - zmiana poziomu na DEBUG aby pokazać wszystkie logi
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_ROUTING_MODE = "FAST"

class PTVRequestQueue:
    def __init__(self, api_key, max_requests_per_second=10):
        self.queue = Queue()
        self.results = {}
        self.lock = Lock()
        self.max_requests_per_second = max_requests_per_second
        self.last_request_time = 0
        self.api_key = api_key
        self._start_worker()

    def _start_worker(self):
        def worker():
            while True:
                request_id, func, args, kwargs = self.queue.get()
                self._rate_limit()
                try:
                    result = func(*args, **kwargs)
                    with self.lock:
                        self.results[request_id] = {'status': 'success', 'data': result}
                except Exception as e:
                    with self.lock:
                        self.results[request_id] = {'status': 'error', 'error': str(e)}
                self.queue.task_done()

        Thread(target=worker, daemon=True).start()

    def _rate_limit(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < 1.0 / self.max_requests_per_second:
            time.sleep(1.0 / self.max_requests_per_second - time_since_last_request)
        self.last_request_time = time.time()

    def add_request(self, request_id, func, *args, **kwargs):
        self.queue.put((request_id, func, args, kwargs))

    def get_result(self, request_id):
        with self.lock:
            return self.results.get(request_id)

    def clear_old_results(self, max_age=3600):  # Czyszczenie wyników starszych niż godzina
        with self.lock:
            current_time = time.time()
            self.results = {k: v for k, v in self.results.items() 
                          if hasattr(v, '_creation_time') and 
                          current_time - v._creation_time < max_age}

class RouteCacheManager:
    def __init__(self, cache_duration=timedelta(days=7)):
        self.cache = {}
        self.cache_duration = cache_duration
        self.stats = {'hits': 0, 'misses': 0}
        self.lock = Lock()

    def _generate_key(self, coord_from, coord_to, avoid_switzerland, routing_mode):
        return (
            tuple(coord_from),
            tuple(coord_to),
            avoid_switzerland,
            routing_mode,
        )

    def get(self, coord_from, coord_to, avoid_switzerland=False, routing_mode=DEFAULT_ROUTING_MODE):
        with self.lock:
            key = self._generate_key(coord_from, coord_to, avoid_switzerland, routing_mode)
            if key in self.cache:
                cache_entry = self.cache[key]
                if datetime.now() - cache_entry['timestamp'] < self.cache_duration:
                    self.stats['hits'] += 1
                    return cache_entry['data']
                else:
                    del self.cache[key]
            self.stats['misses'] += 1
            return None

    def set(self, coord_from, coord_to, data, avoid_switzerland=False, routing_mode=DEFAULT_ROUTING_MODE):
        with self.lock:
            key = self._generate_key(coord_from, coord_to, avoid_switzerland, routing_mode)
            self.cache[key] = {
                'data': data,
                'timestamp': datetime.now()
            }

    def get_stats(self):
        with self.lock:
            total = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
            return {
                'hit_rate': f"{hit_rate:.2f}%",
                'total_requests': total,
                'cache_size': len(self.cache)
            }

class PTVRouteManager:
    def __init__(self, api_key, cache_duration=timedelta(days=7), max_requests_per_second=10):
        self.api_key = api_key
        self.request_queue = PTVRequestQueue(api_key, max_requests_per_second)
        self.cache_manager = RouteCacheManager(cache_duration)

    def get_routes_batch(self, routes, avoid_switzerland=False, routing_mode=DEFAULT_ROUTING_MODE):
        """Przetwarza wiele tras w jednym wywołaniu"""
        results = {}
        batch_size = 5
        
        for i in range(0, len(routes), batch_size):
            batch = routes[i:i + batch_size]
            waypoints = []
            for coord_from, coord_to in batch:
                waypoints.extend([f"{coord_from[0]},{coord_from[1]}", f"{coord_to[0]},{coord_to[1]}"])
            
            base_url = "https://api.myptv.com/routing/v1/routes/batch"
            headers = {"apiKey": self.api_key}
            params = {
                "waypoints": waypoints,
                "results": "TOLL_COSTS,DISTANCE,POLYLINE,TOLL_SECTIONS,TOLL_SYSTEMS",
                "options[routingMode]": routing_mode,
                "options[trafficMode]": "AVERAGE"
            }
            
            if avoid_switzerland:
                params["options[prohibitedCountries]"] = "CH"
            
            try:
                response = requests.post(base_url, json=params, headers=headers, timeout=40)
                
                if response.status_code == 200:
                    data = response.json()
                    for idx, route_data in enumerate(data['routes']):
                        route_key = batch[idx]
                        distance_km = route_data['distance'] / 1000
                        
                        # Przetwarzanie opłat drogowych
                        toll_info = self.process_toll_costs(route_data.get('toll', {}))
                        
                        result = {
                            'distance': distance_km,
                            'polyline': route_data.get('polyline', ''),
                            'toll_cost': toll_info['total_cost'],
                            'road_toll': toll_info['costs_by_type']['ROAD']['EUR'],
                            'other_toll': (toll_info['costs_by_type']['TUNNEL']['EUR'] +
                                         toll_info['costs_by_type']['BRIDGE']['EUR'] +
                                         toll_info['costs_by_type']['FERRY']['EUR']),
                            'toll_details': toll_info['total_cost_by_country'],
                            'special_systems': toll_info['special_systems']
                        }
                        
                        results[route_key] = result
                        # Zapisz w cache
                        coord_from, coord_to = batch[idx]
                        self.cache_manager.set(coord_from, coord_to, result, avoid_switzerland, routing_mode)
                else:
                    logger.warning(f"Błąd API PTV batch: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Wyjątek podczas pobierania tras batch: {str(e)}")
        
        return results

    def get_route_distance(self, coord_from, coord_to, avoid_switzerland=False, routing_mode=DEFAULT_ROUTING_MODE):
        # Sprawdź cache
        cached_result = self.cache_manager.get(coord_from, coord_to, avoid_switzerland, routing_mode)
        if cached_result is not None:
            return cached_result

        # Generuj unikalny ID dla requestu
        request_id = f"route_{coord_from}_{coord_to}_{int(time.time())}"
        
        def _make_request():
            base_url = "https://api.myptv.com/routing/v1/routes"
            headers = {"apiKey": self.api_key}
            
            params = [
                ("waypoints", f"{coord_from[0]},{coord_from[1]}"),
                ("waypoints", f"{coord_to[0]},{coord_to[1]}"),
                ("results", "LEGS,POLYLINE,TOLL_COSTS,TOLL_SECTIONS,TOLL_SYSTEMS"),
                ("options[routingMode]", routing_mode),
                ("options[trafficMode]", "AVERAGE")
            ]
            
            if avoid_switzerland:
                params.append(("options[prohibitedCountries]", "CH"))

            max_retries = 3
            retry_delay = 2  # sekundy między próbami
            
            # Log parametrów zapytania
            logger.info(f"""
=== Rozpoczynam zapytanie do PTV API ===
URL: {base_url}
Trasa: {coord_from} -> {coord_to}
Parametry:
- Unikanie Szwajcarii: {avoid_switzerland}
- Tryb routingu: {routing_mode}
- Timeout połączenia: 5s
- Timeout odczytu: 35s
""")
            
            for attempt in range(max_retries):
                start_time = time.time()
                try:
                    logger.info(f"Próba {attempt + 1}/{max_retries} - Start")
                    
                    # Rozdzielamy timeout na połączenie (5s) i odczyt (35s)
                    response = requests.get(base_url, params=params, headers=headers, 
                                         timeout=(5, 35))
                    
                    request_time = time.time() - start_time
                    logger.info(f"Czas odpowiedzi: {request_time:.2f}s")
                    
                    if response.status_code == 200:
                        logger.info(f"Sukces - Otrzymano odpowiedź 200 OK w {request_time:.2f}s")
                        data = response.json()
                        
                        # Przetwarzanie kosztów
                        if 'toll' in data:
                            toll_info = self.process_toll_costs(data['toll'])
                        
                        distance = None
                        if 'legs' in data and isinstance(data['legs'], list):
                            distance = sum(leg.get('distance', 0) for leg in data['legs'])
                            logger.info(f"Obliczony dystans: {distance/1000:.2f}km")
                        
                        if distance is not None:
                            result = {
                                'distance': distance / 1000,
                                'polyline': data.get('polyline', ''),
                                'toll_cost': toll_info['total_cost'],
                                'road_toll': toll_info['costs_by_type']['ROAD']['EUR'],
                                'other_toll': (toll_info['costs_by_type']['TUNNEL']['EUR'] +
                                             toll_info['costs_by_type']['BRIDGE']['EUR'] +
                                             toll_info['costs_by_type']['FERRY']['EUR']),
                                'toll_details': toll_info['total_cost_by_country'],
                                'special_systems': toll_info['special_systems']
                            }
                            
                            # Zapisz w cache
                            self.cache_manager.set(coord_from, coord_to, result, avoid_switzerland, routing_mode)
                            logger.info("=== Zakończono zapytanie z sukcesem ===")
                            return result
                        else:
                            logger.warning(f"Brak danych o dystansie w odpowiedzi API dla trasy {coord_from} -> {coord_to}")
                            return None
                    elif response.status_code == 400 and avoid_switzerland:
                        logger.info(f"""
=== Otrzymano błąd 400 z avoid_switzerland=True ===
Czas odpowiedzi: {request_time:.2f}s
Próbuję bez unikania Szwajcarii...
""")
                        
                        # Usuń parametr avoid_switzerland
                        retry_params = [p for p in params if p[0] != "options[prohibitedCountries]"]
                        
                        # Spróbuj ponownie
                        retry_start_time = time.time()
                        retry_response = requests.get(base_url, params=retry_params, headers=headers, 
                                                   timeout=(5, 35))
                        retry_time = time.time() - retry_start_time
                        
                        logger.info(f"Czas odpowiedzi bez unikania Szwajcarii: {retry_time:.2f}s")
                        
                        if retry_response.status_code == 200:
                            retry_data = retry_response.json()
                            if 'toll' in retry_data:
                                toll_info = self.process_toll_costs(retry_data['toll'])
                            
                            distance = None
                            if 'legs' in retry_data and isinstance(retry_data['legs'], list):
                                distance = sum(leg.get('distance', 0) for leg in retry_data['legs'])
                                logger.info(f"Obliczony dystans (bez unikania CH): {distance/1000:.2f}km")
                            
                            if distance is not None:
                                result = {
                                    'distance': distance / 1000,
                                    'polyline': retry_data.get('polyline', ''),
                                    'toll_cost': toll_info['total_cost'],
                                    'road_toll': toll_info['costs_by_type']['ROAD']['EUR'],
                                    'other_toll': (toll_info['costs_by_type']['TUNNEL']['EUR'] +
                                                 toll_info['costs_by_type']['BRIDGE']['EUR'] +
                                                 toll_info['costs_by_type']['FERRY']['EUR']),
                                    'toll_details': toll_info['total_cost_by_country'],
                                    'special_systems': toll_info['special_systems']
                                }
                                
                                # Zapisz w cache z avoid_switzerland=False
                                self.cache_manager.set(coord_from, coord_to, result, False, routing_mode)
                                logger.info("=== Zakończono zapytanie z sukcesem (bez unikania CH) ===")
                                return result
                        else:
                            logger.warning(f"""
=== Błąd przy próbie bez unikania Szwajcarii ===
Kod odpowiedzi: {retry_response.status_code}
Czas odpowiedzi: {retry_time:.2f}s
""")
                            return None
                    else:
                        error_details = "Brak szczegółów błędu"
                        try:
                            error_details = response.json()
                        except:
                            try:
                                error_details = response.text
                            except:
                                pass
                        
                        logger.warning(f"""
=== Błąd API PTV ===
Kod odpowiedzi: {response.status_code}
Czas odpowiedzi: {request_time:.2f}s
Trasa: {coord_from} -> {coord_to}
Szczegóły: {error_details}
""")
                        # Nie zwracamy None tutaj - pozwalamy na ponowną próbę
                except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                    request_time = time.time() - start_time
                    if attempt < max_retries - 1:
                        logger.warning(f"""
=== Timeout podczas próby {attempt + 1}/{max_retries} ===
Typ timeoutu: {type(e).__name__}
Czas do timeoutu: {request_time:.2f}s
Trasa: {coord_from} -> {coord_to}
Szczegóły błędu: {str(e)}
Ponawiam za {retry_delay}s...
""")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"""
=== Wszystkie próby zakończone timeoutem ===
Ostatni timeout: {type(e).__name__}
Czas do timeoutu: {request_time:.2f}s
Trasa: {coord_from} -> {coord_to}
Szczegóły ostatniego błędu: {str(e)}
""")
                        return None
                except Exception as e:
                    request_time = time.time() - start_time
                    logger.error(f"""
=== Nieoczekiwany błąd podczas próby {attempt + 1}/{max_retries} ===
Typ błędu: {type(e).__name__}
Czas do błędu: {request_time:.2f}s
Trasa: {coord_from} -> {coord_to}
Szczegóły błędu: {str(e)}
Stack trace:
{traceback.format_exc()}
""")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
            
            logger.error(f"""
=== Wszystkie próby nieudane ===
Trasa: {coord_from} -> {coord_to}
Parametry: {params}
""")
            return None  # Jeśli wszystkie próby się nie powiodły

        # Dodaj request do kolejki
        self.request_queue.add_request(request_id, _make_request)
        
        # Czekaj na wynik (z timeout)
        max_wait = 30  # sekundy
        start_time = time.time()
        while time.time() - start_time < max_wait:
            result = self.request_queue.get_result(request_id)
            if result is not None:
                if result['status'] == 'success':
                    return result['data']
                else:
                    return None
            time.sleep(0.1)
        
        logger.warning("Timeout")
        return None

    def get_stats(self):
        return self.cache_manager.get_stats()

    def separate_toll_costs_by_type(self, toll_data):
        """Separates toll costs by type (road, tunnel, bridge, ferry)"""
        result = {
            'ROAD': {'EUR': 0.0},  # standardowe opłaty drogowe
            'TUNNEL': {'EUR': 0.0},  # tunele
            'BRIDGE': {'EUR': 0.0},  # mosty
            'FERRY': {'EUR': 0.0},   # promy
        }
        
        if not toll_data or 'sections' not in toll_data:
            return result
        
        for section in toll_data['sections']:
            toll_type = section.get('tollRoadType', 'GENERAL')
            # Mapowanie GENERAL na ROAD dla lepszej czytelności
            if toll_type == 'GENERAL':
                toll_type = 'ROAD'
            
            for cost in section.get('costs', []):
                currency = cost.get('currency', 'EUR')
                price = cost.get('price', 0.0)
                
                # Inicjalizacja słownika dla nowej waluty jeśli potrzebne
                if currency not in result[toll_type]:
                    result[toll_type][currency] = 0.0
                
                result[toll_type][currency] += price
                
                # Jeśli mamy przeliczoną cenę w EUR, dodajemy ją też
                converted_price = cost.get('convertedPrice', {}).get('price', 0.0)
                if converted_price and currency != 'EUR':
                    result[toll_type]['EUR'] += converted_price
        
        return result

    def process_toll_costs(self, toll_data):
        """Process toll costs from API response"""
        result = {
            'total_cost': 0,
            'total_cost_by_country': {},
            'costs_by_type': {
                'ROAD': {'EUR': 0},
                'TUNNEL': {'EUR': 0},
                'BRIDGE': {'EUR': 0},
                'FERRY': {'EUR': 0}
            },
            'special_systems': []  # Lista systemów specjalnych (tunele, mosty, promy)
        }
        
        if not toll_data:
            return result
            
        total_cost = 0

        # Pobierz całkowity koszt i koszty według krajów
        if 'costs' in toll_data:
            total_cost = toll_data['costs'].get('convertedPrice', {}).get('price', 0)
            result['total_cost'] = total_cost
            
            # Koszty według krajów
            for country in toll_data['costs'].get('countries', []):
                code = country.get('countryCode')
                cost = country.get('convertedPrice', {}).get('price', 0)
                if code and cost is not None:
                    result['total_cost_by_country'][code] = cost

        # Analiza sekcji dla klasyfikacji kosztów
        road_toll = 0
        tunnel_toll = 0
        bridge_toll = 0
        ferry_toll = 0
        
        # Słownik do mapowania nazw systemów do kosztów z sekcji
        system_name_to_cost = {}

        # Najpierw sprawdź sekcje
        for section in toll_data.get('sections', []):
            section_cost = section.get('costs', [{}])[0].get('convertedPrice', {}).get('price', 0)
            section_type = section.get('tollRoadType', '').upper()
            section_name = section.get('name')
            print(f"DEBUG section: name='{section_name}', type='{section_type}', cost={section_cost}")
            
            if section_type == 'TUNNEL':
                tunnel_toll += section_cost
                # Zapisz koszt dla tuneli, nawet jeśli nie ma nazwy sekcji
                # Nazwa może być w systemach
                if section_cost > 0:
                    # Spróbuj znaleźć odpowiadający system na podstawie kosztu
                    for sys in toll_data.get('systems', []):
                        sys_name = sys.get('name', '')
                        if 'TUNNEL' in sys_name.upper() or 'MONT-BLANC' in sys_name.upper():
                            system_name_to_cost[sys_name] = section_cost
                            break
                # Dodaj tylko jeśli ma rzeczywistą nazwę
                if section_name:
                    system_name_to_cost[section_name] = section_cost
                    result['special_systems'].append({
                        'name': section_name,
                        'type': 'TUNNEL',
                        'cost': section_cost,
                        'operator': section.get('operatorName', '')
                    })
            elif section_type == 'BRIDGE':
                bridge_toll += section_cost
                # Zapisz koszt dla mostów, nawet jeśli nie ma nazwy sekcji
                if section_cost > 0:
                    for sys in toll_data.get('systems', []):
                        sys_name = sys.get('name', '')
                        if 'BRIDGE' in sys_name.upper():
                            system_name_to_cost[sys_name] = section_cost
                            break
                # Dodaj tylko jeśli ma rzeczywistą nazwę
                if section_name:
                    system_name_to_cost[section_name] = section_cost
                    result['special_systems'].append({
                        'name': section_name,
                        'type': 'BRIDGE',
                        'cost': section_cost,
                        'operator': section.get('operatorName', '')
                    })
            elif section_type == 'FERRY':
                ferry_toll += section_cost
                # Zapisz koszt dla promów, nawet jeśli nie ma nazwy sekcji
                if section_cost > 0:
                    for sys in toll_data.get('systems', []):
                        sys_name = sys.get('name', '')
                        if 'FERRY' in sys_name.upper():
                            system_name_to_cost[sys_name] = section_cost
                            break
                # Dodaj tylko jeśli ma rzeczywistą nazwę
                if section_name:
                    system_name_to_cost[section_name] = section_cost
                    result['special_systems'].append({
                        'name': section_name,
                        'type': 'FERRY',
                        'cost': section_cost,
                        'operator': section.get('operatorName', '')
                    })
            else:
                road_toll += section_cost

        # Sprawdź systemy opłat - zawsze dla nazw, ale koszty tylko jeśli nie ma sekcji
        has_section_costs = (road_toll + tunnel_toll + bridge_toll + ferry_toll) > 0
        
        for system in toll_data.get('systems', []):
                system_cost = system.get('costs', {}).get('convertedPrice', {}).get('price', 0)
                system_name = system.get('name', '').upper()
                system_type = system.get('type', '').upper()
                operator_name = system.get('operatorName', '').upper()
                print(f"DEBUG system: name='{system.get('name')}', type='{system_type}', cost={system_cost}")

                # Sprawdź czy system już został dodany z sekcji
                system_real_name = system.get('name')
                already_added = any(sys['name'] == system_real_name for sys in result['special_systems'])
                
                # Klasyfikacja na podstawie nazwy systemu i typu
                if 'TUNNEL' in system_name or 'TUNNEL' in system_type:
                    if not has_section_costs:  # Dodaj koszt tylko jeśli nie ma kosztów z sekcji
                        tunnel_toll += system_cost
                    # Dodaj informację o nazwie systemu tylko jeśli jeszcze nie został dodany
                    if system_real_name and not already_added:
                        # Użyj kosztu z mapowania jeśli dostępny, w przeciwnym razie koszt systemowy
                        display_cost = system_name_to_cost.get(system_real_name, system_cost)
                        print(f"DEBUG mapping: system_real_name='{system_real_name}', mapped_cost={system_name_to_cost.get(system_real_name)}, system_cost={system_cost}, display_cost={display_cost}")
                        result['special_systems'].append({
                            'name': system_real_name,
                            'type': 'TUNNEL',
                            'cost': display_cost,
                            'operator': system.get('operatorName', '')
                        })
                elif 'BRIDGE' in system_name or 'BRIDGE' in system_type:
                    if not has_section_costs:
                        bridge_toll += system_cost
                    # Dodaj informację o nazwie systemu tylko jeśli jeszcze nie został dodany
                    if system_real_name and not already_added:
                        display_cost = system_name_to_cost.get(system_real_name, system_cost)
                        result['special_systems'].append({
                            'name': system_real_name,
                            'type': 'BRIDGE',
                            'cost': display_cost,
                            'operator': system.get('operatorName', '')
                        })
                elif 'FERRY' in system_name or 'FERRY' in system_type:
                    if not has_section_costs:
                        ferry_toll += system_cost
                    # Dodaj informację o nazwie systemu tylko jeśli jeszcze nie został dodany
                    if system_real_name and not already_added:
                        display_cost = system_name_to_cost.get(system_real_name, system_cost)
                        result['special_systems'].append({
                            'name': system_real_name,
                            'type': 'FERRY',
                            'cost': display_cost,
                            'operator': system.get('operatorName', '')
                        })
                elif system_type in ["DISTANCE_BASED", "TIME_BASED", "SECTION_BASED"]:
                    if not has_section_costs:
                        road_toll += system_cost
                else:
                    # Jeśli typ nie jest znany, sprawdź znane systemy
                    if 'MONT-BLANC' in system_name or 'MONT BLANC' in system_name:
                        if not has_section_costs:
                            tunnel_toll += system_cost
                        # Dla Mont-Blanc zawsze dodaj informację o nazwie jeśli nie został już dodany
                        if not already_added:
                            final_name = system_real_name or 'Mont-Blanc Tunnel'
                            display_cost = system_name_to_cost.get(final_name, system_cost)
                            result['special_systems'].append({
                                'name': final_name,
                                'type': 'TUNNEL',
                                'cost': display_cost,
                                'operator': system.get('operatorName', '')
                            })
                    else:
                        if not has_section_costs:
                            road_toll += system_cost

        # Jeśli wciąż nie mamy kosztów, ale mamy całkowity koszt, spróbuj oszacować
        if (road_toll + tunnel_toll + bridge_toll + ferry_toll) == 0 and total_cost > 0:
            # Sprawdź znane systemy w danych
            for system in toll_data.get('systems', []):
                system_name = system.get('name', '').upper()
                if 'MONT-BLANC' in system_name or 'MONT BLANC' in system_name:
                    tunnel_toll = 333.42  # Znana stała cena za tunel Mont Blanc
                    road_toll = total_cost - tunnel_toll
                    break
            else:
                # Jeśli nie znaleziono znanych systemów, wszystko idzie do opłat drogowych
                road_toll = total_cost

        # Zapisz wyniki
        result['costs_by_type']['ROAD']['EUR'] = road_toll
        result['costs_by_type']['TUNNEL']['EUR'] = tunnel_toll
        result['costs_by_type']['BRIDGE']['EUR'] = bridge_toll
        result['costs_by_type']['FERRY']['EUR'] = ferry_toll
        
        return result

    def get_excel_formats(self, workbook):
        """Get Excel formats for different cell types"""
        formats = {
            'header': workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#D9D9D9'
            }),
            'number': workbook.add_format({
                'num_format': '0.00',
                'align': 'right'
            }),
            'cost': workbook.add_format({
                'num_format': '0.00 €',
                'align': 'right'
            }),
            'zero_cost': workbook.add_format({
                'num_format': '0.00 €',
                'align': 'right',
                'color': '#808080'  # szary kolor dla zerowych kosztów
            })
        }
        return formats

    def prepare_excel_header(self, worksheet, include_toll_costs=True):
        """Prepare Excel header with new cost breakdown columns"""
        formats = self.get_excel_formats(worksheet.book)
        headers = ['ID', 'Dystans [km]', 'Czas [h]']
        
        if include_toll_costs:
            headers.extend([
                'Opłaty drogowe [EUR]',
                'Koszt/km [EUR]',
                'Dodatkowe opłaty [EUR]',
                'w tym - Tunele [EUR]',
                'w tym - Mosty [EUR]',
                'w tym - Promy [EUR]',
                'Suma kosztów [EUR]'
            ])
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, formats['header'])
            worksheet.set_column(col, col, len(header) + 2)
        
        return worksheet

    def process_route_result(self, route_result, worksheet, row, include_toll_costs=True):
        """Process single route result and write to worksheet"""
        if not route_result or 'error' in route_result:
            return row

        # Existing distance and time calculations
        distance = route_result.get('distance', 0) / 1000  # km
        travel_time = route_result.get('travelTime', 0) / 3600  # hours

        # Process toll costs with new breakdown
        toll_info = self.process_toll_costs(route_result.get('toll', {}))
        total_cost = toll_info['total_cost']
        costs_by_type = toll_info['costs_by_type']
        
        # Rozdzielenie kosztów
        road_cost = costs_by_type['ROAD']['EUR']
        tunnel_cost = costs_by_type['TUNNEL']['EUR']
        bridge_cost = costs_by_type['BRIDGE']['EUR']
        ferry_cost = costs_by_type['FERRY']['EUR']
        
        # Suma kosztów specjalnych
        special_costs = tunnel_cost + bridge_cost + ferry_cost
        
        # Obliczenie kosztu na km (tylko z opłat drogowych)
        cost_per_km = road_cost / distance if distance > 0 else 0

        # Update Excel columns
        formats = self.get_excel_formats(worksheet.book)
        col = 0
        
        # ID
        worksheet.write(row, col, row)
        col += 1
        
        # Dystans
        worksheet.write(row, col, distance, formats['number'])
        col += 1
        
        # Czas
        worksheet.write(row, col, travel_time, formats['number'])
        col += 1
        
        if include_toll_costs:
            # Opłaty drogowe
            worksheet.write(row, col, road_cost, formats['cost'])
            col += 1
            
            # Koszt na km (tylko z opłat drogowych)
            worksheet.write(row, col, cost_per_km, formats['cost'])
            col += 1
            
            # Dodatkowe opłaty (suma tuneli, mostów, promów)
            worksheet.write(row, col, special_costs, formats['cost'])
            col += 1
            
            # Szczegóły dodatkowych opłat
            worksheet.write(row, col, tunnel_cost, formats['cost'])
            col += 1
            worksheet.write(row, col, bridge_cost, formats['cost'])
            col += 1
            worksheet.write(row, col, ferry_cost, formats['cost'])
            col += 1
            
            # Suma wszystkich kosztów
            worksheet.write(row, col, total_cost, formats['cost'])
            col += 1

        return row + 1 