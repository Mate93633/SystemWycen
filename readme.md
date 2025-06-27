# System Wyceny Tras - Dokumentacja

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**System Wyceny Tras** to profesjonalna aplikacja webowa do automatycznego obliczania kosztów transportu drogowego w Europie.

## 📋 Spis treści

- [Wprowadzenie](#wprowadzenie)
- [Wymagania systemowe](#wymagania-systemowe)
- [Instalacja i konfiguracja](#instalacja-i-konfiguracja)
- [Szybki start](#szybki-start)
- [Architektura aplikacji](#architektura-aplikacji)
- [Funkcjonalności](#funkcjonalności)
- [Interfejs użytkownika](#interfejs-użytkownika)
- [API Endpoints](#api-endpoints)
- [Integracje zewnętrzne](#integracje-zewnętrzne)
- [System cache'owania](#system-cacheowania)
- [Geokodowanie](#geokodowanie)
- [Obliczanie tras i kosztów](#obliczanie-tras-i-kosztów)
- [Pliki konfiguracyjne](#pliki-konfiguracyjne)
- [Zarządzanie błędami](#zarządzanie-błędami)
- [Monitoring i logowanie](#monitoring-i-logowanie)
- [Przewodnik użytkownika](#przewodnik-użytkownika)
- [FAQ](#faq)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)

## 🚀 Wprowadzenie

System Wyceny Tras to zaawansowana aplikacja przeznaczona do automatyzacji procesu wyceny transportu drogowego. Aplikacja umożliwia:

- ✅ Automatyczne obliczanie kosztów transportu dla tras europejskich
- ✅ Przetwarzanie wsadowe plików Excel z wieloma trasami
- ✅ Precyzyjne geokodowanie lokalizacji
- ✅ Integrację z API PTV Group dla tras i opłat drogowych
- ✅ Optymalizację tras z unikaniem wybranych krajów
- ✅ Kalkulację marży na podstawie danych historycznych

### 🎯 Obszar zastosowań
- Firmy spedycyjne i transportowe
- Działy logistyki przedsiębiorstw
- Freelancerzy zajmujący się transportem
- Analitycy kosztów transportu

## 💻 Wymagania systemowe

### Minimalne wymagania
- **Python**: 3.8 lub nowszy
- **System**: Windows 10+, Linux Ubuntu 18.04+, macOS 10.15+
- **RAM**: 4 GB (zalecane 8 GB)
- **Dysk**: 2 GB wolnego miejsca
- **Internet**: Stałe połączenie (wymagane dla API)

### Zalecane wymagania
- **Python**: 3.9+
- **RAM**: 8 GB lub więcej
- **Procesor**: 4 rdzenie lub więcej
- **Internet**: Szerokopasmowe (>10 Mbps)

## 🔧 Instalacja i konfiguracja

### 1. Klonowanie repozytorium
```bash
git clone <repository-url>
cd Wyceny
```

### 2. Tworzenie środowiska wirtualnego
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Instalacja zależności
```bash
pip install -r requirements.txt
```

### 4. Konfiguracja kluczy API
W pliku `appGPT.py` skonfiguruj klucz API PTV:
```python
PTV_API_KEY = "TWÓJ_KLUCZ_API_PTV"
```

> **⚠️ Uwaga**: Zalecamy użycie zmiennych środowiskowych dla kluczy API w środowisku produkcyjnym.

### 5. Uruchomienie aplikacji
```bash
python appGPT.py
```

Aplikacja będzie dostępna pod adresem: `http://localhost:5000`

## ⚡ Szybki start

### Przetwarzanie pliku Excel

1. **Przygotuj plik Excel** z kolumnami:
   - Kraj załadunku
   - Kod pocztowy załadunku  
   - Miasto załadunku (opcjonalne)
   - Kraj rozładunku
   - Kod pocztowy rozładunku
   - Miasto rozładunku (opcjonalne)

2. **Wgraj plik** na stronie głównej aplikacji

3. **Skonfiguruj parametry**:
   - Typ matrycy marży (Klient/Targi)
   - Koszt paliwa (domyślnie 0.40 €/km)
   - Koszt kierowcy (domyślnie 210 €/dzień)

4. **Kliknij "Oblicz"** i monitoruj postęp

5. **Pobierz wyniki** w formie pliku Excel

### Testowanie pojedynczej trasy

1. Przejdź do `/test_route_form`
2. Wprowadź dane punktów załadunku i rozładunku
3. Ustaw parametry kosztów
4. Kliknij "Oblicz trasę"
5. Sprawdź wyniki z mapą Google

## 🏗️ Architektura aplikacji

### Struktura projektowa
Wyceny/
├── 📄 appGPT.py # Główny plik aplikacji Flask
├── 📄 ptv_api_manager.py # Menedżer API PTV
├── 📄 requirements.txt # Zależności Python
├── 📄 regions.csv # Mapowanie regionów
├── 📄 global_data.csv # Dane globalne
├── 📊 Matrix.xlsx # Matryca marży - klient
├── 📊 Matrix_Targi.xlsx # Matryca marży - targi
├── 📊 historical_rates.xlsx # Historyczne stawki
├── 📊 historical_rates_gielda.xlsx # Stawki giełdowe
├── 📁 templates/ # Szablony HTML
│ ├── base.html
│ ├── upload.html
│ ├── test_route_form.html
│ └── ...
├── 📁 static/ # Pliki statyczne
├── 💾 geo_cache/ # Cache geokodowania
├── 💾 route_cache/ # Cache tras
└── 💾 locations_cache/ # Cache lokalizacji


### Komponenty główne

#### 🌐 Flask Application (`appGPT.py`)
- Główny kontroler aplikacji
- Definicje endpointów HTTP
- Logika biznesowa
- Zarządzanie sesjami

#### 🛣️ PTV API Manager (`ptv_api_manager.py`)
- `PTVRouteManager`: Zarządzanie trasami
- `PTVRequestQueue`: Kolejkowanie zapytań
- `RouteCacheManager`: Cache'owanie wyników
- Obsługa rate limiting

#### 💾 System cache'owania
- `geo_cache`: Współrzędne geograficzne
- `route_cache`: Obliczone trasy
- `locations_cache`: Zweryfikowane lokalizacje

## ⭐ Funkcjonalności

### 📊 Przetwarzanie wsadowe plików Excel

**Format wejściowy**: `.xlsx`, `.xls`

**Wymagane kolumny**:
- Kraj załadunku
- Kod pocztowy załadunku
- Miasto załadunku (opcjonalne)
- Kraj rozładunku
- Kod pocztowy rozładunku
- Miasto rozładunku (opcjonalne)

**Dane wyjściowe**:
- 📏 Dystans (km)
- 🛣️ Podlot (km)
- ⛽ Koszt paliwa
- 💰 Opłaty drogowe
- 👨‍💼 Koszt kierowcy + leasing
- 📍 Koszt podlotu
- 💯 Opłaty/km
- 🧮 Suma kosztów
- 🗺️ Link do mapy Google
- 💵 Sugerowany fracht (historyczny i matrix)
- 📈 Oczekiwany zysk
- ⏱️ Transit time (dni)

### 🎯 Wycena pojedynczej trasy
- Formularz do wprowadzania danych
- Niestandardowe koszty
- Wybór typu matrycy marży
- Podgląd wyników w czasie rzeczywistym

### 🌍 Geokodowanie automatyczne
- Integracja z Nominatim (OpenStreetMap)
- Integracja z PTV Geocoding API
- System fallback przy błędach
- Możliwość ręcznej korekty współrzędnych

### 🚛 Optymalizacja tras
- Unikanie wybranych krajów (domyślnie Szwajcaria)
- Różne tryby routingu (FAST, ECO, SHORT)
- Obsługa opłat drogowych europejskich
- Kalkulacja podlotu

### 🗺️ System regionów
- Mapowanie kodów pocztowych na regiony
- Wsparcie dla 20+ krajów europejskich
- Elastyczne zarządzanie stawkami regionalnymi

## 🖥️ Interfejs użytkownika

### Dostępne widoki

| Endpoint | Opis | Funkcjonalność |
|----------|------|----------------|
| `/` | Strona główna | Upload pliku Excel, konfiguracja parametrów |
| `/test_route_form` | Pojedyncza trasa | Formularz dla jednej trasy |
| `/ungeocoded_locations` | Geokodowanie | Lista nierozpoznanych lokalizacji |
| `/progress` | Postęp | Monitoring przetwarzania |
| `/show_cache` | Cache | Zarządzanie pamięcią podręczną |

## 🔌 API Endpoints

### Główne endpointy

| Endpoint | Metoda | Opis | Parametry |
|----------|--------|------|-----------|
| `/` | GET, POST | Strona główna i upload | `file`, `matrix_type`, `fuel_cost`, `driver_cost` |
| `/progress` | GET | Status przetwarzania | - |
| `/download` | GET | Pobieranie wyników | - |
| `/test_route_form` | GET, POST | Formularz trasy | `load_country`, `load_postal`, `unload_country`, `unload_postal` |
| `/ungeocoded_locations` | GET, POST | Zarządzanie geokodowaniem | - |
| `/save_manual_coordinates` | POST | Zapisz współrzędne | `location_key`, `lat`, `lon` |

### Endpointy zarządzania

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/show_cache` | GET | Podgląd cache |
| `/save_cache` | GET | Zapis cache na dysk |
| `/clear_luxembourg_cache` | GET | Czyszczenie cache Luksemburga |
| `/ptv_stats` | GET | Statystyki PTV API |
| `/geocoding_progress` | GET | Postęp geokodowania |

## 🔗 Integracje zewnętrzne

### 🚗 PTV Group API
- **Endpoint**: `https://api.myptv.com/`
- **Funkcje**: Routing, geokodowanie, opłaty drogowe
- **Rate limiting**: 10 zapytań/sekundę
- **Wymagany klucz API**: ✅ Tak

```python
PTV_API_KEY = "YOUR_API_KEY"
ptv_manager = PTVRouteManager(PTV_API_KEY)
```

### 🌐 Nominatim (OpenStreetMap)
- **Endpoint**: `https://nominatim.openstreetmap.org/`
- **Funkcje**: Geokodowanie backup
- **Rate limiting**: 1 zapytanie/sekundę
- **Wymagany klucz API**: ❌ Nie

```python
geolocator = Nominatim(user_agent="wycena_transportu", timeout=15)
```

## 💾 System cache'owania

### Typy cache

#### 🌍 Geo Cache (`geo_cache`)
- **Cel**: Współrzędne geograficzne
- **Klucz**: `(kraj, kod_pocztowy, miasto)`
- **Czas życia**: Nieokreślony
- **Lokalizacja**: `geo_cache/`

#### 🛣️ Route Cache (`route_cache`)
- **Cel**: Obliczone trasy
- **Klucz**: `(współrzędne_start, współrzędne_koniec, parametry)`
- **Czas życia**: 7 dni
- **Lokalizacja**: `route_cache/`

#### 📍 Locations Cache (`locations_cache`)
- **Cel**: Zweryfikowane lokalizacje
- **Klucz**: `(kraj, kod_pocztowy)`
- **Czas życia**: Nieokreślony
- **Lokalizacja**: `locations_cache/`

### Zarządzanie cache

```python
# Zapis na dysk
def save_caches():
    joblib.dump(dict(geo_cache), "geo_cache_backup.joblib")
    joblib.dump(dict(route_cache), "route_cache_backup.joblib")

# Ładowanie z dysku
def load_caches():
    geo_cache.update(joblib.load("geo_cache_backup.joblib"))
    route_cache.update(joblib.load("route_cache_backup.joblib"))
```

## 🌍 Geokodowanie

### Proces geokodowania

1. **Sprawdzenie cache** - Wyszukanie w lokalnym cache
2. **PTV Geocoding** - Próba przez PTV API
3. **Nominatim fallback** - Backup przez OpenStreetMap
4. **Manual override** - Ręczne wprowadzenie

### Funkcje geokodowania

```python
def get_coordinates(country, postal_code, city=None):
    """
    Pobiera współrzędne geograficzne dla lokalizacji
    
    Args:
        country (str): Kod kraju
        postal_code (str): Kod pocztowy
        city (str, optional): Nazwa miasta
    
    Returns:
        tuple: (latitude, longitude) lub None
    """

def verify_city_postal_code_match(country, postal_code, city, threshold_km=100):
    """
    Weryfikuje czy miasto i kod pocztowy są dopasowane
    
    Args:
        country (str): Kod kraju
        postal_code (str): Kod pocztowy
        city (str): Nazwa miasta
        threshold_km (int): Próg odległości w km
    
    Returns:
        dict: Wynik weryfikacji
    """
```

## 💰 Obliczanie tras i kosztów

### Komponenty kosztów

#### ⛽ Koszt paliwa
```python
fuel_cost = distance_km * fuel_cost_per_km  # Domyślnie: 0.40 €/km
```

#### 💰 Opłaty drogowe
- Pobierane z PTV API
- Podział na: drogi, tunele, mosty, promy
- Różne systemy płatności (vinieta, pay-per-use)

#### 👨‍💼 Koszt kierowcy
```python
driver_days = calculate_driver_days(distance_km)
driver_cost = driver_days * daily_driver_cost  # Domyślnie: 210 €/dzień
```

#### 🛣️ Podlot
- Średni koszt dojazdu do punktu załadunku
- Obliczany na podstawie danych historycznych
- Uwzględnia opłaty i paliwo

### Algorytm obliczania tras

```python
# 1. Geokodowanie punktów
load_coords = get_coordinates(load_country, load_postal, load_city)
unload_coords = get_coordinates(unload_country, unload_postal, unload_city)

# 2. Obliczanie trasy
route_result = ptv_manager.get_route_distance(
    load_coords, 
    unload_coords,
    avoid_switzerland=True,
    routing_mode="FAST"
)

# 3. Kalkulacja kosztów
total_cost = fuel_cost + toll_cost + driver_cost + podlot_cost
```

## 📁 Pliki konfiguracyjne

### 🗺️ regions.csv
Mapowanie kodów pocztowych na regiony:
```csv
kod;kraj;region
10;AT;ATWSCHÓD
11;AT;ATWSCHÓD
...
```

### 📊 Matrix.xlsx / Matrix_Targi.xlsx
- Matryca marży dla różnych relacji
- Regiony załadunku vs rozładunku
- Oczekiwana marża w €/dzień
- Różne matryca dla różnych typów klientów

### 📈 historical_rates.xlsx
- Historyczne stawki transportowe
- Dane z przeszłych transakcji
- Stawki €/km dla różnych relacji
- Wykorzystywane do sugestii cen

### 🌐 global_data.csv
- Globalne dane konfiguracyjne
- Parametry systemowe
- Domyślne wartości
- Mapowania krajów

## ⚠️ Zarządzanie błędami

### Typy wyjątków

```python
class GeocodeException(Exception):
    """Wyjątek sygnalizujący potrzebę ręcznego geokodowania."""
    def __init__(self, ungeocoded_locations):
        self.ungeocoded_locations = ungeocoded_locations

class LocationVerificationRequired(Exception):
    """Wyjątek sygnalizujący potrzebę weryfikacji lokalizacji."""
    def __init__(self, locations_to_verify):
        self.locations_to_verify = locations_to_verify
```

### Obsługa błędów API

**PTV API Errors:**
- `429`: Rate limiting
- `401`: Unauthorized
- `500+`: Server errors
- Timeout errors

**Strategia retry:**
```python
max_retries = 3
retry_delay = 2  # sekundy między próbami

for attempt in range(max_retries):
    try:
        result = api_call()
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        time.sleep(retry_delay * (2 ** attempt))
```

## 📊 Monitoring i logowanie

### Konfiguracja logów
```python
logging.basicConfig(
    level=logging.ERROR,
    format='%(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

### Pliki logów
- `app.log` - Główne logi aplikacji
- `ptv_timing.log` - Logi wydajności PTV API
- `performance.log` - Logi wydajności ogólnej

### Metryki monitorowane
- Liczba przetworzonych tras
- Czas odpowiedzi API
- Współczynnik hit/miss cache
- Błędy geokodowania
- Wykorzystanie rate limitów

## 📖 Przewodnik użytkownika

### Krok 1: Przygotowanie pliku Excel

Przygotuj plik Excel z następującymi kolumnami:

| Kolumna | Wymagana | Przykład | Opis |
|---------|----------|----------|------|
| Kraj załadunku | ✅ | PL | Kod kraju |
| Kod pocztowy załadunku | ✅ | 00-001 | Kod pocztowy |
| Miasto załadunku | ❌ | Warszawa | Nazwa miasta |
| Kraj rozładunku | ✅ | DE | Kod kraju docelowego |
| Kod pocztowy rozładunku | ✅ | 10115 | Kod pocztowy |
| Miasto rozładunku | ❌ | Berlin | Nazwa miasta |

### Krok 2: Upload i konfiguracja

1. Przejdź na stronę główną aplikacji
2. Wybierz przygotowany plik Excel
3. Ustaw typ matrycy marży:
   - **Matrix Klient** - dla standardowych klientów
   - **Matrix Targi** - dla targów i eventów
4. Skonfiguruj koszty:
   - **Koszt paliwa** (domyślnie 0.40 €/km)
   - **Koszt kierowcy + leasing** (domyślnie 210 €/dzień)
5. Kliknij "Oblicz"

### Krok 3: Monitorowanie postępu

- Zostaniesz przekierowany na stronę postępu
- Pasek postępu pokazuje aktualny stan
- W przypadku problemów z geokodowaniem otrzymasz powiadomienie
- Po zakończeniu możesz pobrać wyniki

### Krok 4: Pobieranie wyników

Wynikowy plik Excel zawiera wszystkie obliczenia i analizy kosztów.

## ❓ FAQ

### Jakie kraje są obsługiwane?
Aplikacja obsługuje 20+ krajów europejskich:
- 🇵🇱 Polska (PL), 🇩🇪 Niemcy (DE), 🇫🇷 Francja (FR), 🇮🇹 Włochy (IT)
- 🇪🇸 Hiszpania (ES), 🇳🇱 Holandia (NL), 🇧🇪 Belgia (BE), 🇦🇹 Austria (AT)
- 🇨🇿 Czechy (CZ), 🇸🇰 Słowacja (SK), 🇭🇺 Węgry (HU), 🇸🇮 Słowenia (SI)
- 🇨🇭 Szwajcaria (CH), 🇵🇹 Portugalia (PT), 🇬🇷 Grecja (GR)
- 🇸🇪 Szwecja (SE), 🇳🇴 Norwegia (NO), 🇩🇰 Dania (DK), 🇫🇮 Finlandia (FI)
- 🇱🇺 Luksemburg (LU), 🇬🇧 Wielka Brytania (UK)

### Dlaczego aplikacja unika Szwajcarii?
Szwajcaria ma specjalne regulacje dotyczące transportu ciężarowego i wysokie opłaty. Domyślnie trasy omijają Szwajcarię dla optymalizacji kosztów, ale można to wyłączyć dla tras do/ze Szwajcarii.

### Jak długo trwa przetwarzanie pliku?
Czas zależy od liczby tras i stanu cache:
- **10-50 tras**: 2-5 minut
- **50-200 tras**: 5-15 minut  
- **200+ tras**: 15+ minut

### Co zrobić gdy geokodowanie kończy się błędem?
1. Sprawdź poprawność kodów pocztowych
2. Uzupełnij nazwy miast
3. Użyj funkcji ręcznego geokodowania
4. Skontaktuj się z administratorem w przypadku problemów z API

### Skąd pochodzą historyczne stawki?
Stawki pochodzą z plików:
- `historical_rates.xlsx` - dane historyczne firmy
- `historical_rates_gielda.xlsx` - dane z giełd transportowych

## 🔧 Rozwiązywanie problemów

### Problem: Aplikacja nie startuje

**Możliwe przyczyny:**
- Brak zainstalowanych zależności
- Nieprawidłowa wersja Python
- Zajęty port 5000

**Rozwiązania:**
```bash
# Sprawdź wersję Python
python --version

# Zainstaluj zależności ponownie
pip install -r requirements.txt

# Uruchom na innym porcie
export FLASK_RUN_PORT=5001
python appGPT.py
```

### Problem: Błędy geokodowania

**Objawy:**
- Brak współrzędnych dla lokalizacji
- Błąd "Nierozpoznane lokalizacje"

**Rozwiązania:**
1. Sprawdź połączenie internetowe
2. Zweryfikuj kody pocztowe
3. Użyj pełnych nazw miast
4. Sprawdź status API PTV

### Problem: Wysokie czasy odpowiedzi

**Możliwe przyczyny:**
- Brak cache dla nowych lokalizacji
- Problemy z API PTV
- Przeciążenie serwera

**Rozwiązania:**
1. Sprawdź status cache: `/show_cache`
2. Zweryfikuj statystyki PTV: `/ptv_stats`
3. Wyczyść stary cache: `/clear_locations_cache`

### Problem: Błędy API PTV

**Kody błędów:**
- **401**: Nieprawidłowy klucz API
- **429**: Przekroczony limit zapytań
- **500**: Błąd serwera PTV

**Rozwiązania:**
1. Sprawdź klucz API PTV
2. Poczekaj na reset limitu (1 minuta)
3. Skontaktuj się z supportem PTV

## 📞 Kontakt i wsparcie

Dla otrzymania wsparcia technicznego lub zgłoszenia błędów:

- **Dokumentacja**: Ten dokument
- **Logi**: Sprawdź pliki `app.log`, `ptv_timing.log`
- **Cache**: Użyj `/show_cache` do diagnostyki
- **Status**: Sprawdź `/ptv_stats` dla statusu API

---

## 📄 Licencja

Ten projekt jest udostępniony na licencji MIT. Zobacz plik [LICENSE](LICENSE) po więcej szczegółów.

## 🤝 Wkład w projekt

Jeśli chcesz przyczynić się do rozwoju projektu:

1. Fork repozytorium
2. Stwórz branch dla swojej funkcji (`git checkout -b feature/AmazingFeature`)
3. Commituj swoje zmiany (`git commit -m 'Add some AmazingFeature'`)
4. Push do brancha (`git push origin feature/AmazingFeature`)
5. Otwórz Pull Request

---

**Wersja dokumentacji**: 1.0  
**Data ostatniej aktualizacji**: 2024  
**Kompatybilność**: Python 3.8+, Flask 2.0+

---

<div align="center">
  <strong>System Wyceny Tras</strong><br>
  Profesjonalne rozwiązanie do wyceny transportu drogowego
</div>