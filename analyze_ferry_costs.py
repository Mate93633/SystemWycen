import pandas as pd
import re
from collections import defaultdict

# Wczytaj dane z CSV
df = pd.read_csv(r'c:\Users\Mateusz Bartosik\Downloads\promy.csv', sep=';', encoding='utf-8')

# Wyczyść dane
df.columns = ['ferry_route', 'cost', 'currency']
df['cost'] = pd.to_numeric(df['cost'], errors='coerce')
df = df[df['currency'] == 'EUR']  # Tylko EUR
df = df[df['cost'] > 0]  # Usuń błędne dane (0, ujemne)
df = df[df['cost'] < 5000]  # Usuń outliers

# Normalizuj nazwy promów
def normalize_ferry_name(name):
    """Normalizuje nazwy promów do standardowego formatu"""
    name = str(name).upper().strip()
    
    # Mapowanie znanych skrótów i wariantów
    replacements = {
        'ROST-TRELL': 'ROSTOCK-TRELLEBORG',
        'TRELL-ROST': 'TRELLEBORG-ROSTOCK',
        'ŚWI-YST': 'SWINOUJSCIE-YSTAT',
        'YST-ŚWI': 'YSTAT-SWINOUJSCIE',
        'ŚWI-MAL': 'SWINOUJSCIE-MALMO',
        'MAL-ŚWI': 'MALMO-SWINOUJSCIE',
        'ŚWI-TRE': 'SWINOUJSCIE-TRELLEBORG',
        'TRE-ŚWI': 'TRELLEBORG-SWINOUJSCIE',
        'DUN-ROS': 'DUNKERQUE-ROSSLARE',
        'ROS-DUN': 'ROSSLARE-DUNKERQUE',
        'DOV-DUN': 'DOVER-DUNKERQUE',
        'DUBL-HOLY': 'DUBLIN-HOLYHEAD',
        'DUHO': 'DUBLIN-HOLYHEAD',
        'HODU': 'HOLYHEAD-DUBLIN',
        'BECN': 'BELFAST-CAIRNRYAN',
        'ROTG': 'ROTTERDAM-GRIMSBY',
        'HKIM': 'HOEK-KILLINGHOLME',
        'IMHK': 'IMMINGHAM-HOEK',
        'KARLSKRONA-GDYNIA': 'KARL-GDYN',
        'IMMI-HOEK': 'IMMINGHAM-HOEK',
        'CHER-ROSS': 'CHERBOURG-ROSSLARE',
        'ROSS-CHER': 'ROSSLARE-CHERBOURG',
        'RŘDBY': 'RODBY',
        'HELSINGŘR': 'HELSINGOR',
        'HELSINGI': 'HELSINKI',
        'YGOPUMENITSA': 'IGOUMENITSA',
        'IGOPUMENITSA': 'IGOUMENITSA',
        'KRISTIANSAND-HIRTSHALS': 'KRISTIANSAND-HIRTSHALS',
        'HIRTSHALS-KRISTIANSAND': 'HIRTSHALS-KRISTIANSAND',
        'BELF-CAIR': 'BELFAST-CAIRNRYAN',
        'CAIR-BELF': 'CAIRNRYAN-BELFAST',
        'ROST-TRELL': 'ROSTOCK-TRELLEBORG',
        'ROSSTOCK': 'ROSTOCK',
        'TRAVEMUNDE': 'TRAVEMUNDE',
        'ŚWINOUJŚCIE': 'SWINOUJSCIE',
        'MUUGA – VUOSAARI': 'MUUGA-VUOSAARI',
        'VIL-MES-VIL': 'VILNIUS-MESSINA-VILNIUS',
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    # Wyczyść białe znaki i normalizuj
    name = re.sub(r'\s+', '-', name)
    name = name.replace('--', '-')
    
    return name

df['normalized_ferry'] = df['ferry_route'].apply(normalize_ferry_name)

# Grupuj i oblicz statystyki
ferry_stats = df.groupby('normalized_ferry').agg({
    'cost': ['count', 'mean', 'median', 'min', 'max', 'std']
}).round(2)

ferry_stats.columns = ['Count', 'Mean', 'Median', 'Min', 'Max', 'StdDev']
ferry_stats = ferry_stats.sort_values('Count', ascending=False)

# Zapisz do pliku
output_file = r'c:\Users\Mateusz Bartosik\Projekty python\SystemWycen\ferry_costs_analysis.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("="*100 + "\n")
    f.write("ANALIZA KOSZTÓW PROMÓW - TWOJE FAKTYCZNE KOSZTY\n")
    f.write("="*100 + "\n\n")
    
    for ferry_name, row in ferry_stats.iterrows():
        if row['Count'] >= 3:  # Pokaż tylko promy z min. 3 przejazdami
            f.write(f"\n{ferry_name}\n")
            f.write(f"  Liczba przejazdów: {int(row['Count'])}\n")
            f.write(f"  Średni koszt: {row['Mean']:.2f} EUR\n")
            f.write(f"  Mediana: {row['Median']:.2f} EUR\n")
            f.write(f"  Min: {row['Min']:.2f} EUR\n")
            f.write(f"  Max: {row['Max']:.2f} EUR\n")
            f.write(f"  Odchylenie: {row['StdDev']:.2f} EUR\n")
            f.write("-"*100 + "\n")

print(f"✅ Analiza zapisana do: {output_file}")
print(f"\nTop 20 najczęściej używanych promów:")
print(ferry_stats.head(20))
