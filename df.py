import pandas as pd

# Załaduj plik Excel
historical_rates_df = pd.read_excel("historical_rates.xlsx")
historical_rates_gielda_df = pd.read_excel("historical_rates_gielda.xlsx")

# Wydrukuj pełną tabelę, aby sprawdzić, czy dane zostały poprawnie wczytane
print("Dane z historical_rates:")
print(historical_rates_df.head(50).to_string())  # Wydrukuj całą tabelę

print("Dane z historical_rates_gielda:")
print(historical_rates_gielda_df.head(50).to_string())  # Wydrukuj całą tabelę
