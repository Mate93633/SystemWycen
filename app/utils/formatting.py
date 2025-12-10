"""
Funkcje formatowania i konwersji danych.

Zawiera funkcje pomocnicze do formatowania wartości liczbowych,
walut, współrzędnych i tekstu.
"""

import re
import unicodedata
import pandas as pd


def safe_float(value):
    """
    Bezpiecznie konwertuje wartość na float.
    
    Obsługuje różne formaty wejściowe (string z przecinkiem, NaN, None).
    
    Args:
        value: Wartość do konwersji (może być string, float, None, NaN)
    
    Returns:
        float lub None jeśli konwersja nie jest możliwa
    """
    if pd.isna(value) or str(value).strip().lower() in ['nan', 'none', '']:
        return None
    try:
        return float(str(value).strip().replace(',', '.'))
    except (ValueError, TypeError):
        return None


def format_currency(value):
    """
    Formatuje wartość jako kwotę pieniężną (zaokrągloną do 2 miejsc po przecinku).
    
    Args:
        value: Wartość do sformatowania
    
    Returns:
        float zaokrąglony do 2 miejsc lub None
    """
    if value is None or pd.isna(value):
        return None
    try:
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None


def format_coordinates(lat, lon, default_text="Brak danych"):
    """
    Formatuje współrzędne geograficzne jako string.
    
    Args:
        lat: Szerokość geograficzna
        lon: Długość geograficzna
        default_text: Tekst zwracany gdy współrzędne są None
    
    Returns:
        String w formacie "lat, lon" lub default_text
    """
    return f"{lat}, {lon}" if None not in (lat, lon) else default_text


def clean_text(text):
    """
    Czyści tekst z znaków specjalnych i normalizuje do ASCII.
    
    Używane do tworzenia kluczy cache i porównywania tekstów.
    
    Args:
        text: Tekst do wyczyszczenia
    
    Returns:
        Znormalizowany tekst (lowercase, tylko litery i cyfry)
    """
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text.lower().strip()


def select_best_rate(row, rate_columns):
    """
    Wybiera najlepszą stawkę z dostępnych kolumn.
    
    Iteruje przez kolumny stawek i zwraca pierwszą niepustą wartość.
    
    Args:
        row: Wiersz DataFrame (dict-like)
        rate_columns: Lista nazw kolumn ze stawkami (w kolejności preferencji)
    
    Returns:
        dict z kluczami 'rate' i 'period' lub None
    """
    for col in rate_columns:
        rate = safe_float(row.get(col))
        if rate is not None:
            # Zwróć zarówno stawkę jak i okres
            period = col.split('_')[-1] if '_' in col else '3m'  # Domyślnie 3m
            return {'rate': rate, 'period': period}
    return None


def calculate_fracht(distance, rate):
    """
    Oblicza fracht (koszt transportu) na podstawie dystansu i stawki.
    
    Args:
        distance: Dystans w km
        rate: Stawka EUR/km
    
    Returns:
        float (fracht w EUR) lub None
    """
    if distance is None or rate is None:
        return None
    try:
        return distance * rate
    except TypeError:
        return None

