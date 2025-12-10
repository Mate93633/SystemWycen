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

from app.config.ferry_data import (
    FERRY_COSTS,
    FERRY_SEA_DISTANCES,
    MANDATORY_FERRY_ROUTES,
    UK_HGV_LEVY_DAILY_EUR,
    is_ferry_mandatory,
    get_best_ferry_for_countries,
    get_ferry_cost,
    get_ferry_sea_distance,
)

__all__ = [
    # Settings
    'PTV_API_KEY',
    'DEFAULT_ROUTING_MODE',
    'DEFAULT_FUEL_COST',
    'DEFAULT_DRIVER_COST',
    # Countries
    'ISO_CODES',
    'COUNTRY_MAPPING',
    'COUNTRY_TO_ISO',
    # Ferry data
    'FERRY_COSTS',
    'FERRY_SEA_DISTANCES',
    'MANDATORY_FERRY_ROUTES',
    'UK_HGV_LEVY_DAILY_EUR',
    'is_ferry_mandatory',
    'get_best_ferry_for_countries',
    'get_ferry_cost',
    'get_ferry_sea_distance',
]

