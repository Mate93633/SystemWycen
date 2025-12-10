"""
Trasy geokodowania (Blueprint).

Zawiera endpointy:
- /upload_for_geocoding (formularz uploadu do geokodowania)
- /ungeocoded_locations (zarządzanie nierozpoznanymi lokalizacjami)
- /save_manual_coordinates (zapisywanie ręcznych współrzędnych)
- /check_locations (sprawdzanie lokalizacji)
- /update_coordinates (aktualizacja współrzędnych)
- /geocoding_progress (postęp geokodowania)
"""

from flask import Blueprint, request, render_template, jsonify
import logging

# Blueprint dla tras geokodowania
geocoding_bp = Blueprint('geocoding', __name__)
logger = logging.getLogger(__name__)


def register_geocoding_routes(
    app,
    geo_cache,
    locations_cache,
    get_user_session,
    GEOCODING_CURRENT_getter,
    GEOCODING_TOTAL_getter
):
    """
    Rejestruje trasy geokodowania w aplikacji Flask.
    
    Uwaga: Ta funkcja jest placeholder - pełna implementacja pozostaje w appGPT.py
    ze względu na złożoność i liczbę zależności.
    
    Args:
        app: Instancja Flask
        geo_cache: Cache geokodowania
        locations_cache: Cache lokalizacji
        get_user_session: Funkcja pobierająca sesję użytkownika
        GEOCODING_CURRENT_getter: Funkcja zwracająca aktualny postęp geokodowania
        GEOCODING_TOTAL_getter: Funkcja zwracająca całkowitą liczbę do geokodowania
    """
    
    @app.route("/upload_for_geocoding")
    def upload_for_geocoding():
        """Formularz uploadu pliku do geokodowania."""
        return render_template("upload_for_geocoding.html")

    @app.route("/geocoding_progress")
    def geocoding_progress_endpoint():
        """Endpoint do śledzenia postępu geokodowania."""
        geocoding_current = GEOCODING_CURRENT_getter()
        geocoding_total = GEOCODING_TOTAL_getter()
        
        if geocoding_total > 0:
            progress = int((geocoding_current / geocoding_total) * 100)
            return jsonify({
                'progress': progress,
                'current': geocoding_current,
                'total': geocoding_total,
                'status': 'running' if geocoding_current < geocoding_total else 'completed'
            })
        else:
            return jsonify({
                'progress': 0,
                'current': 0,
                'total': 0,
                'status': 'idle'
            })
    
    # Uwaga: Pozostałe endpointy (/ungeocoded_locations, /save_manual_coordinates,
    # /check_locations, /update_coordinates) pozostają w appGPT.py ze względu
    # na złożoność i liczbę zależności. Mogą być przeniesione w przyszłości.

