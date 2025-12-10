"""
Moduł konfiguracji aplikacji.

Zawiera stałe, mapowania i ustawienia używane w całej aplikacji.
"""

from app.config.settings import (
    PTV_API_KEY,
    DEFAULT_ROUTING_MODE,
    DEFAULT_FUEL_COST,
    DEFAULT_DRIVER_COST,
)

from app.config.countries import (
    ISO_CODES,
    COUNTRY_MAPPING,
    COUNTRY_TO_ISO,
)

__all__ = [
    'PTV_API_KEY',
    'DEFAULT_ROUTING_MODE',
    'DEFAULT_FUEL_COST',
    'DEFAULT_DRIVER_COST',
    'ISO_CODES',
    'COUNTRY_MAPPING',
    'COUNTRY_TO_ISO',
]

