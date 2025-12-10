"""
Moduł tras Flask (Blueprints).

Zawiera definicje endpointów HTTP podzielone na logiczne grupy:
- main: Główne trasy (/, /download, /progress)
- admin: Trasy administracyjne (/admin/*, /show_cache, etc.)
- geocoding: Trasy geokodowania (/ungeocoded_locations, etc.)
- test_routes: Trasy testowe (/test_route_form, etc.)

Uwaga: Ze względu na zachowanie kompatybilności wstecznej,
niektóre trasy nadal są zdefiniowane w appGPT.py.
Funkcje register_*_routes() pozwalają na stopniowe przenoszenie
tras do modułów bez konieczności jednorazowej dużej refaktoryzacji.
"""

from app.routes.main import register_main_routes, main_bp
from app.routes.admin import register_admin_routes, admin_bp
from app.routes.geocoding import register_geocoding_routes, geocoding_bp
from app.routes.test_routes import register_test_routes, test_routes_bp

__all__ = [
    'main_bp',
    'admin_bp', 
    'geocoding_bp',
    'test_routes_bp',
    'register_main_routes',
    'register_admin_routes',
    'register_geocoding_routes',
    'register_test_routes',
]
