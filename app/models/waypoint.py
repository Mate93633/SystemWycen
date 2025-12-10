"""
Modele danych dla tras i punktów pośrednich.

Zawiera dataclasses reprezentujące punkty na trasie (waypoints)
oraz żądania obliczenia trasy.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.config.settings import DEFAULT_FUEL_COST, DEFAULT_DRIVER_COST, DEFAULT_ROUTING_MODE
from app.config.countries import COUNTRY_TO_ISO


@dataclass
class WaypointData:
    """
    Reprezentacja pojedynczego punktu na trasie.
    
    Może być utworzony na dwa sposoby:
    1. Kraj + kod pocztowy (+ opcjonalnie miasto) - wymaga geokodowania
    2. Bezpośrednio współrzędne - bez geokodowania
    
    Attributes:
        country: Kod kraju (ISO 2-letter, np. 'PL') lub None dla koordynat
        postal_code: Kod pocztowy (min 2 cyfry) lub None dla koordynat
        city: Nazwa miasta (opcjonalne)
        coordinates: Współrzędne (lat, lon) - podane bezpośrednio lub po geokodowaniu
    """
    country: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    coordinates: Optional[Tuple[float, float]] = None
    
    def __post_init__(self):
        """Walidacja i normalizacja danych wejściowych"""
        # Scenariusz 1: Koordynaty bezpośrednie
        if self.coordinates and len(self.coordinates) == 2:
            # Walidacja koordynat
            lat, lon = self.coordinates
            if not (-90 <= lat <= 90):
                raise ValueError(f"Nieprawidłowa szerokość geograficzna: {lat} (musi być -90 do 90)")
            if not (-180 <= lon <= 180):
                raise ValueError(f"Nieprawidłowa długość geograficzna: {lon} (musi być -180 do 180)")
            # Koordynaty OK, country/postal mogą być None
            return
        
        # Scenariusz 2: Kraj + kod pocztowy (wymaga geokodowania)
        if not self.country or not self.postal_code:
            raise ValueError("WaypointData wymaga albo coordinates albo (country + postal_code)")
        
        # Normalizacja
        self.country = self.country.upper().strip()
        self.postal_code = self.postal_code.strip()
        
        # Konwersja pełnej nazwy kraju na kod ISO (np. "GERMANY" -> "DE")
        if len(self.country) > 2:
            iso_code = COUNTRY_TO_ISO.get(self.country)
            if iso_code:
                self.country = iso_code
            else:
                raise ValueError(f"Nieznana nazwa kraju: '{self.country}'. Użyj kodu ISO (np. DE) lub pełnej nazwy (np. GERMANY)")
        
        # Walidacja kodu kraju (2 litery)
        if len(self.country) != 2 or not self.country.isalpha():
            raise ValueError(f"Kod kraju musi mieć 2 litery (ISO 3166-1): '{self.country}'")
        
        # Walidacja kodu pocztowego (min 2 znaki)
        if len(self.postal_code) < 2:
            raise ValueError(f"Kod pocztowy musi mieć minimum 2 znaki: '{self.postal_code}'")
        
        # Normalizacja miasta (handle NaN from pandas)
        if self.city:
            # Sprawdź czy to nie jest NaN/None/float
            if isinstance(self.city, str):
                self.city = self.city.strip()
                if not self.city:  # Pusta string po strip
                    self.city = None
            else:
                # NaN, float, lub inny typ - ustaw None
                self.city = None
    
    def is_geocoded(self) -> bool:
        """Sprawdza czy punkt ma przypisane współrzędne"""
        return self.coordinates is not None and len(self.coordinates) == 2
    
    def needs_geocoding(self) -> bool:
        """Sprawdza czy punkt wymaga geokodowania"""
        return not self.is_geocoded() and self.country and self.postal_code
    
    def __str__(self) -> str:
        """String representation dla logowania"""
        if self.is_geocoded() and not self.country:
            # Tylko koordynaty
            return f"Coords({self.coordinates[0]:.4f}, {self.coordinates[1]:.4f})"
        elif self.country and self.postal_code:
            # Kraj + kod
            city_str = f" ({self.city})" if self.city else ""
            coords_str = f" [{self.coordinates[0]:.4f}, {self.coordinates[1]:.4f}]" if self.is_geocoded() else ""
            return f"{self.country} {self.postal_code}{city_str}{coords_str}"
        else:
            return "WaypointData(invalid)"


@dataclass
class RouteRequest:
    """
    Żądanie obliczenia trasy z punktami pośrednimi.
    
    Attributes:
        start: Punkt startowy
        end: Punkt końcowy
        waypoints: Lista punktów pośrednich (0-5)
        fuel_cost: Koszt paliwa [EUR/km]
        driver_cost: Koszt kierowcy [EUR/dzień]
        matrix_type: Typ matrycy marży ('klient' lub 'targi')
        avoid_switzerland: Czy unikać Szwajcarii
        avoid_eurotunnel: Czy unikać Eurotunelu (RAIL_SHUTTLES)
        avoid_serbia: Czy unikać Serbii
        routing_mode: Tryb routingu ('FAST', 'ECO', 'SHORT')
    """
    start: WaypointData
    end: WaypointData
    waypoints: List[WaypointData] = field(default_factory=list)
    fuel_cost: float = DEFAULT_FUEL_COST
    driver_cost: float = DEFAULT_DRIVER_COST
    matrix_type: str = "klient"
    avoid_switzerland: bool = False
    avoid_eurotunnel: bool = True
    avoid_serbia: bool = True
    routing_mode: str = DEFAULT_ROUTING_MODE
    
    def __post_init__(self):
        """Walidacja danych"""
        if len(self.waypoints) > 5:
            raise ValueError("Maksymalnie 5 punktów pośrednich dozwolone")
        
        if self.fuel_cost < 0 or self.fuel_cost > 5:
            raise ValueError("Koszt paliwa musi być w zakresie 0-5 EUR/km")
        
        if self.driver_cost < 0 or self.driver_cost > 1000:
            raise ValueError("Koszt kierowcy musi być w zakresie 0-1000 EUR/dzień")
        
        if self.matrix_type not in ['klient', 'targi']:
            raise ValueError("matrix_type musi być 'klient' lub 'targi'")
    
    def get_all_points_ordered(self) -> List[WaypointData]:
        """Zwraca wszystkie punkty w kolejności: start → waypoints → end"""
        return [self.start] + self.waypoints + [self.end]
    
    def total_waypoints_count(self) -> int:
        """Liczba wszystkich punktów włączając start i end"""
        return 2 + len(self.waypoints)
    
    def has_waypoints(self) -> bool:
        """Czy trasa zawiera punkty pośrednie"""
        return len(self.waypoints) > 0
    
    def __str__(self) -> str:
        """String representation dla logowania"""
        points_str = " → ".join(str(p) for p in self.get_all_points_ordered())
        return f"Route[{self.total_waypoints_count()} points]: {points_str}"

