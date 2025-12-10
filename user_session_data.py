"""
Moduł definiujący strukturę danych dla sesji użytkownika.

Ten moduł zawiera dataclass reprezentującą stan sesji pojedynczego użytkownika
w systemie wyceny tras. Zgodnie z zasadą Single Responsibility Principle,
odpowiada wyłącznie za strukturę danych sesji.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import io
import time


@dataclass
class UserSessionData:
    """
    Reprezentuje dane sesji pojedynczego użytkownika.
    
    Attributes:
        session_id: Unikalny identyfikator sesji
        progress: Postęp przetwarzania w procentach (0-100, -1 dla błędu geokodowania, -2 dla weryfikacji)
        result_excel: BytesIO z wynikowym plikiem Excel
        current_row: Aktualnie przetwarzany wiersz
        total_rows: Całkowita liczba wierszy do przetworzenia
        processing_complete: Czy przetwarzanie zostało zakończone
        geocoding_current: Liczba dotychczas geokodowanych lokalizacji
        geocoding_total: Całkowita liczba lokalizacji do geokodowania
        preview_data: Dane do podglądu w interfejsie użytkownika
        locations_to_verify: Lista lokalizacji wymagających weryfikacji
        file_bytes: Bajty uploadowanego pliku Excel
        fuel_cost: Koszt paliwa (EUR/km)
        driver_cost: Koszt kierowcy (EUR/dzień)
        matrix_type: Typ matrycy marży ('klient' lub 'targi')
        created_at: Timestamp utworzenia sesji
        last_activity: Timestamp ostatniej aktywności
        thread: Referencja do wątku przetwarzającego (opcjonalna)
    """
    
    session_id: str
    progress: int = 0
    result_excel: Optional[io.BytesIO] = None
    current_row: int = 0
    total_rows: int = 0
    processing_complete: bool = False
    geocoding_current: int = 0
    geocoding_total: int = 0
    preview_data: Dict[str, Any] = field(default_factory=lambda: {
        'headers': [
            'Kraj załadunku',
            'Kod pocztowy załadunku',
            'Kraj rozładunku',
            'Kod pocztowy rozładunku',
            'Dystans (km)',
            'Podlot (km)',
            'Odjazd (km)',
            'Koszt paliwa',
            'Opłaty drogowe',
            'Koszt kierowcy + leasing',
            'Koszt podlotu (opłaty + paliwo)',
            'Koszt odjazdu (opłaty + paliwo)',
            'Opłaty/km',
            'Opłaty drogowe (szczegóły)',
            'Suma kosztów',
            'Link do mapy',
            'Sugerowany fracht wg historycznych stawek',
            'Stawka minimalna (€/km)',
            'Suma kosztów (bez podlotu i odjazdu)',
            'Oczekiwany zysk',
            'Transit time (dni)'
        ],
        'rows': [],
        'total_count': 0
    })
    locations_to_verify: List[Any] = field(default_factory=list)
    file_bytes: Optional[bytes] = None
    fuel_cost: float = 0.40
    driver_cost: float = 210.0
    matrix_type: str = 'klient'
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    thread: Optional[Any] = None
    
    def update_activity(self) -> None:
        """Aktualizuje timestamp ostatniej aktywności."""
        self.last_activity = time.time()
    
    def get_age_minutes(self) -> int:
        """
        Zwraca wiek sesji w minutach.
        
        Returns:
            Liczba minut od utworzenia sesji
        """
        return int((time.time() - self.created_at) / 60)
    
    def get_inactivity_minutes(self) -> int:
        """
        Zwraca czas bezczynności w minutach.
        
        Returns:
            Liczba minut od ostatniej aktywności
        """
        return int((time.time() - self.last_activity) / 60)
    
    def reset_progress(self) -> None:
        """Resetuje dane przetwarzania zachowując konfigurację."""
        self.progress = 0
        self.current_row = 0
        self.total_rows = 0
        self.geocoding_current = 0
        self.geocoding_total = 0
        self.preview_data = {
            'headers': self.preview_data.get('headers', []),
            'rows': [],
            'total_count': 0
        }
        self.result_excel = None
        self.processing_complete = False
        self.locations_to_verify = []
        self.update_activity()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konwertuje dane sesji do słownika (do serializacji JSON).
        
        Returns:
            Słownik z danymi sesji
        """
        return {
            'session_id': self.session_id[:8],  # Tylko pierwsze 8 znaków dla bezpieczeństwa
            'progress': self.progress,
            'current_row': self.current_row,
            'total_rows': self.total_rows,
            'processing_complete': self.processing_complete,
            'geocoding_current': self.geocoding_current,
            'geocoding_total': self.geocoding_total,
            'preview_data': self.preview_data,
            'fuel_cost': self.fuel_cost,
            'driver_cost': self.driver_cost,
            'matrix_type': self.matrix_type,
            'age_minutes': self.get_age_minutes(),
            'inactivity_minutes': self.get_inactivity_minutes(),
            'has_result': self.result_excel is not None
        }

