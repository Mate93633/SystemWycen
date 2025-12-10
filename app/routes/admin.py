"""
Trasy administracyjne (Blueprint).

Zawiera endpointy:
- /admin/sessions (monitoring sesji)
- /admin/cleanup_sessions (czyszczenie sesji)
- /show_cache (podgląd cache)
- /save_cache (zapis cache)
- /clear_luxembourg_cache (czyszczenie cache Luksemburga)
- /clear_locations_cache (czyszczenie cache lokalizacji)
- /ptv_stats (statystyki PTV API)
"""

from flask import Blueprint, jsonify
import logging
import time

# Blueprint dla tras administracyjnych
admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)


def register_admin_routes(
    app,
    session_manager,
    cleanup_scheduler,
    geo_cache,
    route_cache,
    locations_cache,
    save_caches,
    clear_luxembourg_cache,
    ptv_manager
):
    """
    Rejestruje trasy administracyjne w aplikacji Flask.
    
    Args:
        app: Instancja Flask
        session_manager: Manager sesji użytkowników
        cleanup_scheduler: Scheduler czyszczenia sesji
        geo_cache: Cache geokodowania
        route_cache: Cache tras
        locations_cache: Cache lokalizacji
        save_caches: Funkcja zapisu cache
        clear_luxembourg_cache: Funkcja czyszczenia cache Luksemburga
        ptv_manager: Manager PTV API
    """
    
    @app.route("/admin/sessions")
    def admin_sessions():
        """
        Endpoint administracyjny do monitorowania aktywnych sesji.
        Pokazuje statystyki i listę wszystkich aktywnych sesji użytkowników.
        """
        try:
            stats = session_manager.get_session_statistics()
            sessions_info = session_manager.get_all_sessions_info()
            
            return jsonify({
                'statistics': stats,
                'active_sessions': sessions_info,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Błąd w /admin/sessions: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route("/admin/cleanup_sessions")
    def admin_cleanup_sessions():
        """
        Endpoint administracyjny do wymuszenia natychmiastowego czyszczenia sesji.
        """
        try:
            deleted_count = cleanup_scheduler.cleanup_now()
            stats = session_manager.get_session_statistics()
            
            return jsonify({
                'deleted_sessions': deleted_count,
                'statistics': stats,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"Błąd w /admin/cleanup_sessions: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route("/show_cache")
    def show_cache():
        """Endpoint do podglądu zawartości cache."""
        geo_cache_info = {k: geo_cache[k] for k in geo_cache}
        route_cache_info = {
            k: str(route_cache[k])[:100] + "..." if len(str(route_cache[k])) > 100 else route_cache[k] 
            for k in route_cache
        }
        locations_cache_info = {
            k: f"Locations data ({len(locations_cache[k].get('locations', []))} ungeocoded, {len(locations_cache[k].get('correct_locations', []))} geocoded)" 
            if locations_cache[k] else "None" 
            for k in locations_cache
        }
        
        return jsonify({
            'geo_cache': geo_cache_info,
            'route_cache': route_cache_info,
            'locations_cache': locations_cache_info,
            'cache_sizes': {
                'geo_cache': len(geo_cache_info),
                'route_cache': len(route_cache_info),
                'locations_cache': len(locations_cache_info)
            }
        })

    @app.route("/save_cache")
    def save_cache_endpoint():
        """Endpoint do zapisu cache na dysk."""
        save_caches()
        return "Zapisano pamięć podręczną."

    @app.route("/clear_luxembourg_cache")
    def clear_luxembourg_cache_endpoint():
        """Endpoint do czyszczenia błędnego cache dla Luksemburga."""
        count = clear_luxembourg_cache()
        return f"Wyczyszczono {count} błędnych wpisów cache dla Luksemburga."

    @app.route("/clear_locations_cache")
    def clear_locations_cache_endpoint():
        """Endpoint do czyszczenia cache lokalizacji."""
        try:
            locations_cache.clear()
            return "Wyczyszczono cache lokalizacji."
        except Exception as e:
            logger.error(f"Błąd podczas czyszczenia cache lokalizacji: {e}")
            return f"Błąd podczas czyszczenia cache lokalizacji: {e}"

    @app.route("/ptv_stats")
    def ptv_stats():
        """Endpoint do pobierania statystyk PTV API."""
        stats = ptv_manager.get_stats()
        return jsonify(stats)

