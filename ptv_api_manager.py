from queue import Queue
from threading import Thread, Lock
import time
from datetime import datetime, timedelta
import requests
import logging

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
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
                    logger.error(f"Error in PTV request: {e}")
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
                "results": "TOLL_COSTS,DISTANCE",
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
                        results[route_key] = distance_km
                        # Zapisz w cache
                        coord_from, coord_to = batch[idx]
                        self.cache_manager.set(coord_from, coord_to, distance_km, 
                                            avoid_switzerland, routing_mode)
                else:
                    logger.error(f"Błąd API PTV (batch): {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Wyjątek w batch processing: {e}")
                
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
            params = {
                "waypoints": [f"{coord_from[0]},{coord_from[1]}", f"{coord_to[0]},{coord_to[1]}"],
                "results": "TOLL_COSTS",
                "options[routingMode]": routing_mode,
                "options[trafficMode]": "AVERAGE"
            }
            if avoid_switzerland:
                params["options[prohibitedCountries]"] = "CH"

            logger.info(f"Wysyłam zapytanie do PTV API: {params}")
            response = requests.get(base_url, params=params, headers=headers, timeout=40)
            logger.info(f"Otrzymano odpowiedź z kodem: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Odpowiedź z API: {data}")
                distance = data.get('distance')
                if distance is not None:
                    distance_km = distance / 1000
                    logger.info(f"Obliczony dystans: {distance_km} km")
                    self.cache_manager.set(coord_from, coord_to, distance_km, 
                                        avoid_switzerland, routing_mode)
                    return distance_km
                else:
                    logger.error(f"Brak dystansu w odpowiedzi API: {data}")
            else:
                logger.error(f"Błąd API PTV: {response.status_code} - {response.text}")
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
                    logger.error(f"Błąd w zapytaniu: {result['error']}")
                    return None
            time.sleep(0.1)
        
        logger.error("Timeout podczas oczekiwania na wynik")
        return None

    def get_stats(self):
        return self.cache_manager.get_stats() 