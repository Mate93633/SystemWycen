from queue import Queue
from threading import Thread, Lock
import time
from datetime import datetime, timedelta
import requests
import logging

# Konfiguracja loggera - zmiana poziomu na WARNING aby ograniczyć logi
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

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

    def get(self, coord_from, coord_to, avoid_switzerland=False, routing_mode="FAST"):
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

    def set(self, coord_from, coord_to, data, avoid_switzerland=False, routing_mode="FAST"):
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

    def get_routes_batch(self, routes, avoid_switzerland=False, routing_mode="FAST"):
        """
        Przetwarza wiele tras w jednym wywołaniu
        routes: lista tupli (coord_from, coord_to)
        """
        results = {}
        batch_size = 5  # Maksymalna liczba tras w jednym batch'u
        
        for i in range(0, len(routes), batch_size):
            batch = routes[i:i + batch_size]
            waypoints = []
            for coord_from, coord_to in batch:
                waypoints.extend([f"{coord_from[0]},{coord_from[1]}", f"{coord_to[0]},{coord_to[1]}"])
            
            base_url = "https://api.myptv.com/routing/v1/routes/batch"
            headers = {"apiKey": self.api_key}
            params = {
                "waypoints": waypoints,
                "results": "TOLL_COSTS,DISTANCE,POLYLINE",
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
                        polyline = route_data.get('polyline', '')
                        results[route_key] = {'distance': distance_km, 'polyline': polyline}
                        # Zapisz w cache
                        coord_from, coord_to = batch[idx]
                        self.cache_manager.set(coord_from, coord_to, {'distance': distance_km, 'polyline': polyline}, 
                                            avoid_switzerland, routing_mode)
                else:
                    pass
            except Exception as e:
                pass
                
        return results

    def get_route_distance(self, coord_from, coord_to, avoid_switzerland=False, routing_mode="FAST"):
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
                ("results", "LEGS,POLYLINE,TOLL_COSTS"),
                ("options[routingMode]", routing_mode),
                ("options[trafficMode]", "AVERAGE")
            ]
            
            if avoid_switzerland:
                params.append(("options[prohibitedCountries]", "CH"))

            try:
                response = requests.get(base_url, params=params, headers=headers, timeout=40)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Pobierz dystans z sekcji legs
                    distance = None
                    if 'legs' in data and isinstance(data['legs'], list):
                        distance = sum(leg.get('distance', 0) for leg in data['legs'])
                    
                    polyline = data.get('polyline', '')
                    
                    # Pobierz opłaty drogowe
                    toll = data.get("toll", {}).get("costs", {})
                    total_toll = toll.get("convertedPrice", {}).get("price")
                    
                    # Wyświetl szczegółowe informacje o opłatach drogowych
                    print(f"\n[TOLL] Wywołanie kosztów drogowych dla: {coord_from} -> {coord_to}")
                    print(f"[TOLL] SUMA EUR: {total_toll}")

                    # Rozbicie na kraje: długość i koszt
                    countries = toll.get("countries", [])
                    if countries:
                        print("[TOLL] Rozbicie na kraje (długość trasy oraz koszt w EUR):")
                        for kraj in countries:
                            code = kraj.get("countryCode")
                            converted = kraj.get("convertedPrice", {}).get("price")
                            distance_m = kraj.get("distance") or kraj.get("length") or kraj.get("segmentLength")
                            distance_km = round(distance_m / 1000, 1) if distance_m is not None else "?"
                            print(f"    {code}: {distance_km} km / {converted} EUR")
                    
                    if distance is not None:
                        result = {
                            'distance': distance / 1000, 
                            'polyline': polyline,
                            'toll_cost': total_toll
                        }
                        # Dodaj szczegółowe informacje o opłatach drogowych
                        toll_details = {}
                        for kraj in toll.get("countries", []):
                            code = kraj.get("countryCode")
                            converted = kraj.get("convertedPrice", {}).get("price")
                            if code and converted:
                                toll_details[code] = converted
                        result['toll_details'] = toll_details
                        
                        # Zapisz w cache
                        self.cache_manager.set(coord_from, coord_to, result, avoid_switzerland, routing_mode)
                        return result
                    else:
                        logger.warning(f"Brak danych o dystansie w odpowiedzi API dla trasy {coord_from} -> {coord_to}")
                        return None
                else:
                    logger.warning(f"Błąd API PTV: {response.status_code} dla trasy {coord_from} -> {coord_to}")
                    return None
            except Exception as e:
                logger.warning(f"Wyjątek podczas pobierania trasy {coord_from} -> {coord_to}: {str(e)}")
                return None

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