import sys
import os

# Dodaj główny katalog do ścieżki Python
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Importuj aplikację Flask
from appGPT import app

# Vercel wymaga funkcji o nazwie 'app' lub handler
# Eksportuj aplikację Flask jako domyślną funkcję
if __name__ == "__main__":
    app.run()
