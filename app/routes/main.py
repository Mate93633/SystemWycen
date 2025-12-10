"""
Główne trasy aplikacji (Blueprint).

Zawiera endpointy:
- / (upload pliku)
- /download (pobieranie wyników)
- /progress (postęp przetwarzania)
"""

from flask import Blueprint, request, render_template, send_file, jsonify
import logging
import threading

# Blueprint dla głównych tras
main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


def register_main_routes(
    app,
    get_user_session,
    background_processing,
    set_margin_matrix,
    get_margin_matrix_info,
    DEFAULT_FUEL_COST,
    DEFAULT_DRIVER_COST
):
    """
    Rejestruje główne trasy w aplikacji Flask.
    
    Ta funkcja przyjmuje zależności jako parametry, co pozwala
    na zachowanie kompatybilności z istniejącym kodem w appGPT.py
    bez konieczności refaktoryzacji całej logiki.
    
    Args:
        app: Instancja Flask
        get_user_session: Funkcja pobierająca sesję użytkownika
        background_processing: Funkcja przetwarzania w tle
        set_margin_matrix: Funkcja ustawiająca macierz marży
        get_margin_matrix_info: Funkcja pobierająca info o macierzy
        DEFAULT_FUEL_COST: Domyślny koszt paliwa
        DEFAULT_DRIVER_COST: Domyślny koszt kierowcy
    """
    
    @app.route("/", methods=["GET", "POST"])
    def upload_file():
        """
        Endpoint do uploadu pliku Excel i rozpoczęcia przetwarzania.
        Każdy użytkownik ma swoją izolowaną sesję.
        """
        if request.method == "POST":
            logger.info("="*80)
            logger.info("POST / - Otrzymano request uploadu pliku")
            logger.info(f"Request files: {list(request.files.keys())}")
            logger.info(f"Request form: {dict(request.form)}")
            logger.info("="*80)
            
            try:
                file = request.files.get("file")
                if not file:
                    logger.error("Brak pliku w requeście!")
                    return render_template("error.html", message="Nie wybrano pliku")

                # Pobierz lub utwórz sesję użytkownika
                user_data = get_user_session()
                
                # Reset danych użytkownika dla nowego przetwarzania
                user_data.reset_progress()
                
                # Pobierz parametry z formularza
                user_data.fuel_cost = float(request.form.get("fuel_cost", DEFAULT_FUEL_COST))
                user_data.driver_cost = float(request.form.get("driver_cost", DEFAULT_DRIVER_COST))
                user_data.matrix_type = request.form.get("matrix_type", "klient")

                # Ustaw odpowiednią macierz marży
                set_margin_matrix(user_data.matrix_type)

                # Czytaj plik w kontekście żądania
                user_data.file_bytes = file.read()
                
                logger.info(f"[{user_data.session_id[:8]}] Rozpoczynam przetwarzanie (fuel={user_data.fuel_cost}, driver={user_data.driver_cost}, matrix={user_data.matrix_type})")

                # Uruchom przetwarzanie w tle z session_id
                thread = threading.Thread(
                    target=background_processing,
                    args=(user_data.session_id,),
                    daemon=True,
                    name=f"BgProcess-{user_data.session_id[:8]}"
                )
                thread.start()
                user_data.thread = thread
                
                return render_template("processing.html")
                
            except Exception as e:
                logger.error(f"Błąd podczas uploadu pliku: {e}", exc_info=True)
                return render_template("error.html", message=str(e))
                
        return render_template("upload.html", 
                             default_fuel_cost=DEFAULT_FUEL_COST,
                             default_driver_cost=DEFAULT_DRIVER_COST)

    @app.route("/download")
    def download():
        """
        Endpoint do pobierania wyników przetwarzania.
        Każdy użytkownik pobiera tylko swoje wyniki.
        """
        try:
            user_data = get_user_session()
            session_id_short = user_data.session_id[:8]
            
            logger.info(
                f"[{session_id_short}] /download - "
                f"complete={user_data.processing_complete}, "
                f"has_result={user_data.result_excel is not None}"
            )
            
            if not user_data.processing_complete:
                logger.warning(f"[{session_id_short}] Próba pobrania - przetwarzanie w toku")
                return "Przetwarzanie jeszcze nie zostało zakończone.", 400
            
            if user_data.result_excel is None:
                logger.warning(f"[{session_id_short}] Próba pobrania - brak wyników")
                return "Brak wyników do pobrania.", 404
            
            # Sprawdź czy plik nie jest pusty
            user_data.result_excel.seek(0, 2)  # Przejdź na koniec
            file_size = user_data.result_excel.tell()
            user_data.result_excel.seek(0)  # Wróć na początek
            
            if file_size <= 100:
                logger.error(f"[{session_id_short}] Plik wynikowy jest zbyt mały: {file_size} bajtów")
                return "Plik Excel jest nieprawidłowy.", 500
            
            logger.info(f"[{session_id_short}] Wysyłam plik wynikowy ({file_size} bajtów)")
            
            return send_file(
                user_data.result_excel,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'zlecenia_{session_id_short}.xlsx'
            )
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania pliku: {e}", exc_info=True)
            return "Błąd podczas pobierania pliku.", 500

    @app.route("/progress")
    def progress():
        """
        Endpoint zwracający postęp przetwarzania dla aktualnego użytkownika.
        Każdy użytkownik widzi tylko swój postęp.
        """
        try:
            user_data = get_user_session()
            
            geocoding_progress = 0
            if user_data.geocoding_total > 0:
                geocoding_progress = min(
                    int((user_data.geocoding_current / user_data.geocoding_total) * 100),
                    100
                )
            
            # Dodaj informację o używanej macierzy
            matrix_name, matrix_file = get_margin_matrix_info()
            
            response_data = {
                'progress': user_data.progress,
                'current': user_data.current_row,
                'total': user_data.total_rows,
                'geocoding_progress': geocoding_progress,
                'error': user_data.progress == -1 or user_data.progress == -2,
                'preview_data': user_data.preview_data,
                'processing_complete': user_data.processing_complete,
                'matrix_name': matrix_name,
                'matrix_file': matrix_file,
                'session_id': user_data.session_id[:8]  # Dla debugowania
            }
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"Błąd w /progress: {e}", exc_info=True)
            return jsonify({
                'error': str(e),
                'progress': -1,
                'processing_complete': False
            }), 500

