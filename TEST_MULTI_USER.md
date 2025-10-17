# Test Wieloużytkownikowy - System Wyceny Tras

## 📋 Cel testu

Weryfikacja czy aplikacja może obsługiwać wielu użytkowników jednocześnie bez konfliktów danych.

## ✅ Kroki testowe

### Przygotowanie

1. **Zainstaluj nowe zależności:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Uruchom aplikację:**
   ```bash
   python appGPT.py
   ```

3. **Otwórz aplikację w przeglądarce:**
   - Przeglądarka 1 (Chrome): `http://localhost:5000`
   - Przeglądarka 2 (Firefox/Incognito): `http://localhost:5000`

---

### Test 1: Podstawowy test dwóch użytkowników

**User A (Chrome):**
1. Otwórz `http://localhost:5000`
2. Wybierz plik Excel (10-20 wierszy)
3. Ustaw parametry:
   - Koszt paliwa: 0.40
   - Koszt kierowcy: 210
   - Matrix: Klient
4. Kliknij "Oblicz"
5. **Zanotuj Session ID** z konsoli deweloperskiej (F12 → Network → progress → Response → session_id)

**User B (Firefox/Incognito):**
1. Otwórz `http://localhost:5000` (w tym samym czasie co User A)
2. Wybierz **inny** plik Excel (5-10 wierszy)
3. Ustaw **inne** parametry:
   - Koszt paliwa: 0.50
   - Koszt kierowcy: 250
   - Matrix: Targi
4. Kliknij "Oblicz"
5. **Zanotuj Session ID**

**Weryfikacja:**
- ✅ Oba użytkownicy widzą swoje własne postępy
- ✅ User A widzi total_rows odpowiadający jego plikowi
- ✅ User B widzi total_rows odpowiadający jego plikowi
- ✅ Postępy są niezależne (jeden nie nadpisuje drugiego)

---

### Test 2: Pobieranie wyników

**User A:**
1. Poczekaj na zakończenie przetwarzania (100%)
2. Kliknij "Pobierz wyniki"
3. Sprawdź pobrany plik `zlecenia_<session_id>.xlsx`

**User B:**
1. Poczekaj na zakończenie przetwarzania (100%)
2. Kliknij "Pobierz wyniki"
3. Sprawdź pobrany plik `zlecenia_<session_id>.xlsx`

**Weryfikacja:**
- ✅ User A pobiera plik z danymi TYLKO ze swojego uploadu
- ✅ User B pobiera plik z danymi TYLKO ze swojego uploadu
- ✅ Pliki mają różne nazwy (różne session_id)
- ✅ Zawartość plików odpowiada uploadowanym plikom

---

### Test 3: Monitoring sesji (Endpoint administracyjny)

1. Otwórz w nowej karcie: `http://localhost:5000/admin/sessions`

**Oczekiwany wynik:**
```json
{
  "statistics": {
    "total_sessions": 2,
    "active_processing": 0,
    "completed": 2,
    "idle": 0,
    "max_age_hours": 24
  },
  "active_sessions": [
    {
      "session_id": "abc12345",
      "progress": 100,
      "total_rows": 20,
      "current_row": 20,
      "complete": true,
      ...
    },
    {
      "session_id": "xyz67890",
      "progress": 100,
      "total_rows": 10,
      "current_row": 10,
      "complete": true,
      ...
    }
  ]
}
```

**Weryfikacja:**
- ✅ Widoczne dwie sesje z różnymi session_id
- ✅ Każda sesja ma swoje total_rows
- ✅ Statistyki pokazują poprawne liczby

---

### Test 4: Równoczesne przetwarzanie

**Timing:**
- User A: Rozpoczyna przetwarzanie w momencie T
- User B: Rozpoczyna przetwarzanie w momencie T+5s (5 sekund później)

**User A:**
1. Upload pliku A (50 wierszy)
2. Obserwuj progress bar

**User B (po 5 sekundach):**
1. Upload pliku B (30 wierszy)
2. Obserwuj progress bar

**Weryfikacja:**
- ✅ User A widzi ciągły postęp 0% → 100% (nie resetuje się)
- ✅ User B widzi własny postęp 0% → 100%
- ✅ Progress bary są niezależne
- ✅ Oba przetwarzania kończą się sukcesem

---

### Test 5: Odporność na zamknięcie przeglądarki

**User A:**
1. Upload pliku Excel
2. Zanotuj Session ID
3. Zamknij przeglądarkę gdy progress = 50%
4. Otwórz ponownie `http://localhost:5000`
5. Sprawdź console → Application → Cookies → session

**Weryfikacja:**
- ✅ Cookie z session_id jest zachowane
- ✅ Przetwarzanie kontynuowane w tle
- ✅ Po odświeżeniu strony użytkownik widzi swój postęp

---

### Test 6: Automatyczne czyszczenie starych sesji

**Symulacja wygaśnięcia:**
1. Otwórz `http://localhost:5000/admin/sessions`
2. Zanotuj liczbę aktywnych sesji
3. W kodzie `session_manager.py` tymczasowo zmień `max_age_hours` na 0.001 (kilka sekund)
4. Poczekaj 10 sekund
5. Wywołaj: `http://localhost:5000/admin/cleanup_sessions`

**Weryfikacja:**
- ✅ Stare sesje są usuwane
- ✅ Response pokazuje liczbę usuniętych sesji
- ✅ `/admin/sessions` pokazuje zmniejszoną liczbę sesji

---

## 🐛 Typowe problemy i rozwiązania

### Problem: "ModuleNotFoundError: No module named 'APScheduler'"
**Rozwiązanie:**
```bash
pip install APScheduler>=3.10.4
```

### Problem: "KeyError: 'session_id'"
**Rozwiązanie:**
- Wyczyść cookies przeglądarki
- Użyj trybu Incognito
- Zrestartuj aplikację

### Problem: Użytkownicy widzą nawzajem swoje postępy
**Diagnoza:**
- Sprawdź czy session_id są różne w `/admin/sessions`
- Sprawdź czy cookies są unikalne (F12 → Application → Cookies)

---

## 📊 Kryteria sukcesu

Test uznaje się za zaliczony gdy:

- [x] Dwóch użytkowników może równocześnie uploadować pliki
- [x] Każdy użytkownik widzi tylko swój postęp
- [x] Każdy użytkownik pobiera tylko swoje wyniki
- [x] Session ID są unikalne
- [x] Dane nie mieszają się między użytkownikami
- [x] Aplikacja nie crashuje przy równoczesnym użyciu
- [x] Scheduler czyszczenia działa poprawnie

---

## 🔍 Logi do weryfikacji

**W konsoli aplikacji powinny pojawić się logi:**

```
[INFO] Utworzono nową sesję użytkownika: abc12345...
[INFO] [abc12345] Rozpoczynam przetwarzanie: fuel=0.4, driver=210, matrix=klient
[INFO] [abc12345] Przetwarzanie zakończone pomyślnie
[INFO] Utworzono nową sesję użytkownika: xyz67890...
[INFO] [xyz67890] Rozpoczynam przetwarzanie: fuel=0.5, driver=250, matrix=targi
[INFO] [xyz67890] Przetwarzanie zakończone pomyślnie
```

Każda sesja powinna być wyraźnie oznaczona prefixem `[session_id]`.

---

## 📝 Raport z testów

Po wykonaniu testów wypełnij:

| Test | Status | Uwagi |
|------|--------|-------|
| Test 1: Podstawowy dwóch użytkowników | ☐ PASS ☐ FAIL | |
| Test 2: Pobieranie wyników | ☐ PASS ☐ FAIL | |
| Test 3: Monitoring sesji | ☐ PASS ☐ FAIL | |
| Test 4: Równoczesne przetwarzanie | ☐ PASS ☐ FAIL | |
| Test 5: Odporność na zamknięcie | ☐ PASS ☐ FAIL | |
| Test 6: Automatyczne czyszczenie | ☐ PASS ☐ FAIL | |

---

**Data testu:** _________________  
**Tester:** _________________  
**Wersja aplikacji:** 2.0 (Multi-user support)

