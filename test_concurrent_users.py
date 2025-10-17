"""
Prosty skrypt do testowania aplikacji z wieloma użytkownikami jednocześnie.

Uruchom aplikację, potem uruchom ten skrypt:
    python test_concurrent_users.py

Ten skrypt symuluje 3 użytkowników uploadujących pliki jednocześnie.
"""

import requests
import threading
import time
from pathlib import Path


BASE_URL = "http://localhost:5000"
TEST_FILE = "Szablon_przetargi — kopia.xlsx"  # Zmień na swój plik testowy


def simulate_user(user_id: int, test_file: Path):
    """Symuluje pojedynczego użytkownika"""
    print(f"👤 User {user_id}: START")
    
    try:
        # Utworzenie nowej sesji (symulacja przeglądarki)
        session = requests.Session()
        
        # Upload pliku
        with open(test_file, 'rb') as f:
            files = {'file': f}
            data = {
                'fuel_cost': '0.40',
                'driver_cost': '210',
                'matrix_type': 'klient'
            }
            
            print(f"👤 User {user_id}: Wysyłam plik...")
            response = session.post(f"{BASE_URL}/", files=files, data=data)
            
            if response.status_code != 200:
                print(f"❌ User {user_id}: Błąd uploadu: {response.status_code}")
                return
        
        print(f"👤 User {user_id}: Plik wysłany, monitoruję postęp...")
        
        # Monitoruj postęp
        last_progress = -1
        while True:
            try:
                progress_response = session.get(f"{BASE_URL}/progress")
                if progress_response.status_code == 200:
                    data = progress_response.json()
                    progress = data.get('progress', 0)
                    
                    if progress != last_progress:
                        print(f"👤 User {user_id}: Progress {progress}%")
                        last_progress = progress
                    
                    # Sprawdź czy zakończono
                    if data.get('complete'):
                        if progress == 100:
                            print(f"✅ User {user_id}: SUKCES! Przetwarzanie zakończone.")
                        elif progress == -2:
                            print(f"⚠️ User {user_id}: Wymagana weryfikacja lokalizacji")
                        else:
                            print(f"❌ User {user_id}: Błąd przetwarzania")
                        break
                
                time.sleep(2)  # Sprawdzaj co 2 sekundy
                
            except Exception as e:
                print(f"❌ User {user_id}: Błąd podczas monitorowania: {e}")
                break
        
        print(f"👤 User {user_id}: KONIEC")
        
    except Exception as e:
        print(f"❌ User {user_id}: Błąd: {e}")


def main():
    """Uruchom test wieloużytkownikowy"""
    test_file = Path(TEST_FILE)
    
    if not test_file.exists():
        print(f"❌ Nie znaleziono pliku testowego: {TEST_FILE}")
        print(f"   Zmień nazwę pliku w test_concurrent_users.py")
        return
    
    print("="*80)
    print("🚀 TEST WIELOUŻYTKOWNIKOWY - START")
    print(f"   Plik testowy: {TEST_FILE}")
    print(f"   Liczba użytkowników: 3")
    print("="*80)
    print()
    
    # Uruchom 3 wątki symulujące użytkowników
    threads = []
    for i in range(1, 4):
        thread = threading.Thread(target=simulate_user, args=(i, test_file))
        threads.append(thread)
        thread.start()
        time.sleep(1)  # Odstęp między startem użytkowników
    
    # Poczekaj na zakończenie wszystkich wątków
    for thread in threads:
        thread.join()
    
    print()
    print("="*80)
    print("🎉 TEST WIELOUŻYTKOWNIKOWY - ZAKOŃCZONY")
    print("="*80)
    
    # Sprawdź statystyki sesji
    try:
        response = requests.get(f"{BASE_URL}/admin/sessions")
        if response.status_code == 200:
            print("\n📊 Statystyki sesji:")
            print(response.text[:500])  # Pierwsze 500 znaków
    except:
        pass


if __name__ == "__main__":
    main()

