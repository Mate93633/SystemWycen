"""
Moduł zarządzania sesjami użytkowników.

Ten moduł implementuje wzorzec Manager/Coordinator do obsługi sesji użytkowników
w aplikacji wieloużytkownikowej. Odpowiada za:
- Tworzenie i usuwanie sesji
- Thread-safe dostęp do danych sesji
- Czyszczenie wygasłych sesji
- Generowanie unikalnych identyfikatorów sesji

Zgodnie z zasadą Single Responsibility Principle, ten moduł odpowiada
wyłącznie za zarządzanie cyklem życia sesji użytkowników.
"""

import secrets
import threading
import logging
from typing import Dict, Optional, List
from datetime import timedelta

from user_session_data import UserSessionData


logger = logging.getLogger(__name__)


class SessionManager:
    """
    Zarządza sesjami użytkowników w aplikacji.
    
    Klasa zapewnia thread-safe operacje na sesjach użytkowników,
    automatyczne czyszczenie starych sesji oraz generowanie
    unikalnych identyfikatorów.
    
    Attributes:
        _sessions: Słownik przechowujący wszystkie aktywne sesje
        _lock: Lock do synchronizacji dostępu do sesji
        _max_age_hours: Maksymalny wiek sesji w godzinach
    """
    
    def __init__(self, max_age_hours: int = 24):
        """
        Inicjalizuje SessionManager.
        
        Args:
            max_age_hours: Maksymalny czas życia sesji w godzinach (domyślnie 24h)
        """
        self._sessions: Dict[str, UserSessionData] = {}
        self._lock = threading.RLock()  # RLock zamiast Lock aby umożliwić recursive locking
        self._max_age_hours = max_age_hours
        logger.info(f"SessionManager zainicjalizowany (max_age={max_age_hours}h)")
    
    def generate_session_id(self) -> str:
        """
        Generuje unikalny, bezpieczny identyfikator sesji.
        
        Returns:
            32-bajtowy token URL-safe
        """
        return secrets.token_urlsafe(32)
    
    def create_session(self, session_id: Optional[str] = None) -> UserSessionData:
        """
        Tworzy nową sesję użytkownika.
        
        Args:
            session_id: Opcjonalny identyfikator sesji (jeśli None, zostanie wygenerowany)
        
        Returns:
            Nowo utworzony obiekt UserSessionData
        """
        if session_id is None:
            session_id = self.generate_session_id()
        
        with self._lock:
            if session_id in self._sessions:
                logger.warning(f"Sesja {session_id[:8]}... już istnieje, zwracam istniejącą")
                return self._sessions[session_id]
            
            new_session = UserSessionData(session_id=session_id)
            self._sessions[session_id] = new_session
            logger.info(f"Utworzono nową sesję: {session_id[:8]}... (total: {len(self._sessions)})")
            
            return new_session
    
    def get_session(self, session_id: str, create_if_missing: bool = True) -> Optional[UserSessionData]:
        """
        Pobiera sesję użytkownika po ID.
        
        Args:
            session_id: Identyfikator sesji
            create_if_missing: Czy utworzyć nową sesję jeśli nie istnieje
        
        Returns:
            Obiekt UserSessionData lub None jeśli nie znaleziono i create_if_missing=False
        """
        with self._lock:
            if session_id not in self._sessions:
                if create_if_missing:
                    logger.info(f"Sesja {session_id[:8]}... nie istnieje, tworzę nową")
                    return self.create_session(session_id)
                else:
                    logger.warning(f"Sesja {session_id[:8]}... nie znaleziona")
                    return None
            
            session = self._sessions[session_id]
            session.update_activity()
            return session
    
    def delete_session(self, session_id: str) -> bool:
        """
        Usuwa sesję użytkownika.
        
        Args:
            session_id: Identyfikator sesji do usunięcia
        
        Returns:
            True jeśli sesja została usunięta, False jeśli nie istniała
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Usunięto sesję: {session_id[:8]}... (pozostało: {len(self._sessions)})")
                return True
            else:
                logger.warning(f"Próba usunięcia nieistniejącej sesji: {session_id[:8]}...")
                return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Usuwa wygasłe sesje na podstawie czasu bezczynności.
        
        Returns:
            Liczba usuniętych sesji
        """
        max_age_seconds = self._max_age_hours * 3600
        expired_sessions = []
        
        with self._lock:
            for session_id, session_data in self._sessions.items():
                inactivity_seconds = session_data.get_inactivity_minutes() * 60
                if inactivity_seconds > max_age_seconds:
                    expired_sessions.append(session_id)
        
        # Usuwamy poza lockiem, aby nie blokować innych operacji
        deleted_count = 0
        for session_id in expired_sessions:
            if self.delete_session(session_id):
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Wyczyszczono {deleted_count} wygasłych sesji")
        
        return deleted_count
    
    def get_active_sessions_count(self) -> int:
        """
        Zwraca liczbę aktywnych sesji.
        
        Returns:
            Liczba sesji w pamięci
        """
        with self._lock:
            return len(self._sessions)
    
    def get_all_sessions_info(self) -> List[Dict]:
        """
        Zwraca informacje o wszystkich aktywnych sesjach.
        
        Returns:
            Lista słowników z informacjami o sesjach
        """
        with self._lock:
            return [session.to_dict() for session in self._sessions.values()]
    
    def session_exists(self, session_id: str) -> bool:
        """
        Sprawdza czy sesja o danym ID istnieje.
        
        Args:
            session_id: Identyfikator sesji
        
        Returns:
            True jeśli sesja istnieje, False w przeciwnym razie
        """
        with self._lock:
            return session_id in self._sessions
    
    def reset_session_progress(self, session_id: str) -> bool:
        """
        Resetuje postęp przetwarzania dla sesji.
        
        Args:
            session_id: Identyfikator sesji
        
        Returns:
            True jeśli operacja się powiodła, False jeśli sesja nie istnieje
        """
        session = self.get_session(session_id, create_if_missing=False)
        if session is None:
            return False
        
        session.reset_progress()
        logger.info(f"Zresetowano postęp dla sesji: {session_id[:8]}...")
        return True
    
    def get_session_statistics(self) -> Dict:
        """
        Zwraca statystyki dotyczące sesji.
        
        Returns:
            Słownik ze statystykami
        """
        with self._lock:
            total_sessions = len(self._sessions)
            active_processing = sum(
                1 for s in self._sessions.values() 
                if not s.processing_complete and s.total_rows > 0
            )
            completed = sum(
                1 for s in self._sessions.values() 
                if s.processing_complete
            )
            
            return {
                'total_sessions': total_sessions,
                'active_processing': active_processing,
                'completed': completed,
                'idle': total_sessions - active_processing - completed,
                'max_age_hours': self._max_age_hours
            }


class SessionCleanupScheduler:
    """
    Harmonogram czyszczenia wygasłych sesji.
    
    Uruchamia okresowe zadanie czyszczące stare sesje w tle.
    Wykorzystuje wzorzec Coordinator do orkiestracji zadań czyszczenia.
    """
    
    def __init__(self, session_manager: SessionManager, interval_hours: int = 1):
        """
        Inicjalizuje scheduler.
        
        Args:
            session_manager: Instancja SessionManager do czyszczenia
            interval_hours: Interwał czyszczenia w godzinach
        """
        self.session_manager = session_manager
        self.interval_hours = interval_hours
        self.scheduler = None
        logger.info(f"SessionCleanupScheduler zainicjalizowany (interval={interval_hours}h)")
    
    def _cleanup_job(self):
        """Zadanie czyszczące uruchamiane przez scheduler."""
        try:
            logger.info("Uruchamiam zadanie czyszczenia sesji...")
            deleted_count = self.session_manager.cleanup_expired_sessions()
            stats = self.session_manager.get_session_statistics()
            logger.info(
                f"Czyszczenie zakończone: usunięto {deleted_count} sesji, "
                f"aktywnych: {stats['total_sessions']}"
            )
        except Exception as e:
            logger.error(f"Błąd podczas czyszczenia sesji: {e}", exc_info=True)
    
    def start(self):
        """Uruchamia scheduler czyszczenia."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            
            self.scheduler = BackgroundScheduler()
            self.scheduler.add_job(
                func=self._cleanup_job,
                trigger="interval",
                hours=self.interval_hours,
                id='session_cleanup',
                name='Session Cleanup Job',
                replace_existing=True
            )
            self.scheduler.start()
            logger.info("Scheduler czyszczenia sesji uruchomiony")
            
        except ImportError:
            logger.warning(
                "APScheduler nie jest zainstalowany. "
                "Automatyczne czyszczenie sesji nie będzie działać. "
                "Zainstaluj: pip install APScheduler"
            )
        except Exception as e:
            logger.error(f"Błąd podczas uruchamiania schedulera: {e}", exc_info=True)
    
    def stop(self):
        """Zatrzymuje scheduler czyszczenia."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Scheduler czyszczenia sesji zatrzymany")
    
    def cleanup_now(self) -> int:
        """
        Wymusza natychmiastowe czyszczenie sesji.
        
        Returns:
            Liczba usuniętych sesji
        """
        return self.session_manager.cleanup_expired_sessions()

