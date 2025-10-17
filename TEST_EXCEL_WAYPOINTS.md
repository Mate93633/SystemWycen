# Testowanie Waypoints w Excel

## 🎯 Jak stworzyć testowy plik Excel

### Format 1: Bez miast (prosty)
```
| Kraj zaladunku | Kod zaladunku | Miasto zaladunku | Punkty_posrednie | Kraj rozladunku | Kod rozładunku | Miasto rozładunku |
|----------------|---------------|------------------|------------------|-----------------|----------------|-------------------|
| PL             | 00-001        | Warszawa         | CZ:11000;AT:1010 | DE              | 10115          | Berlin            |
| DE             | 10115         | Berlin           |                  | FR              | 75001          | Paris             |
```

### Format 2: Z miastami
```
| Kraj zaladunku | Kod zaladunku | Miasto zaladunku | Punkty_posrednie                | Kraj rozladunku | Kod rozładunku | Miasto rozładunku |
|----------------|---------------|------------------|---------------------------------|-----------------|----------------|-------------------|
| PL             | 02-001        | Warszawa         | CZ:11000:Praha;AT:1010:Wien     | DE              | 10115          | Berlin            |
```

### Format 3: Mix (niektóre z waypoints, niektóre bez)
```
| Kraj zaladunku | Kod zaladunku | Punkty_posrednie | Kraj rozladunku | Kod rozładunku |
|----------------|---------------|------------------|-----------------|----------------|
| PL             | 00-001        | CZ:11000;AT:1010 | DE              | 10115          |
| FR             | 75001         |                  | IT              | 20100          |
| PL             | 02-001        | SK:81000         | HU              | 1011           |
```

## 📋 Kroki testowania

1. Otwórz Excel
2. Stwórz nowy arkusz
3. Wprowadź kolumny zgodnie z powyższym formatem
4. Zapisz jako `test_waypoints.xlsx`
5. Wgraj przez aplikację na `/`
6. Sprawdź logi i wyniki

## ✅ Czego oczekiwać

### Dla wiersza z waypoints:
- Logger: `"Wiersz X: Wykryto Y punktów pośrednich"`
- Geokodowanie wszystkich punktów
- Wywołanie PTV API z multi-waypoint routing
- Dystans większy niż trasa bezpośrednia

### Dla wiersza bez waypoints:
- Brak logów o waypoints
- Standardowy flow (backward compatibility)
- get_route_distance() zamiast calculate_multi_waypoint_route()

## 🐛 Debug

Jeśli coś nie działa:

1. Sprawdź `app.log`:
   ```
   grep -i "waypoint" app.log
   grep -i "Wykryto" app.log
   ```

2. Sprawdź console output:
   ```
   Sparsowano waypoint: CZ 11000
   Sparsowano waypoint: AT 1010
   ```

3. Sprawdź PTV API calls:
   ```
   grep "waypoints" ptv_timing.log
   ```

## 📝 Przykładowe trasy do testów

### Test 1: PL → CZ → AT → DE (Europa Środkowa)
- Start: PL 00-001 (Warszawa)
- Waypoint 1: CZ 11000 (Praha)
- Waypoint 2: AT 1010 (Wien)
- End: DE 10115 (Berlin)
- **Oczekiwany dystans**: ~1200-1400 km

### Test 2: FR → CH → IT (Europa Zachodnia + Alpy)
- Start: FR 75001 (Paris)
- Waypoint 1: CH 8000 (Zürich)
- End: IT 20100 (Milano)
- **Oczekiwane**: Wysokie opłaty drogowe (CH, IT)

### Test 3: PL → DE (bez waypoints - backward compatibility)
- Start: PL 02-001 (Warszawa)
- End: DE 20000 (Hamburg)
- **Oczekiwane**: Standardowy routing bez logów waypoints

---

**Data:** 17 października 2025  
**Feature:** Waypoints dla Excel Upload  
**Branch:** feature/waypoints-complete

