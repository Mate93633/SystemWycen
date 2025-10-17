# 📝 Changelog - Wsparcie Wieloużytkownikowe v2.0

## 🎯 Co zostało zrobione?

Aplikacja "System Wyceny Tras" została przeprojektowana aby wspierać **wielu użytkowników jednocześnie**.

---

## ✅ Zmiany techniczne

### 1. **Nowa architektura sesji**

**Utworzone pliki:**
- `user_session_data.py` - Dataclass przechowująca dane pojedynczej sesji użytkownika
- `session_manager.py` - Manager zarządzający wszystkimi sesjami użytkowników
- `test_concurrent_users.py` - Skrypt do testowania równoczesnych użytkowników

**Zmienione pliki:**
- `appGPT.py` - Główna aplikacja Flask
  - Usunięto zmienne globalne (PROGRESS, RESULT_EXCEL, CURRENT_ROW, itp.)
  - Dodano Flask session management
  - Każdy endpoint używa `get_user_session()` do izolacji danych
  - Background processing działa per-użytkownik
  
- `requirements.txt` - Dodano APScheduler>=3.10.4

- `readme.md` - Zaktualizowano dokumentację

### 2. **Izolacja danych użytkowników**

**Przed:**
```python
# Globalne zmienne - wspólne dla wszystkich
PROGRESS = 0
RESULT_EXCEL = None
CURRENT_ROW = 0
```

**Po:**
```python
# Każdy użytkownik ma swoją sesję
user_data = get_user_session()
user_data.progress = 50
user_data.result_excel = BytesIO(...)
user_data.current_row = 10
```

### 3. **Bezpieczeństwo sesji**

- **Unikalne ID sesji:** 32-bajtowe tokeny (secrets.token_urlsafe)
- **HttpOnly cookies:** Ochrona przed XSS
- **Automatyczne czyszczenie:** Sesje starsze niż 24h są usuwane
- **Thread-safe:** RLock dla synchronizacji dostępu

### 4. **Monitorowanie**

**Nowe endpointy:**
- `/admin/sessions` - Podgląd wszystkich aktywnych sesji
- `/admin/cleanup_sessions` - Ręczne wymuszone czyszczenie starych sesji

---

## 🐛 Naprawione błędy podczas implementacji

### Bug #1: DEADLOCK w SessionManager
**Problem:** `get_session()` blokował lock, potem wywoływał `create_session()` który próbował znowu zablokować ten sam lock.

**Rozwiązanie:** Zmieniono `threading.Lock()` na `threading.RLock()` (Reentrant Lock).

```python
# Przed
self._lock = threading.Lock()

# Po
self._lock = threading.RLock()  # Pozwala na recursive locking
```

### Bug #2: Zmienne globalne w error handling
**Problem:** `CURRENT_ROW` i `TOTAL_ROWS` były używane w blokach `except`, ale już nie istniały jako globalne.

**Rozwiązanie:** Dodano fallback do `user_data`:
```python
current_row_num = user_data.current_row if user_data else (CURRENT_ROW if 'CURRENT_ROW' in globals() else i+1)
```

### Bug #3: Debug mode przerywał przetwarzanie
**Problem:** Flask `debug=True` powodował auto-reload, który zabijał background threads.

**Rozwiązanie:** Zmieniono na `debug=False` w production.

---

## 📊 Korzyści

### Dla użytkowników:
✅ Wielu użytkowników może korzystać z aplikacji jednocześnie  
✅ Każdy użytkownik widzi tylko swoje dane  
✅ Brak konfliktów i nadpisywania wyników  
✅ Automatyczne czyszczenie starych sesji  

### Dla developerów:
✅ Kod zgodny z zasadami OOP  
✅ Łatwe dodawanie nowych funkcjonalności per-użytkownik  
✅ Thread-safe operations  
✅ Monitorowanie i debugging ułatwione  

---

## 🧪 Jak przetestować?

### Test 1: Ręczny test dwóch użytkowników
1. Otwórz aplikację w Chrome: `http://localhost:5000`
2. Otwórz aplikację w Firefox: `http://localhost:5000`
3. Upload różnych plików w obu przeglądarkach
4. Sprawdź czy oba przetwarzania działają równolegle

### Test 2: Automatyczny test
```bash
python test_concurrent_users.py
```

### Test 3: Monitoring sesji
Otwórz w przeglądarce: `http://localhost:5000/admin/sessions`

---

## 🔧 Konfiguracja

W `appGPT.py` możesz dostosować:

```python
# Maksymalny czas życia sesji (domyślnie 24h)
session_manager = SessionManager(max_age_hours=24)

# Częstotliwość czyszczenia sesji (domyślnie co 1h)
cleanup_scheduler = SessionCleanupScheduler(session_manager, interval_hours=1)

# Permanent session lifetime (Flask)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
```

---

## 📚 Architektura

```
┌─────────────────────────────────────────────────────────┐
│                     Flask App                           │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Endpoint: /upload                                │  │
│  │  1. get_user_session() → UserSessionData         │  │
│  │  2. Zapisz parametry w user_data                 │  │
│  │  3. Start background_processing(session_id)      │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  SessionManager (thread-safe)                     │  │
│  │  ├─ session_1: UserSessionData (user A)          │  │
│  │  ├─ session_2: UserSessionData (user B)          │  │
│  │  └─ session_3: UserSessionData (user C)          │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Background Threads                               │  │
│  │  ├─ Thread A → process_przetargi(session_1)      │  │
│  │  ├─ Thread B → process_przetargi(session_2)      │  │
│  │  └─ Thread C → process_przetargi(session_3)      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Wdrożenie

### Krok 1: Zainstaluj nowe zależności
```bash
pip install -r requirements.txt
```

### Krok 2: Uruchom aplikację
```bash
python appGPT.py
```

### Krok 3: Testuj!
Otwórz aplikację w wielu przeglądarkach i przetestuj równoczesne przetwarzanie.

---

## 📞 Wsparcie

Jeśli napotkasz problemy:
1. Sprawdź logi w konsoli (poziom INFO)
2. Sprawdź aktywne sesje: `/admin/sessions`
3. Wymuś czyszczenie sesji: `/admin/cleanup_sessions`

---

**Data wydania:** 2025-10-17  
**Wersja:** 2.0  
**Status:** ✅ Gotowe do produkcji

