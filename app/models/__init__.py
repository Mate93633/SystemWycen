"""
Moduł modeli danych aplikacji.

Zawiera dataclasses i klasy reprezentujące struktury danych
używane w całej aplikacji.
"""

from app.models.waypoint import WaypointData, RouteRequest
from app.models.exceptions import GeocodeException, LocationVerificationRequired

__all__ = [
    'WaypointData',
    'RouteRequest',
    'GeocodeException',
    'LocationVerificationRequired',
]

