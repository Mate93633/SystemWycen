"""
Ustawienia główne aplikacji.

Zawiera klucze API, domyślne wartości i konfigurację systemową.
Wszystkie wartości można nadpisać przez zmienne środowiskowe.
"""

import os

# === KLUCZE API ===
# Klucz API PTV - można nadpisać przez zmienną środowiskową PTV_API_KEY
PTV_API_KEY = os.environ.get(
    'PTV_API_KEY',
    "RVVfZmQ1YTcyY2E4ZjNiNDhmOTlhYjE5NjRmNGZhYTdlNTc6NGUyM2VhMmEtZTc2YS00YmVkLWIyMTMtZDc2YjE0NWZjZjE1"
)

# === USTAWIENIA ROUTINGU ===
# Tryb wyznaczania trasy: FAST, ECO, SHORT
DEFAULT_ROUTING_MODE = os.environ.get('DEFAULT_ROUTING_MODE', "FAST")

# === USTAWIENIA KOSZTÓW ===
# Domyślny koszt paliwa [EUR/km]
DEFAULT_FUEL_COST = float(os.environ.get('DEFAULT_FUEL_COST', '1.1'))

# Domyślny koszt kierowcy [EUR/dzień]
DEFAULT_DRIVER_COST = float(os.environ.get('DEFAULT_DRIVER_COST', '0'))

# === USTAWIENIA SESJI ===
# Maksymalny czas życia sesji użytkownika [godziny]
SESSION_MAX_AGE_HOURS = int(os.environ.get('SESSION_MAX_AGE_HOURS', '24'))

# === USTAWIENIA CACHE ===
# Ścieżki do katalogów cache
GEO_CACHE_DIR = os.environ.get('GEO_CACHE_DIR', 'geo_cache')
ROUTE_CACHE_DIR = os.environ.get('ROUTE_CACHE_DIR', 'route_cache')
LOCATIONS_CACHE_DIR = os.environ.get('LOCATIONS_CACHE_DIR', 'locations_cache')

# === USTAWIENIA LOGOWANIA ===
# Poziom logowania: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'ERROR')
LOG_FILE = os.environ.get('LOG_FILE', 'app.log')

# === USTAWIENIA FLASK ===
# Klucz sekretny dla sesji Flask
FLASK_SECRET_KEY = os.environ.get(
    'FLASK_SECRET_KEY',
    'your-secret-key-change-in-production'
)

# Tryb debug
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

# Host i port
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))

