"""
Funkcje geograficzne i obliczenia odległości.

Zawiera funkcje do obliczeń geodezyjnych.
"""

import math
from typing import Tuple, Optional


def haversine(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> Optional[float]:
    """
    Oblicza odległość między dwoma punktami na Ziemi używając wzoru Haversine.
    
    Wzór Haversine uwzględnia krzywiznę Ziemi i daje dokładne wyniki
    dla odległości do kilku tysięcy kilometrów.
    
    Args:
        coord1: Tuple (latitude, longitude) pierwszego punktu
        coord2: Tuple (latitude, longitude) drugiego punktu
    
    Returns:
        Odległość w kilometrach lub None jeśli któraś współrzędna jest None
    
    Example:
        >>> haversine((52.2297, 21.0122), (51.5074, -0.1278))  # Warszawa -> Londyn
        1445.5  # km (przybliżona wartość)
    """
    if None in coord1 or None in coord2:
        return None
    
    # Promień Ziemi w kilometrach
    R = 6371
    
    # Konwersja na radiany
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    
    # Różnice
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Wzór Haversine
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    
    return R * 2 * math.asin(math.sqrt(a))


def is_valid_coordinates(lat: float, lon: float) -> bool:
    """
    Sprawdza czy współrzędne są prawidłowe.
    
    Args:
        lat: Szerokość geograficzna
        lon: Długość geograficzna
    
    Returns:
        True jeśli współrzędne są w prawidłowym zakresie
    """
    if lat is None or lon is None:
        return False
    
    return -90 <= lat <= 90 and -180 <= lon <= 180


def format_coordinates_for_api(lat: float, lon: float) -> str:
    """
    Formatuje współrzędne do użycia w API (np. PTV).
    
    Args:
        lat: Szerokość geograficzna
        lon: Długość geograficzna
    
    Returns:
        String w formacie "lat,lon"
    """
    return f"{lat},{lon}"

