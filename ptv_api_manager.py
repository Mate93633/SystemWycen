from queue import Queue
from threading import Thread, Lock
import time
import math
from datetime import datetime, timedelta
import requests
import logging
import traceback

# Konfiguracja loggera - zmiana poziomu na DEBUG aby pokazać wszystkie logi
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DEFAULT_ROUTING_MODE = "FAST"

# UK HGV Road User Levy - dzienna winieta dla ciężarówek >38t, Euro VI (w EUR)
# Źródło: UK Government HGV Levy rates 2024/2025 - £9.69/dzień ≈ 11€
UK_HGV_LEVY_DAILY_EUR = 11.0

# Koszty promów (w EUR) - na podstawie faktycznych danych z promy.csv (2024/2025)
# Ceny dla ciężarówek 40t - zaktualizowane na podstawie historii przejazdów
FERRY_COSTS = {
    # Kanał La Manche
    'Dover-Calais': 190,
    'Calais-Dover': 190,
    'Dover-Dunkirk': 190,
    'Dunkirk-Dover': 190,
    'Dover-Dunkerque': 190,
    'Dunkerque-Dover': 190,
    'Folkestone-Calais (Eurotunnel)': 250,
    'Calais-Folkestone (Eurotunnel)': 250,
    'Portsmouth-Le Havre': 350,
    'Le Havre-Portsmouth': 350,
    'Newhaven-Dieppe': 280,
    'Dieppe-Newhaven': 280,
    'Portsmouth-Cherbourg': 320,
    'Cherbourg-Portsmouth': 320,
    
    # Morze Północne
    'Hull-Rotterdam': 400,
    'Rotterdam-Hull': 400,
    'Newcastle-Amsterdam': 450,
    'Amsterdam-Newcastle': 450,
    'Harwich-Hook of Holland': 280,
    'Hook of Holland-Harwich': 280,
    'Immingham-Hoek': 700,
    'Hoek-Immingham': 700,
    
    # Morze Irlandzkie
    'Holyhead-Dublin': 380,
    'Dublin-Holyhead': 380,
    'Liverpool-Dublin': 300,
    'Dublin-Liverpool': 300,
    'Fishguard-Rosslare': 390,
    'Rosslare-Fishguard': 390,
    'Pembroke-Rosslare': 390,
    'Rosslare-Pembroke': 390,
    'Cairnryan-Larne': 200,
    'Larne-Cairnryan': 200,
    'Cairnryan-Belfast': 290,
    'Belfast-Cairnryan': 290,
    'Cherbourg-Dublin': 1150,
    'Dublin-Cherbourg': 1150,
    'Cherbourg-Rosslare': 1140,
    'Rosslare-Cherbourg': 1140,
    'Dunkerque-Rosslare': 1645,
    'Rosslare-Dunkerque': 1645,
    'Dunkirk-Rosslare': 1645,
    'Rosslare-Dunkirk': 1645,
    'Zeebrugge-Rosslare': 1320,
    'Rosslare-Zeebrugge': 1320,
    
    # Morze Bałtyckie
    'Tallinn-Helsinki': 380,
    'Helsinki-Tallinn': 380,
    'Tallinn-Helsingi': 380,  # Alternatywna nazwa z PTV API
    'Helsingi-Tallinn': 380,  # Alternatywna nazwa z PTV API
    'Stockholm-Turku': 620,
    'Turku-Stockholm': 550,
    'Kapellskar-Naantali': 600,
    'Naantali-Kapellskar': 600,
    'Gdansk-Nynashamn': 800,
    'Nynashamn-Gdansk': 800,
    'Karlskrona-Gdynia': 515,
    'Gdynia-Karlskrona': 515,
    'Swinoujscie-Ystad': 360,
    'Ystad-Swinoujscie': 360,
    'Swinoujscie-Malmo': 400,
    'Malmo-Swinoujscie': 400,
    'Swinoujscie-Trelleborg': 405,
    'Trelleborg-Swinoujscie': 405,
    'Rostock-Trelleborg': 310,
    'Trelleborg-Rostock': 340,
    'Travemunde-Trelleborg': 440,
    'Trelleborg-Travemunde': 440,
    'Puttgarden-Rodby': 260,
    'Rodby-Puttgarden': 240,
    'Rostock-Gedser': 280,
    'Gedser-Rostock': 200,
    'Helsingborg-Helsingor': 190,
    'Helsingor-Helsingborg': 190,
    'Kiel-Klaipeda': 1200,
    'Klaipeda-Kiel': 1200,
    'Muuga-Vuosaari': 345,
    'Vuosaari-Muuga': 345,
    
    # Morze Adriatyckie
    'Patras-Ancona': 1500,
    'Ancona-Patras': 1500,
    'Patras-Bari': 1200,
    'Bari-Patras': 1200,
    'Igoumenitsa-Ancona': 890,
    'Ancona-Igoumenitsa': 890,
    'Igoumenitsa-Bari': 760,
    'Bari-Igoumenitsa': 760,
    'Igoumenitsa-Brindisi': 710,
    'Brindisi-Igoumenitsa': 710,
    'Split-Ancona': 600,
    'Ancona-Split': 600,
    
    # Morze Północne (Norwegia)
    'Kristiansand-Hirtshals': 535,
    'Hirtshals-Kristiansand': 535,
    
    # Morze Śródziemne
    'Barcelona-Civitavecchia': 900,
    'Civitavecchia-Barcelona': 900,
    'Marseille-Tunis': 1100,
    'Tunis-Marseille': 1100,
    'Genoa-Barcelona': 850,
    'Barcelona-Genoa': 850,
    'Civitavecchia-Palermo': 700,
    'Palermo-Civitavecchia': 700,
    
    # Zatoka Biskajska
    'Portsmouth-Bilbao': 1000,
    'Bilbao-Portsmouth': 1000,
    'Plymouth-Santander': 900,
    'Santander-Plymouth': 900,
}

# Dystanse morskie promów (w km) - używane do odróżnienia dystansu "na kołach" od dystansu na promie
# Wartości są przybliżone na podstawie rzeczywistych tras morskich
FERRY_SEA_DISTANCES = {
    # Kanał La Manche
    'Dover-Calais': 42,
    'Calais-Dover': 42,
    'Dover-Dunkirk': 60,
    'Dunkirk-Dover': 60,
    'Dover-Dunkerque': 60,
    'Dunkerque-Dover': 60,
    'Folkestone-Calais (Eurotunnel)': 50,  # Pod kanałem, ale dla spójności
    'Calais-Folkestone (Eurotunnel)': 50,
    'Portsmouth-Le Havre': 160,
    'Le Havre-Portsmouth': 160,
    'Newhaven-Dieppe': 110,
    'Dieppe-Newhaven': 110,
    'Portsmouth-Cherbourg': 120,
    'Cherbourg-Portsmouth': 120,
    
    # Morze Północne
    'Hull-Rotterdam': 350,
    'Rotterdam-Hull': 350,
    'Newcastle-Amsterdam': 400,
    'Amsterdam-Newcastle': 400,
    'Harwich-Hook of Holland': 140,
    'Hook of Holland-Harwich': 140,
    'Immingham-Hoek': 320,
    'Hoek-Immingham': 320,
    
    # Morze Irlandzkie
    'Holyhead-Dublin': 110,
    'Dublin-Holyhead': 110,
    'Liverpool-Dublin': 180,
    'Dublin-Liverpool': 180,
    'Fishguard-Rosslare': 90,
    'Rosslare-Fishguard': 90,
    'Pembroke-Rosslare': 90,
    'Rosslare-Pembroke': 90,
    'Cairnryan-Larne': 50,
    'Larne-Cairnryan': 50,
    'Cairnryan-Belfast': 50,
    'Belfast-Cairnryan': 50,
    'Cherbourg-Dublin': 450,
    'Dublin-Cherbourg': 450,
    'Cherbourg-Rosslare': 320,
    'Rosslare-Cherbourg': 320,
    'Dunkerque-Rosslare': 950,
    'Rosslare-Dunkerque': 950,
    'Dunkirk-Rosslare': 950,
    'Rosslare-Dunkirk': 950,
    'Zeebrugge-Rosslare': 850,
    'Rosslare-Zeebrugge': 850,
    
    # Morze Bałtyckie
    'Tallinn-Helsinki': 85,
    'Helsinki-Tallinn': 85,
    'Tallinn-Helsingi': 85,  # Alternatywna nazwa z PTV API
    'Helsingi-Tallinn': 85,  # Alternatywna nazwa z PTV API
    'Stockholm-Turku': 300,
    'Turku-Stockholm': 300,
    'Kapellskar-Naantali': 280,
    'Naantali-Kapellskar': 280,
    'Gdansk-Nynashamn': 650,
    'Nynashamn-Gdansk': 650,
    'Karlskrona-Gdynia': 380,
    'Gdynia-Karlskrona': 380,
    'Swinoujscie-Ystad': 240,
    'Ystad-Swinoujscie': 240,
    'Swinoujscie-Malmo': 280,
    'Malmo-Swinoujscie': 280,
    'Swinoujscie-Trelleborg': 260,
    'Trelleborg-Swinoujscie': 260,
    'Rostock-Trelleborg': 180,
    'Trelleborg-Rostock': 180,
    'Travemunde-Trelleborg': 180,
    'Trelleborg-Travemunde': 180,
    'Puttgarden-Rodby': 19,
    'Rodby-Puttgarden': 19,
    'Rostock-Gedser': 65,
    'Gedser-Rostock': 65,
    'Helsingborg-Helsingor': 4,
    'Helsingor-Helsingborg': 4,
    'Kiel-Klaipeda': 1050,
    'Klaipeda-Kiel': 1050,
    'Muuga-Vuosaari': 90,
    'Vuosaari-Muuga': 90,
    'Kristiansand-Hirtshals': 150,
    'Hirtshals-Kristiansand': 150,
    
    # Morze Adriatyckie
    'Patras-Ancona': 980,
    'Ancona-Patras': 980,
    'Patras-Bari': 820,
    'Bari-Patras': 820,
    'Igoumenitsa-Ancona': 850,
    'Ancona-Igoumenitsa': 850,
    'Igoumenitsa-Bari': 650,
    'Bari-Igoumenitsa': 650,
    'Igoumenitsa-Brindisi': 580,
    'Brindisi-Igoumenitsa': 580,
    'Split-Ancona': 280,
    'Ancona-Split': 280,
    
    # Morze Śródziemne
    'Barcelona-Civitavecchia': 620,
    'Civitavecchia-Barcelona': 620,
    'Marseille-Tunis': 850,
    'Tunis-Marseille': 850,
    'Genoa-Barcelona': 550,
    'Barcelona-Genoa': 550,
    'Civitavecchia-Palermo': 450,
    'Palermo-Civitavecchia': 450,
    
    # Zatoka Biskajska
    'Portsmouth-Bilbao': 880,
    'Bilbao-Portsmouth': 880,
    'Plymouth-Santander': 650,
    'Santander-Plymouth': 650,
}



MANDATORY_FERRY_ROUTES = {

    # =========================================================================
    # BULGARIA
    # =========================================================================
    ('BG', 'SE'): {
        'name': 'Travemunde-Trelleborg',  # Via Germany
        'start': (53.9603, 10.8697),
        'end': (55.3667, 13.1500),
        'cost': 440.0,
        'duration_hours': 8,
        'operator': 'TT-Line'
    },
    ('SE', 'BG'): {
        'name': 'Trelleborg-Travemunde',
        'start': (55.3667, 13.1500),
        'end': (53.9603, 10.8697),
        'cost': 440.0,
        'duration_hours': 8,
        'operator': 'TT-Line'
    },
    
    # =========================================================================
    # DENMARK
    # =========================================================================
    ('DK', 'FI'): {
        'name': 'Kapellskar-Stockholm-Helsinki',  # Via Sweden
        'start': (59.7333, 19.0667),
        'end': (60.1699, 24.9384),
        'cost': 1000.0,  # Stockholm-Turku 620 + Tallinn-Helsinki 380
        'duration_hours': 26,
        'operator': 'Finnlines / Viking Line'
    },
    ('FI', 'DK'): {
        'name': 'Helsinki-Stockholm-Kapellskar',
        'start': (60.1699, 24.9384),
        'end': (59.7333, 19.0667),
        'cost': 920.0,  # Helsinki-Tallinn 370 + Turku-Stockholm 550
        'duration_hours': 26,
        'operator': 'Finnlines / Viking Line'
    },
    ('DK', 'PT'): {
        'name': 'Esbjerg-Harwich-Portsmouth',  # Via UK
        'start': (55.4667, 8.4500),
        'end': (50.8198, -1.0879),
        'cost': 410.0,
        'duration_hours': 20,
        'operator': 'DFDS'
    },
    ('PT', 'DK'): {
        'name': 'Portsmouth-Harwich-Esbjerg',
        'start': (50.8198, -1.0879),
        'end': (55.4667, 8.4500),
        'cost': 410.0,
        'duration_hours': 20,
        'operator': 'DFDS'
    },
    ('DK', 'ES'): {
        'name': 'Esbjerg-Newcastle',  # Via UK
        'start': (55.4667, 8.4500),
        'end': (55.0077, -1.4400),
        'cost': 410.0,
        'duration_hours': 18,
        'operator': 'DFDS'
    },
    ('ES', 'DK'): {
        'name': 'Newcastle-Esbjerg',
        'start': (55.0077, -1.4400),
        'end': (55.4667, 8.4500),
        'cost': 410.0,
        'duration_hours': 18,
        'operator': 'DFDS'
    },
    
    # =========================================================================
    # GERMANY ↔ SWEDEN
    # =========================================================================
    ('DE', 'SE'): {
        'name': 'Kiel-Gothenburg',
        'start': (54.3233, 10.1394),
        'end': (57.7089, 11.9746),
        'cost': 450.0,
        'duration_hours': 14,
        'operator': 'Stena Line'
    },
    ('SE', 'DE'): {
        'name': 'Gothenburg-Kiel',
        'start': (57.7089, 11.9746),
        'end': (54.3233, 10.1394),
        'cost': 450.0,
        'duration_hours': 14,
        'operator': 'Stena Line'
    },
    
    # =========================================================================
    # GREECE
    # =========================================================================
    ('GR', 'SE'): {
        'name': 'Igoumenitsa-Ancona',  # Via Italy
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('SE', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'DK'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('DK', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'IT'): {
        'name': 'Igoumenitsa-Bari',
        'start': (39.5030, 20.2660),
        'end': (41.1171, 16.8719),
        'cost': 760.0,
        'duration_hours': 11,
        'operator': 'Superfast Ferries'
    },
    ('IT', 'GR'): {
        'name': 'Bari-Igoumenitsa',
        'start': (41.1171, 16.8719),
        'end': (39.5030, 20.2660),
        'cost': 760.0,
        'duration_hours': 11,
        'operator': 'Superfast Ferries'
    },
    ('GR', 'ES'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('ES', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 1050.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'GB'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 1050.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GB', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 1050.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'AT'): {
        'name': 'Igoumenitsa-Bari',
        'start': (39.5030, 20.2660),
        'end': (41.1171, 16.8719),
        'cost': 1050.0,
        'duration_hours': 11,
        'operator': 'Superfast Ferries'
    },
    ('AT', 'GR'): {
        'name': 'Bari-Igoumenitsa',
        'start': (41.1171, 16.8719),
        'end': (39.5030, 20.2660),
        'cost': 1050.0,
        'duration_hours': 11,
        'operator': 'Superfast Ferries'
    },
    ('GR', 'BE'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('BE', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'FR'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('FR', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'DE'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('DE', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'NL'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('NL', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'PT'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('PT', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 890.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('GR', 'CH'): {
        'name': 'Igoumenitsa-Ancona',
        'start': (39.5030, 20.2660),
        'end': (43.6158, 13.5184),
        'cost': 1050.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    ('CH', 'GR'): {
        'name': 'Ancona-Igoumenitsa',
        'start': (43.6158, 13.5184),
        'end': (39.5030, 20.2660),
        'cost': 1050.0,
        'duration_hours': 15,
        'operator': 'Superfast Ferries / ANEK Lines'
    },
    
    # =========================================================================
    # ITALY
    # =========================================================================
    ('IT', 'FI'): {
        'name': 'Rostock-Helsinki',  # Via Germany
        'start': (54.0833, 12.1333),
        'end': (60.1699, 24.9384),
        'cost': 450.0,
        'duration_hours': 24,
        'operator': 'Finnlines'
    },
    ('FI', 'IT'): {
        'name': 'Helsinki-Rostock',
        'start': (60.1699, 24.9384),
        'end': (54.0833, 12.1333),
        'cost': 450.0,
        'duration_hours': 24,
        'operator': 'Finnlines'
    },
    ('IT', 'SE'): {
        'name': 'Rostock-Trelleborg',  # Via Germany
        'start': (54.0833, 12.1333),
        'end': (55.3667, 13.1500),
        'cost': 410.0,
        'duration_hours': 6,
        'operator': 'Stena Line / TT-Line'
    },
    ('SE', 'IT'): {
        'name': 'Trelleborg-Rostock',
        'start': (55.3667, 13.1500),
        'end': (54.0833, 12.1333),
        'cost': 450.0,
        'duration_hours': 6,
        'operator': 'Stena Line / TT-Line'
    },
    
    # =========================================================================
    # NETHERLANDS
    # =========================================================================
    ('NL', 'DK'): {
        'name': 'Amsterdam-Newcastle-Kristiansand',  # Via UK/Norway
        'start': (52.4092, 4.9389),
        'end': (58.1467, 7.9956),
        'cost': 300.0,
        'duration_hours': 26,
        'operator': 'DFDS'
    },
    ('DK', 'NL'): {
        'name': 'Kristiansand-Newcastle-Amsterdam',
        'start': (58.1467, 7.9956),
        'end': (52.4092, 4.9389),
        'cost': 300.0,
        'duration_hours': 26,
        'operator': 'DFDS'
    },
    ('NL', 'FI'): {
        'name': 'Amsterdam-Newcastle-Helsinki',  # Via UK
        'start': (52.4092, 4.9389),
        'end': (60.1699, 24.9384),
        'cost': 1100.0,
        'duration_hours': 48,
        'operator': 'DFDS / Finnlines'
    },
    ('FI', 'NL'): {
        'name': 'Helsinki-Newcastle-Amsterdam',
        'start': (60.1699, 24.9384),
        'end': (52.4092, 4.9389),
        'cost': 1100.0,
        'duration_hours': 48,
        'operator': 'Finnlines / DFDS'
    },
    ('NL', 'SE'): {
        'name': 'Amsterdam-Gothenburg',  # Direct or via Denmark
        'start': (52.4092, 4.9389),
        'end': (57.7089, 11.9746),
        'cost': 410.0,
        'duration_hours': 24,
        'operator': 'DFDS'
    },
    ('SE', 'NL'): {
        'name': 'Gothenburg-Amsterdam',
        'start': (57.7089, 11.9746),
        'end': (52.4092, 4.9389),
        'cost': 450.0,
        'duration_hours': 24,
        'operator': 'DFDS'
    },
    
    # =========================================================================
    # POLAND
    # =========================================================================
    ('PL', 'DK'): {
        'name': 'Swinoujscie-Ystad-Copenhagen',  # Via Sweden
        'start': (53.9100, 14.2478),
        'end': (55.6761, 12.5683),
        'cost': 600.0,
        'duration_hours': 10,
        'operator': 'Unity Line'
    },
    ('DK', 'PL'): {
        'name': 'Copenhagen-Ystad-Swinoujscie',
        'start': (55.6761, 12.5683),
        'end': (53.9100, 14.2478),
        'cost': 600.0,
        'duration_hours': 10,
        'operator': 'Unity Line'
    },
    ('PL', 'FI'): {
        'name': 'Gdansk-Nynashamn-Helsinki',  # Via Sweden
        'start': (54.3520, 18.6466),
        'end': (60.1699, 24.9384),
        'cost': 450.0,
        'duration_hours': 28,
        'operator': 'Polferries / Viking Line'
    },
    ('FI', 'PL'): {
        'name': 'Helsinki-Nynashamn-Gdansk',
        'start': (60.1699, 24.9384),
        'end': (54.3520, 18.6466),
        'cost': 450.0,
        'duration_hours': 28,
        'operator': 'Viking Line / Polferries'
    },
    ('PL', 'SE'): {
        'name': 'Swinoujscie-Ystad',
        'start': (53.9100, 14.2478),
        'end': (55.4295, 13.8200),
        'cost': 450.0,
        'duration_hours': 7,
        'operator': 'Unity Line / Polferries'
    },
    ('SE', 'PL'): {
        'name': 'Ystad-Swinoujscie',
        'start': (55.4295, 13.8200),
        'end': (53.9100, 14.2478),
        'cost': 400.0,
        'duration_hours': 7,
        'operator': 'Unity Line / Polferries'
    },
    
    # =========================================================================
    # PORTUGAL
    # =========================================================================
    ('PT', 'DK'): {
        'name': 'Leixoes-Portsmouth-Harwich',  # Via UK
        'start': (41.1760, -8.7040),
        'end': (51.9460, 1.2843),
        'cost': 350.0,
        'duration_hours': 36,
        'operator': 'Grimaldi'
    },
    ('PT', 'SE'): {
        'name': 'Leixoes-Santander-Portsmouth',  # Via Spain/UK
        'start': (41.1760, -8.7040),
        'end': (50.8198, -1.0879),
        'cost': 450.0,
        'duration_hours': 40,
        'operator': 'Grimaldi / Brittany Ferries'
    },
    ('SE', 'PT'): {
        'name': 'Portsmouth-Santander-Leixoes',
        'start': (50.8198, -1.0879),
        'end': (41.1760, -8.7040),
        'cost': 450.0,
        'duration_hours': 40,
        'operator': 'Brittany Ferries / Grimaldi'
    },
    
    # =========================================================================
    # SPAIN
    # =========================================================================
    ('ES', 'SE'): {
        'name': 'Santander-Portsmouth',
        'start': (43.4623, -3.8099),
        'end': (50.8198, -1.0879),
        'cost': 450.0,
        'duration_hours': 24,
        'operator': 'Brittany Ferries'
    },
    ('SE', 'ES'): {
        'name': 'Portsmouth-Santander',
        'start': (50.8198, -1.0879),
        'end': (43.4623, -3.8099),
        'cost': 450.0,
        'duration_hours': 24,
        'operator': 'Brittany Ferries'
    },
    ('ES', 'DK'): {
        'name': 'Santander-Portsmouth',  # Via UK
        'start': (43.4623, -3.8099),
        'end': (50.8198, -1.0879),
        'cost': 300.0,
        'duration_hours': 24,
        'operator': 'Brittany Ferries'
    },
    ('ES', 'FI'): {
        'name': 'Barcelona-Civitavecchia',  # Via Italy
        'start': (41.3851, 2.1734),
        'end': (42.0931, 11.7865),
        'cost': 1060.0,
        'duration_hours': 20,
        'operator': 'Grimaldi Lines'
    },
    ('FI', 'ES'): {
        'name': 'Civitavecchia-Barcelona',
        'start': (42.0931, 11.7865),
        'end': (41.3851, 2.1734),
        'cost': 1060.0,
        'duration_hours': 20,
        'operator': 'Grimaldi Lines'
    },
    
    # =========================================================================
    # UK
    # =========================================================================
    ('GB', 'FI'): {
        'name': 'Harwich-Hook of Holland-Travemunde-Helsinki',
        'start': (51.9460, 1.2843),
        'end': (60.1699, 24.9384),
        'cost': 1250.0,
        'duration_hours': 48,
        'operator': 'Stena Line / Finnlines'
    },
    ('FI', 'GB'): {
        'name': 'Helsinki-Travemunde-Hook of Holland-Harwich',
        'start': (60.1699, 24.9384),
        'end': (51.9460, 1.2843),
        'cost': 1250.0,
        'duration_hours': 48,
        'operator': 'Finnlines / Stena Line'
    },
    ('GB', 'IT'): {
        'name': 'Dover-Calais',  # Via France (land connection)
        'start': (51.1279, 1.3134),
        'end': (50.9513, 1.8587),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('IT', 'GB'): {
        'name': 'Calais-Dover',
        'start': (50.9513, 1.8587),
        'end': (51.1279, 1.3134),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('GB', 'NL'): {
        'name': 'Dover-Calais',  # Via France (land connection)
        'start': (51.1279, 1.3134),
        'end': (50.9513, 1.8587),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('NL', 'GB'): {
        'name': 'Calais-Dover',
        'start': (50.9513, 1.8587),
        'end': (51.1279, 1.3134),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('GB', 'PL'): {
        'name': 'Hull-Rotterdam-Swinoujscie',  # Via Netherlands
        'start': (53.7444, -0.3340),
        'end': (53.9100, 14.2478),
        'cost': 190.0,
        'duration_hours': 30,
        'operator': 'P&O Ferries / Unity Line'
    },
    ('PL', 'GB'): {
        'name': 'Swinoujscie-Rotterdam-Hull',
        'start': (53.9100, 14.2478),
        'end': (53.7444, -0.3340),
        'cost': 190.0,
        'duration_hours': 30,
        'operator': 'Unity Line / P&O Ferries'
    },
    ('GB', 'ES'): {
        'name': 'Portsmouth-Santander',
        'start': (50.8198, -1.0879),
        'end': (43.4623, -3.8099),
        'cost': 190.0,
        'duration_hours': 24,
        'operator': 'Brittany Ferries'
    },
    ('ES', 'GB'): {
        'name': 'Santander-Portsmouth',
        'start': (43.4623, -3.8099),
        'end': (50.8198, -1.0879),
        'cost': 190.0,
        'duration_hours': 24,
        'operator': 'Brittany Ferries'
    },
    ('GB', 'SE'): {
        'name': 'Newcastle-Amsterdam-Gothenburg',  # Via Netherlands/Denmark
        'start': (55.0077, -1.4400),
        'end': (57.7089, 11.9746),
        'cost': 410.0,
        'duration_hours': 40,
        'operator': 'DFDS'
    },
    ('SE', 'GB'): {
        'name': 'Gothenburg-Amsterdam-Newcastle',
        'start': (57.7089, 11.9746),
        'end': (55.0077, -1.4400),
        'cost': 410.0,
        'duration_hours': 40,
        'operator': 'DFDS'
    },
    ('GB', 'CH'): {
        'name': 'Dover-Calais',  # Via France (land)
        'start': (51.1279, 1.3134),
        'end': (50.9513, 1.8587),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('CH', 'GB'): {
        'name': 'Calais-Dover',
        'start': (50.9513, 1.8587),
        'end': (51.1279, 1.3134),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('GB', 'DK'): {
        'name': 'Harwich-Esbjerg',
        'start': (51.9460, 1.2843),
        'end': (55.4667, 8.4500),
        'cost': 600.0,
        'duration_hours': 18,
        'operator': 'DFDS'
    },
    ('DK', 'GB'): {
        'name': 'Esbjerg-Harwich',
        'start': (55.4667, 8.4500),
        'end': (51.9460, 1.2843),
        'cost': 600.0,
        'duration_hours': 18,
        'operator': 'DFDS'
    },
    ('GB', 'FR'): {
        'name': 'Dover-Calais',
        'start': (51.1279, 1.3134),
        'end': (50.9513, 1.8587),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('FR', 'GB'): {
        'name': 'Calais-Dover',
        'start': (50.9513, 1.8587),
        'end': (51.1279, 1.3134),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('GB', 'DE'): {
        'name': 'Dover-Calais',
        'start': (51.1279, 1.3134),
        'end': (50.9513, 1.8587),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    ('DE', 'GB'): {
        'name': 'Calais-Dover',
        'start': (50.9513, 1.8587),
        'end': (51.1279, 1.3134),
        'cost': 190.0,
        'duration_hours': 1.5,
        'operator': 'P&O Ferries / DFDS'
    },
    
    # =========================================================================
    # FINLANDIA ↔ ESTONIA (brak połączenia lądowego - most obowiązkowy)
    # =========================================================================
    ('FI', 'EE'): {
        'name': 'Helsinki-Tallinn',
        'start': (60.1699, 24.9384),
        'end': (59.4370, 24.7536),
        'cost': 380.0,
        'duration_hours': 2.5,
        'operator': 'Tallink Silja / Viking Line / Eckerö Line'
    },
    ('EE', 'FI'): {
        'name': 'Tallinn-Helsinki',
        'start': (59.4370, 24.7536),
        'end': (60.1699, 24.9384),
        'cost': 380.0,
        'duration_hours': 2.5,
        'operator': 'Tallink Silja / Viking Line / Eckerö Line'
    },
}


def is_ferry_mandatory(country_from: str, country_to: str) -> bool:
    """
    Sprawdza czy dla danej pary krajów prom jest obowiązkowy.
    
    Args:
        country_from: Kod kraju początkowego (np. 'GR', 'IT', 'GB')
        country_to: Kod kraju docelowego
        
    Returns:
        True jeśli prom jest obowiązkowy dla tej pary krajów
    """
    if not country_from or not country_to:
        return False
    
    country_from = country_from.upper()
    country_to = country_to.upper()
    
    return (country_from, country_to) in MANDATORY_FERRY_ROUTES

def get_best_ferry_for_countries(country_from: str, country_to: str):
    """
    Zwraca zdefiniowany prom dla pary krajów.
    
    Args:
        country_from: Kod kraju początkowego
        country_to: Kod kraju docelowego
        
    Returns:
        Słownik z informacjami o promie lub None
    """
    if not country_from or not country_to:
        return None
    
    country_from = country_from.upper()
    country_to = country_to.upper()
    
    return MANDATORY_FERRY_ROUTES.get((country_from, country_to))


class PTVRequestQueue:
    def __init__(self, api_key, max_requests_per_second=10):
        self.queue = Queue()
        self.results = {}
        self.lock = Lock()
        self.max_requests_per_second = max_requests_per_second
        self.last_request_time = 0
        self.api_key = api_key
        self._start_worker()

    def _start_worker(self):
        def worker():
            while True:
                request_id, func, args, kwargs = self.queue.get()
                self._rate_limit()
                try:
                    result = func(*args, **kwargs)
                    with self.lock:
                        self.results[request_id] = {'status': 'success', 'data': result}
                except Exception as e:
                    with self.lock:
                        self.results[request_id] = {'status': 'error', 'error': str(e)}
                self.queue.task_done()

        Thread(target=worker, daemon=True).start()

    def _rate_limit(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < 1.0 / self.max_requests_per_second:
            time.sleep(1.0 / self.max_requests_per_second - time_since_last_request)
        self.last_request_time = time.time()

    def add_request(self, request_id, func, *args, **kwargs):
        self.queue.put((request_id, func, args, kwargs))

    def get_result(self, request_id):
        with self.lock:
            return self.results.get(request_id)

    def clear_old_results(self, max_age=3600):  # Czyszczenie wyników starszych niż godzina
        with self.lock:
            current_time = time.time()
            self.results = {k: v for k, v in self.results.items() 
                          if hasattr(v, '_creation_time') and 
                          current_time - v._creation_time < max_age}

class RouteCacheManager:
    def __init__(self, cache_duration=timedelta(days=7)):
        self.cache = {}
        self.cache_duration = cache_duration
        self.stats = {'hits': 0, 'misses': 0}
        self.lock = Lock()

    def _generate_key(self, coord_from, coord_to, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia=True):
        return (
            tuple(coord_from),
            tuple(coord_to),
            avoid_switzerland,
            avoid_eurotunnel,
            avoid_serbia,
            routing_mode,
        )

    def get(self, coord_from, coord_to, avoid_switzerland=False, avoid_eurotunnel=False, routing_mode=DEFAULT_ROUTING_MODE, avoid_serbia=True):
        with self.lock:
            key = self._generate_key(coord_from, coord_to, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia)
            if key in self.cache:
                cache_entry = self.cache[key]
                if datetime.now() - cache_entry['timestamp'] < self.cache_duration:
                    self.stats['hits'] += 1
                    return cache_entry['data']
                else:
                    del self.cache[key]
            self.stats['misses'] += 1
            return None

    def set(self, coord_from, coord_to, data, avoid_switzerland=False, avoid_eurotunnel=False, routing_mode=DEFAULT_ROUTING_MODE, avoid_serbia=True):
        with self.lock:
            key = self._generate_key(coord_from, coord_to, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia)
            self.cache[key] = {
                'data': data,
                'timestamp': datetime.now()
            }

    def get_stats(self):
        with self.lock:
            total = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
            return {
                'hit_rate': f"{hit_rate:.2f}%",
                'total_requests': total,
                'cache_size': len(self.cache)
            }
    
    def _generate_waypoints_key(self, waypoints, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia=True):
        """
        Generuje klucz cache dla trasy z waypoints.
        WAŻNE: Kolejność waypoints ma znaczenie!
        """
        waypoints_tuple = tuple(tuple(wp) for wp in waypoints)
        return (waypoints_tuple, avoid_switzerland, avoid_eurotunnel, avoid_serbia, routing_mode)
    
    def get_waypoints_route(self, waypoints, avoid_switzerland=False, avoid_eurotunnel=False, routing_mode=DEFAULT_ROUTING_MODE, avoid_serbia=True):
        """Pobiera trasę z cache dla waypoints"""
        with self.lock:
            key = self._generate_waypoints_key(waypoints, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia)
            
            if key in self.cache:
                cache_entry = self.cache[key]
                
                # Sprawdź ważność
                if datetime.now() - cache_entry['timestamp'] < self.cache_duration:
                    self.stats['hits'] += 1
                    return cache_entry['data']
                else:
                    # Wygasł - usuń
                    del self.cache[key]
            
            self.stats['misses'] += 1
            return None
    
    def set_waypoints_route(self, waypoints, data, avoid_switzerland=False, avoid_eurotunnel=False, routing_mode=DEFAULT_ROUTING_MODE, avoid_serbia=True):
        """Zapisuje trasę do cache dla waypoints"""
        with self.lock:
            key = self._generate_waypoints_key(waypoints, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia)
            self.cache[key] = {
                'data': data,
                'timestamp': datetime.now()
            }
            logger.debug(f"Cache zapisany dla {len(waypoints)} waypoints")

class PTVRouteManager:
    def __init__(self, api_key, cache_duration=timedelta(days=7), max_requests_per_second=10):
        self.api_key = api_key
        self.request_queue = PTVRequestQueue(api_key, max_requests_per_second)
        self.cache_manager = RouteCacheManager(cache_duration)

    def get_routes_batch(self, routes, avoid_switzerland=False, avoid_serbia=True, routing_mode=DEFAULT_ROUTING_MODE):
        """Przetwarza wiele tras w jednym wywołaniu"""
        results = {}
        batch_size = 5
        
        for i in range(0, len(routes), batch_size):
            batch = routes[i:i + batch_size]
            waypoints = []
            for coord_from, coord_to in batch:
                waypoints.extend([f"{coord_from[0]},{coord_from[1]}", f"{coord_to[0]},{coord_to[1]}"])
            
            base_url = "https://api.myptv.com/routing/v1/routes/batch"
            headers = {"apiKey": self.api_key}
            params = {
                "waypoints": waypoints,
                "results": "TOLL_COSTS,DISTANCE,POLYLINE,TOLL_SECTIONS,TOLL_SYSTEMS,COMBINED_TRANSPORT_EVENTS",
                "options[routingMode]": routing_mode,
                "options[trafficMode]": "AVERAGE"
            }
            
            # Zbierz kraje do unikania
            prohibited_countries = []
            if avoid_switzerland:
                prohibited_countries.append("CH")
            if avoid_serbia:
                prohibited_countries.append("RS")
            
            if prohibited_countries:
                params["options[prohibitedCountries]"] = ",".join(prohibited_countries)
            
            try:
                response = requests.post(base_url, json=params, headers=headers, timeout=40)
                
                if response.status_code == 200:
                    data = response.json()
                    for idx, route_data in enumerate(data['routes']):
                        route_key = batch[idx]
                        distance_km = route_data['distance'] / 1000
                        
                        # Przetwarzanie opłat drogowych
                        toll_info = self.process_toll_costs(route_data.get('toll', {}))
                        
                        result = {
                            'distance': distance_km,
                            'polyline': route_data.get('polyline', ''),
                            'toll_cost': toll_info['total_cost'],
                            'road_toll': (toll_info['costs_by_type']['ROAD']['EUR'] +
                                         toll_info['costs_by_type']['TUNNEL']['EUR'] +
                                         toll_info['costs_by_type']['BRIDGE']['EUR']),
                            'other_toll': toll_info['costs_by_type']['FERRY']['EUR'],
                            'toll_details': toll_info['total_cost_by_country'],
                            'special_systems': toll_info['special_systems']
                        }
                        
                        # DEBUG: logowanie dla analizy rozbieżności toll
                        logger.info(f"🔍 DEBUG BATCH route_key={route_key}: toll_cost={result['toll_cost']:.2f}, road_toll={result['road_toll']:.2f}, toll_details={result['toll_details']}, special_systems={result['special_systems']}")
                        
                        results[route_key] = result
                        # Zapisz w cache
                        coord_from, coord_to = batch[idx]
                        self.cache_manager.set(coord_from, coord_to, result, avoid_switzerland, False, routing_mode, avoid_serbia)
                else:
                    logger.warning(f"Błąd API PTV batch: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"Wyjątek podczas pobierania tras batch: {str(e)}")
        
        return results

    def get_route_distance(self, coord_from, coord_to, avoid_switzerland=False, avoid_eurotunnel=False, 
                          routing_mode=DEFAULT_ROUTING_MODE, country_from=None, country_to=None, avoid_serbia=True):
        # Sprawdź czy prom jest obowiązkowy
        ferry_route = None
        logger.info(f"🔍 get_route_distance: Sprawdzam promy dla {country_from} -> {country_to}")
        if country_from and country_to and is_ferry_mandatory(country_from, country_to):
            ferry_route = get_best_ferry_for_countries(country_from, country_to)
            if ferry_route:
                logger.info(f"🚢 OBOWIĄZKOWY PROM (get_route_distance): {ferry_route['name']} dla {country_from} -> {country_to}")
                # Jeśli jest prom, użyj get_route_with_waypoints zamiast prostego zapytania
                waypoints = [coord_from, coord_to]
                return self.get_route_with_waypoints(
                    waypoints=waypoints,
                    avoid_switzerland=avoid_switzerland,
                    avoid_eurotunnel=avoid_eurotunnel,
                    routing_mode=routing_mode,
                    country_from=country_from,
                    country_to=country_to,
                    avoid_serbia=avoid_serbia
                )
        
        # Sprawdź cache (dodajemy avoid_serbia do klucza cache)
        cached_result = self.cache_manager.get(coord_from, coord_to, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia)
        if cached_result is not None:
            return cached_result

        # Generuj unikalny ID dla requestu
        request_id = f"route_{coord_from}_{coord_to}_{int(time.time())}"
        
        def _make_request():
            base_url = "https://api.myptv.com/routing/v1/routes"
            headers = {"apiKey": self.api_key}
            
            params = [
                ("waypoints", f"{coord_from[0]},{coord_from[1]}"),
                ("waypoints", f"{coord_to[0]},{coord_to[1]}"),
                ("results", "LEGS,POLYLINE,TOLL_COSTS,TOLL_SECTIONS,TOLL_SYSTEMS,COMBINED_TRANSPORT_EVENTS"),
                ("options[routingMode]", routing_mode),
                ("options[trafficMode]", "AVERAGE")
            ]
            
            # Zbierz kraje do unikania
            prohibited_countries = []
            if avoid_switzerland:
                prohibited_countries.append("CH")
            if avoid_serbia:
                prohibited_countries.append("RS")
            
            # Dodaj jako pojedynczy parametr rozdzielony przecinkami
            if prohibited_countries:
                params.append(("options[prohibitedCountries]", ",".join(prohibited_countries)))
            
            if avoid_eurotunnel:
                params.append(("options[avoid]", "RAIL_SHUTTLES"))

            max_retries = 3
            retry_delay = 2  # sekundy między próbami
            
            # Log parametrów zapytania
            logger.info(f"""
=== Rozpoczynam zapytanie do PTV API ===
URL: {base_url}
Trasa: {coord_from} -> {coord_to}
Parametry:
- Unikanie Szwajcarii: {avoid_switzerland}
- Unikanie Serbii: {avoid_serbia}
- Unikanie Eurotunelu: {avoid_eurotunnel}
- Tryb routingu: {routing_mode}
- Timeout połączenia: 5s
- Timeout odczytu: 35s
""")
            
            for attempt in range(max_retries):
                start_time = time.time()
                try:
                    logger.info(f"Próba {attempt + 1}/{max_retries} - Start")
                    
                    # Rozdzielamy timeout na połączenie (5s) i odczyt (35s)
                    response = requests.get(base_url, params=params, headers=headers, 
                                         timeout=(5, 35))
                    
                    request_time = time.time() - start_time
                    logger.info(f"Czas odpowiedzi: {request_time:.2f}s")
                    
                    if response.status_code == 200:
                        logger.info(f"Sukces - Otrzymano odpowiedź 200 OK w {request_time:.2f}s")
                        data = response.json()
                        
                        # Sprawdź czy są eventy z promami
                        events = data.get('events', [])
                        if events:
                            logger.info(f"📦 Otrzymano {len(events)} eventów z API (w tym potencjalne promy)")
                        
                        # Wyciągnij informacje o promach z eventów
                        ferry_info = self._extract_combined_transport_info(events)
                        
                        # Przetwarzanie kosztów z uwzględnieniem COMBINED_TRANSPORT_EVENTS
                        if 'toll' in data:
                            toll_info = self.process_toll_costs(
                                data['toll'], 
                                data.get('legs', []), 
                                avoid_eurotunnel, 
                                data.get('polyline', ''),
                                events  # COMBINED_TRANSPORT_EVENTS
                            )
                        
                        distance = None
                        if 'legs' in data and isinstance(data['legs'], list):
                            distance = sum(leg.get('distance', 0) for leg in data['legs'])
                            logger.info(f"Obliczony dystans: {distance/1000:.2f}km")
                        
                        if distance is not None:
                            # Oblicz dystans drogowy vs promowy
                            distance_analysis = self._calculate_road_distance(distance, ferry_info)
                            
                            result = {
                                'distance': distance / 1000,  # Całkowity dystans (zgodność wsteczna)
                                'total_distance_km': distance_analysis['total_distance_km'],
                                'road_distance_km': distance_analysis['road_distance_km'],
                                'ferry_distance_km': distance_analysis['ferry_distance_km'],
                                'ferry_segments': distance_analysis['ferry_segments'],
                                'polyline': data.get('polyline', ''),
                                'toll_cost': toll_info['total_cost'],
                                'road_toll': (toll_info['costs_by_type']['ROAD']['EUR'] +
                                             toll_info['costs_by_type']['TUNNEL']['EUR'] +
                                             toll_info['costs_by_type']['BRIDGE']['EUR']),
                                'other_toll': toll_info['costs_by_type']['FERRY']['EUR'],
                                'toll_details': toll_info['total_cost_by_country'],
                                'special_systems': toll_info['special_systems']
                            }
                            
                            # Zapisz w cache
                            self.cache_manager.set(coord_from, coord_to, result, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia)
                            logger.info("=== Zakończono zapytanie z sukcesem ===")
                            return result
                        else:
                            logger.warning(f"Brak danych o dystansie w odpowiedzi API dla trasy {coord_from} -> {coord_to}")
                            return None
                    elif response.status_code == 400 and avoid_switzerland:
                        logger.info(f"""
=== Otrzymano błąd 400 z avoid_switzerland=True ===
Czas odpowiedzi: {request_time:.2f}s
Próbuję bez unikania Szwajcarii...
""")
                        
                        # Usuń parametr avoid_switzerland
                        retry_params = [p for p in params if p[0] != "options[prohibitedCountries]"]
                        
                        # Spróbuj ponownie
                        retry_start_time = time.time()
                        retry_response = requests.get(base_url, params=retry_params, headers=headers, 
                                                   timeout=(5, 35))
                        retry_time = time.time() - retry_start_time
                        
                        logger.info(f"Czas odpowiedzi bez unikania Szwajcarii: {retry_time:.2f}s")
                        
                        if retry_response.status_code == 200:
                            retry_data = retry_response.json()
                            
                            # Wyciągnij informacje o promach
                            retry_events = retry_data.get('events', [])
                            ferry_info = self._extract_combined_transport_info(retry_events)
                            
                            if 'toll' in retry_data:
                                toll_info = self.process_toll_costs(
                                    retry_data['toll'], 
                                    retry_data.get('legs', []), 
                                    avoid_eurotunnel, 
                                    retry_data.get('polyline', ''),
                                    retry_events  # COMBINED_TRANSPORT_EVENTS
                                )
                            
                            distance = None
                            if 'legs' in retry_data and isinstance(retry_data['legs'], list):
                                distance = sum(leg.get('distance', 0) for leg in retry_data['legs'])
                                logger.info(f"Obliczony dystans (bez unikania CH): {distance/1000:.2f}km")
                            
                            if distance is not None:
                                # Oblicz dystans drogowy vs promowy
                                distance_analysis = self._calculate_road_distance(distance, ferry_info)
                                
                                result = {
                                    'distance': distance / 1000,
                                    'total_distance_km': distance_analysis['total_distance_km'],
                                    'road_distance_km': distance_analysis['road_distance_km'],
                                    'ferry_distance_km': distance_analysis['ferry_distance_km'],
                                    'ferry_segments': distance_analysis['ferry_segments'],
                                    'polyline': retry_data.get('polyline', ''),
                                    'toll_cost': toll_info['total_cost'],
                                    'road_toll': (toll_info['costs_by_type']['ROAD']['EUR'] +
                                                 toll_info['costs_by_type']['TUNNEL']['EUR'] +
                                                 toll_info['costs_by_type']['BRIDGE']['EUR']),
                                    'other_toll': toll_info['costs_by_type']['FERRY']['EUR'],
                                    'toll_details': toll_info['total_cost_by_country'],
                                    'special_systems': toll_info['special_systems']
                                }
                                
                                # Zapisz w cache z avoid_switzerland=False
                                self.cache_manager.set(coord_from, coord_to, result, False, avoid_eurotunnel, routing_mode, avoid_serbia)
                                logger.info("=== Zakończono zapytanie z sukcesem (bez unikania CH) ===")
                                return result
                        else:
                            logger.warning(f"""
=== Błąd przy próbie bez unikania Szwajcarii ===
Kod odpowiedzi: {retry_response.status_code}
Czas odpowiedzi: {retry_time:.2f}s
""")
                            return None
                    else:
                        error_details = "Brak szczegółów błędu"
                        try:
                            error_details = response.json()
                        except:
                            try:
                                error_details = response.text
                            except:
                                pass
                        
                        logger.warning(f"""
=== Błąd API PTV ===
Kod odpowiedzi: {response.status_code}
Czas odpowiedzi: {request_time:.2f}s
Trasa: {coord_from} -> {coord_to}
Szczegóły: {error_details}
""")
                        # Nie zwracamy None tutaj - pozwalamy na ponowną próbę
                except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                    request_time = time.time() - start_time
                    if attempt < max_retries - 1:
                        logger.warning(f"""
=== Timeout podczas próby {attempt + 1}/{max_retries} ===
Typ timeoutu: {type(e).__name__}
Czas do timeoutu: {request_time:.2f}s
Trasa: {coord_from} -> {coord_to}
Szczegóły błędu: {str(e)}
Ponawiam za {retry_delay}s...
""")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"""
=== Wszystkie próby zakończone timeoutem ===
Ostatni timeout: {type(e).__name__}
Czas do timeoutu: {request_time:.2f}s
Trasa: {coord_from} -> {coord_to}
Szczegóły ostatniego błędu: {str(e)}
""")
                        return None
                except Exception as e:
                    request_time = time.time() - start_time
                    logger.error(f"""
=== Nieoczekiwany błąd podczas próby {attempt + 1}/{max_retries} ===
Typ błędu: {type(e).__name__}
Czas do błędu: {request_time:.2f}s
Trasa: {coord_from} -> {coord_to}
Szczegóły błędu: {str(e)}
Stack trace:
{traceback.format_exc()}
""")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
            
            logger.error(f"""
=== Wszystkie próby nieudane ===
Trasa: {coord_from} -> {coord_to}
Parametry: {params}
""")
            return None  # Jeśli wszystkie próby się nie powiodły

        # Dodaj request do kolejki
        self.request_queue.add_request(request_id, _make_request)
        
        # Czekaj na wynik (z timeout)
        max_wait = 30  # sekundy
        start_time = time.time()
        while time.time() - start_time < max_wait:
            result = self.request_queue.get_result(request_id)
            if result is not None:
                if result['status'] == 'success':
                    return result['data']
                else:
                    return None
            time.sleep(0.1)
        
        logger.warning("Timeout")
        return None

    def get_route_with_waypoints(self, waypoints, avoid_switzerland=False, avoid_eurotunnel=False, 
                                   routing_mode=DEFAULT_ROUTING_MODE, country_from=None, country_to=None, avoid_serbia=True):
        """
        Oblicza trasę z wieloma waypoints.
        
        Args:
            waypoints: Lista współrzędnych [(lat1, lon1), (lat2, lon2), ...]
                      Minimum 2 punkty (start, end), maksimum 25
            avoid_switzerland: Czy unikać Szwajcarii
            avoid_eurotunnel: Czy unikać Eurotunelu (RAIL_SHUTTLES)
            avoid_serbia: Czy unikać Serbii
            routing_mode: Tryb routingu (FAST, ECO, SHORT)
            country_from: Kod kraju początkowego (opcjonalnie, do wykrycia obowiązkowych promów)
            country_to: Kod kraju docelowego (opcjonalnie, do wykrycia obowiązkowych promów)
        
        Returns:
            Dict z wynikami lub None w przypadku błędu
        """
        if len(waypoints) < 2:
            logger.error("Minimum 2 waypoints required")
            return None
        
        if len(waypoints) > 25:
            logger.error(f"Maximum 25 waypoints allowed, got {len(waypoints)}")
            return None
        
        # Sprawdź czy prom jest obowiązkowy dla tej pary krajów
        ferry_route = None
        if country_from and country_to and is_ferry_mandatory(country_from, country_to):
            ferry_route = get_best_ferry_for_countries(country_from, country_to)
            if ferry_route:
                logger.info(f"🚢 OBOWIĄZKOWY PROM wykryty: {ferry_route['name']} dla trasy {country_from} -> {country_to}")
                logger.info("🔧 Dzielę trasę na 2 segmenty: [start→port_A] + [prom_A→B] + [port_B→end]")
                
                ferry_start = ferry_route['start']
                ferry_end = ferry_route['end']
                
                # Segment 1: wszystkie waypoints przed promem + port startowy
                segment1_waypoints = waypoints[:-1] + [ferry_start]
                logger.info(f"Segment 1: {len(segment1_waypoints)} waypoints (do portu {ferry_route['name'].split('-')[0]})")
                
                # Segment 2: port docelowy + wszystkie waypoints po promie
                segment2_waypoints = [ferry_end] + [waypoints[-1]]
                logger.info(f"Segment 2: {len(segment2_waypoints)} waypoints (od portu {ferry_route['name'].split('-')[1]})")
                
                # Oblicz segment 1
                result1 = self.get_route_with_waypoints(
                    segment1_waypoints,
                    avoid_switzerland=avoid_switzerland,
                    avoid_eurotunnel=avoid_eurotunnel,
                    avoid_serbia=avoid_serbia,
                    routing_mode=routing_mode,
                    country_from=None,  # Bez rekurencji
                    country_to=None
                )
                
                if not result1:
                    logger.error("Nie udało się obliczyć segmentu 1 (do portu)")
                    return None
                
                # Oblicz segment 2
                result2 = self.get_route_with_waypoints(
                    segment2_waypoints,
                    avoid_switzerland=avoid_switzerland,
                    avoid_eurotunnel=avoid_eurotunnel,
                    avoid_serbia=avoid_serbia,
                    routing_mode=routing_mode,
                    country_from=None,  # Bez rekurencji
                    country_to=None
                )
                
                if not result2:
                    logger.error("Nie udało się obliczyć segmentu 2 (od portu)")
                    return None
                
                # Połącz wyniki
                logger.info(f"✅ Segment 1: {result1['distance']:.2f} km, toll_cost={result1['toll_cost']:.2f} EUR, road_toll={result1.get('road_toll', 0):.2f} EUR")
                logger.info(f"   Segment 1 toll_details: {result1.get('toll_details', {})}")
                logger.info(f"   Segment 1 special_systems: {result1.get('special_systems', [])}")
                logger.info(f"✅ Segment 2: {result2['distance']:.2f} km, toll_cost={result2['toll_cost']:.2f} EUR, road_toll={result2.get('road_toll', 0):.2f} EUR")
                logger.info(f"   Segment 2 toll_details: {result2.get('toll_details', {})}")
                logger.info(f"   Segment 2 special_systems: {result2.get('special_systems', [])}")
                logger.info(f"🚢 Prom: {ferry_route['duration_hours']}h, {ferry_route['cost']} EUR")
                
                # Pobierz dystans promu ze słownika
                ferry_name = ferry_route['name']
                ferry_sea_distance_km = FERRY_SEA_DISTANCES.get(ferry_name, 0)
                
                if ferry_sea_distance_km == 0:
                    # Fallback: oszacuj z czasu (30 km/h)
                    ferry_sea_distance_km = ferry_route.get('duration_hours', 0) * 30
                    logger.warning(
                        f"⚠️  Prom '{ferry_name}': brak w słowniku, szacuję dystans = {ferry_sea_distance_km:.1f} km"
                    )
                
                # Oblicz dystanse
                # UWAGA: Segmenty 1 i 2 to trasy drogowe (bez promu obowiązkowego między nimi)
                segment1_road_km = result1.get('road_distance_km', result1['distance'])
                segment2_road_km = result2.get('road_distance_km', result2['distance'])
                segment1_ferry_km = result1.get('ferry_distance_km', 0)
                segment2_ferry_km = result2.get('ferry_distance_km', 0)
                
                # Dystans drogowy = segmenty drogowe (bez promu obowiązkowego)
                total_road_km = segment1_road_km + segment2_road_km
                
                # Dystans promowy = promy w segmentach + prom obowiązkowy
                total_ferry_km = segment1_ferry_km + segment2_ferry_km + ferry_sea_distance_km
                
                # Całkowity dystans = dystans drogowy + dystans promowy
                # NIE używamy result1['distance'] + result2['distance'], bo to nie zawiera promu obowiązkowego!
                total_distance_km = total_road_km + total_ferry_km
                
                # Połącz dystanse, koszty i szczegóły
                combined_result = {
                    'distance': total_distance_km,  # Zgodność wsteczna
                    'total_distance_km': total_distance_km,
                    'road_distance_km': total_road_km,
                    'ferry_distance_km': total_ferry_km,
                    'ferry_segments': result1.get('ferry_segments', []) + result2.get('ferry_segments', []) + [{
                        'name': ferry_name,
                        'distance_km': ferry_sea_distance_km,
                        'duration_hours': ferry_route.get('duration_hours', 0)
                    }],
                    'legs': result1.get('legs', []) + result2.get('legs', []),
                    'polyline': result1.get('polyline', '') + '|' + result2.get('polyline', ''),
                    'toll_cost': result1['toll_cost'] + result2['toll_cost'] + ferry_route['cost'],
                    'road_toll': result1.get('road_toll', 0) + result2.get('road_toll', 0),
                    'other_toll': result1.get('other_toll', 0) + result2.get('other_toll', 0) + ferry_route['cost'],
                    'toll_details': {},
                    'special_systems': [],
                    'ferry_ports': {
                        'start': ferry_start,
                        'end': ferry_end
                    }
                }
                
                logger.info(
                    f"📏 Połączone dystanse: total={total_distance_km:.2f}km, "
                    f"road={total_road_km:.2f}km, ferry={total_ferry_km:.2f}km"
                )
                
                # Połącz toll_details
                for country, cost in result1.get('toll_details', {}).items():
                    combined_result['toll_details'][country] = combined_result['toll_details'].get(country, 0) + cost
                for country, cost in result2.get('toll_details', {}).items():
                    combined_result['toll_details'][country] = combined_result['toll_details'].get(country, 0) + cost
                
                # Połącz special_systems
                combined_result['special_systems'].extend(result1.get('special_systems', []))
                combined_result['special_systems'].extend(result2.get('special_systems', []))
                combined_result['special_systems'].append({
                    'name': ferry_route['name'],
                    'cost': ferry_route['cost'],
                    'type': 'FERRY',
                    'operator': ferry_route.get('operator', ''),
                    'duration_hours': ferry_route.get('duration_hours', 0),
                    'mandatory': True
                })
                
                combined_result['ferry_used'] = ferry_route['name']
                
                logger.info(f"📊 ŁĄCZNIE: {combined_result['distance']:.2f} km, toll_cost={combined_result['toll_cost']:.2f} EUR, road_toll={combined_result['road_toll']:.2f} EUR")
                logger.info(f"   ŁĄCZNIE toll_details: {combined_result['toll_details']}")
                logger.info(f"   ŁĄCZNIE special_systems: {combined_result['special_systems']}")
                
                return combined_result
        
        # Sprawdź cache
        cached_result = self.cache_manager.get_waypoints_route(
            waypoints, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia
        )
        if cached_result is not None:
            logger.info(f"Cache HIT dla trasy z {len(waypoints)} waypoints")
            return cached_result
        
        logger.info(f"Cache MISS - wywołanie PTV API dla {len(waypoints)} waypoints")
        
        # Generuj unikalny ID dla requestu
        request_id = f"route_waypoints_{hash(tuple(waypoints))}_{int(time.time())}"
        
        def _make_request():
            base_url = "https://api.myptv.com/routing/v1/routes"
            headers = {"apiKey": self.api_key}
            
            # Budowanie parametrów - każdy waypoint jako osobny parametr
            params = []
            for lat, lon in waypoints:
                params.append(("waypoints", f"{lat},{lon}"))
            
            params.extend([
                ("results", "LEGS,POLYLINE,TOLL_COSTS,TOLL_SECTIONS,TOLL_SYSTEMS,COMBINED_TRANSPORT_EVENTS"),
                ("options[routingMode]", routing_mode),
                ("options[trafficMode]", "AVERAGE")
            ])
            
            # Zbierz kraje do unikania
            prohibited_countries = []
            if avoid_switzerland:
                prohibited_countries.append("CH")
            if avoid_serbia:
                prohibited_countries.append("RS")
            
            # Dodaj jako pojedynczy parametr rozdzielony przecinkami
            if prohibited_countries:
                params.append(("options[prohibitedCountries]", ",".join(prohibited_countries)))
            
            if avoid_eurotunnel:
                params.append(("options[avoid]", "RAIL_SHUTTLES"))
            
            logger.info(f"PTV API request: {len(waypoints)} waypoints, avoid_CH={avoid_switzerland}, avoid_RS={avoid_serbia}, avoid_eurotunnel={avoid_eurotunnel}")
            
            # Retry logic
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                start_time = time.time()
                
                try:
                    logger.debug(f"Próba {attempt + 1}/{max_retries}")
                    
                    response = requests.get(
                        base_url, 
                        params=params, 
                        headers=headers, 
                        timeout=(5, 35)
                    )
                    
                    request_time = time.time() - start_time
                    logger.info(f"PTV API response: {response.status_code} w {request_time:.2f}s")
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Sprawdź czy są eventy z promami
                        events = data.get('events', [])
                        if events:
                            logger.info(f"📦 Otrzymano {len(events)} eventów z API dla trasy z {len(waypoints)} waypoints")
                        
                        # Wyciągnij informacje o promach
                        ferry_info = self._extract_combined_transport_info(events)
                        
                        # Przetwarzanie opłat drogowych z uwzględnieniem COMBINED_TRANSPORT_EVENTS
                        toll_info = self.process_toll_costs(
                            data.get('toll', {}), 
                            data.get('legs', []), 
                            avoid_eurotunnel, 
                            data.get('polyline', ''),
                            events  # COMBINED_TRANSPORT_EVENTS
                        )
                        
                        # Oblicz całkowity dystans ze wszystkich legs
                        total_distance = 0
                        if 'legs' in data and isinstance(data['legs'], list):
                            total_distance = sum(
                                leg.get('distance', 0) for leg in data['legs']
                            )
                            logger.debug(f"Obliczony dystans: {total_distance/1000:.2f}km z {len(data['legs'])} segmentów")
                        
                        # Oblicz dystans drogowy vs promowy
                        distance_analysis = self._calculate_road_distance(total_distance, ferry_info)
                        
                        result = {
                            'distance': total_distance / 1000,  # m → km (zgodność wsteczna)
                            'total_distance_km': distance_analysis['total_distance_km'],
                            'road_distance_km': distance_analysis['road_distance_km'],
                            'ferry_distance_km': distance_analysis['ferry_distance_km'],
                            'ferry_segments': distance_analysis['ferry_segments'],
                            'legs': data.get('legs', []),
                            'polyline': data.get('polyline', ''),
                            'toll_cost': toll_info['total_cost'],
                            'road_toll': (
                                toll_info['costs_by_type']['ROAD']['EUR'] +
                                toll_info['costs_by_type']['TUNNEL']['EUR'] +
                                toll_info['costs_by_type']['BRIDGE']['EUR']
                            ),
                            'other_toll': toll_info['costs_by_type']['FERRY']['EUR'],
                            'toll_details': toll_info['total_cost_by_country'],
                            'special_systems': toll_info['special_systems'],
                            'ferry_used': None
                        }
                        
                        # Zapisz w cache
                        self.cache_manager.set_waypoints_route(
                            waypoints, result, avoid_switzerland, avoid_eurotunnel, routing_mode, avoid_serbia
                        )
                        
                        logger.info("Trasa obliczona i zapisana w cache")
                        return result
                    
                    elif response.status_code == 400 and avoid_switzerland:
                        logger.warning("Błąd 400 z avoid_switzerland=True - próbuję bez unikania Szwajcarii")
                        
                        retry_params = [p for p in params if p[0] != "options[prohibitedCountries]"]
                        retry_response = requests.get(
                            base_url, params=retry_params, headers=headers, timeout=(5, 35)
                        )
                        
                        if retry_response.status_code == 200:
                            data = retry_response.json()
                            
                            # Wyciągnij informacje o promach
                            retry_events = data.get('events', [])
                            ferry_info = self._extract_combined_transport_info(retry_events)
                            
                            toll_info = self.process_toll_costs(
                                data.get('toll', {}), 
                                data.get('legs', []), 
                                avoid_eurotunnel, 
                                data.get('polyline', ''),
                                retry_events  # COMBINED_TRANSPORT_EVENTS
                            )
                            
                            total_distance = 0
                            if 'legs' in data:
                                total_distance = sum(leg.get('distance', 0) for leg in data['legs'])
                            
                            # Oblicz dystans drogowy vs promowy
                            distance_analysis = self._calculate_road_distance(total_distance, ferry_info)
                            
                            result = {
                                'distance': total_distance / 1000,
                                'total_distance_km': distance_analysis['total_distance_km'],
                                'road_distance_km': distance_analysis['road_distance_km'],
                                'ferry_distance_km': distance_analysis['ferry_distance_km'],
                                'ferry_segments': distance_analysis['ferry_segments'],
                                'legs': data.get('legs', []),
                                'polyline': data.get('polyline', ''),
                                'toll_cost': toll_info['total_cost'],
                                'road_toll': (
                                    toll_info['costs_by_type']['ROAD']['EUR'] +
                                    toll_info['costs_by_type']['TUNNEL']['EUR'] +
                                    toll_info['costs_by_type']['BRIDGE']['EUR']
                                ),
                                'other_toll': toll_info['costs_by_type']['FERRY']['EUR'],
                                'toll_details': toll_info['total_cost_by_country'],
                                'special_systems': toll_info['special_systems'],
                                'ferry_used': None
                            }
                            
                            # Zapisz z avoid_switzerland=False
                            self.cache_manager.set_waypoints_route(
                                waypoints, result, False, avoid_eurotunnel, routing_mode, avoid_serbia
                            )
                            
                            logger.info("Trasa obliczona bez unikania Szwajcarii")
                            return result
                        else:
                            logger.error(f"Fallback również nieudany: {retry_response.status_code}")
                            return None
                    
                    else:
                        logger.warning(f"PTV API błąd: {response.status_code}")
                    
                except (requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
                    request_time = time.time() - start_time
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"Timeout ({type(e).__name__}) po {request_time:.2f}s - retry za {retry_delay}s...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Wszystkie próby zakończone timeoutem po {request_time:.2f}s")
                        return None
                
                except Exception as e:
                    logger.error(f"Nieoczekiwany błąd: {e}", exc_info=True)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
            
            logger.error("Wszystkie próby nieudane")
            return None
        
        # Dodaj request do kolejki
        self.request_queue.add_request(request_id, _make_request)
        
        # Czekaj na wynik (dłuższy timeout dla tras z waypoints)
        max_wait = 40
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            result = self.request_queue.get_result(request_id)
            if result is not None:
                if result['status'] == 'success':
                    return result['data']
                else:
                    logger.error(f"Request zakończony błędem: {result.get('error')}")
                    return None
            time.sleep(0.1)
        
        logger.warning(f"Timeout oczekiwania na wynik ({max_wait}s)")
        return None

    def get_stats(self):
        return self.cache_manager.get_stats()

    def separate_toll_costs_by_type(self, toll_data):
        """Separates toll costs by type (road, tunnel, bridge, ferry)"""
        result = {
            'ROAD': {'EUR': 0.0},  # standardowe opłaty drogowe
            'TUNNEL': {'EUR': 0.0},  # tunele
            'BRIDGE': {'EUR': 0.0},  # mosty
            'FERRY': {'EUR': 0.0},   # promy
        }
        
        if not toll_data or 'sections' not in toll_data:
            return result
        
        for section in toll_data['sections']:
            toll_type = section.get('tollRoadType', 'GENERAL')
            # Mapowanie GENERAL na ROAD dla lepszej czytelności
            if toll_type == 'GENERAL':
                toll_type = 'ROAD'
            
            for cost in section.get('costs', []):
                currency = cost.get('currency', 'EUR')
                price = cost.get('price', 0.0)
                
                # Inicjalizacja słownika dla nowej waluty jeśli potrzebne
                if currency not in result[toll_type]:
                    result[toll_type][currency] = 0.0
                
                result[toll_type][currency] += price
                
                # Jeśli mamy przeliczoną cenę w EUR, dodajemy ją też
                converted_price = cost.get('convertedPrice', {}).get('price', 0.0)
                if converted_price and currency != 'EUR':
                    result[toll_type]['EUR'] += converted_price
        
        return result

    def _decode_polyline(self, polyline_str):
        """
        Dekoduje polyline z API PTV do listy punktów [lat, lng].
        Obsługuje zarówno format GeoJSON jak i standardowy encoded polyline.
        """
        import polyline as pl
        
        try:
            if not polyline_str or not isinstance(polyline_str, str):
                return []
            
            # Sprawdź czy mamy do czynienia z formatem GeoJSON
            if 'coordinates' in polyline_str:
                try:
                    # Znajdź początek i koniec koordynatów
                    start = polyline_str.find('[[') + 2
                    end = polyline_str.rfind(']]')
                    if start == -1 or end == -1:
                        return []
                    
                    # Wyciągnij tylko koordynaty
                    coords_str = polyline_str[start:end]
                    points = []
                    
                    # Podziel na pary współrzędnych
                    coords = coords_str.split('],[')
                    for coord in coords:
                        coord = coord.strip('[]')
                        if ',' in coord:
                            try:
                                lng, lat = map(float, coord.split(','))
                                points.append((lat, lng))  # tuple zamiast list
                            except (ValueError, TypeError):
                                continue
                    
                    return points
                except Exception:
                    return []
            else:
                # Spróbuj standardowego dekodowania polyline
                try:
                    return pl.decode(polyline_str)
                except Exception:
                    return []
        except Exception:
            return []

    def _calculate_distance_in_gb(self, polyline_str, toll_data):
        """
        Oblicza dystans w GB używając dodatkowego zapytania do PTV API.
        
        1. Dekoduje polyline i bierze pierwszy/ostatni punkt
        2. Sprawdza czy GB jest na początku czy końcu trasy
        3. Robi zapytanie do PTV API: punkt_w_GB → Dover lub Dover → punkt_w_GB
        
        Args:
            polyline_str: Zakodowany polyline z odpowiedzi API
            toll_data: Dane toll z odpowiedzi API (do sprawdzenia kolejności krajów)
        
        Returns:
            float: Dystans w GB w metrach
        """
        # Dover - główny port promowy GB
        DOVER_COORDS = (51.1279, 1.3134)
        
        if not polyline_str:
            logger.warning("_calculate_distance_in_gb: brak polyline_str")
            return 0
        
        try:
            import polyline as pl
            
            # Dekoduj polyline (ten sam sposób co w appGPT.py)
            coords = self._decode_polyline(polyline_str)
            
            logger.info(f"_calculate_distance_in_gb: zdekodowano {len(coords)} punktów")
            
            if len(coords) < 2:
                return 0
            
            # Pierwszy i ostatni punkt trasy
            first_point = coords[0]
            last_point = coords[-1]
            
            logger.info(f"_calculate_distance_in_gb: pierwszy punkt {first_point}, ostatni punkt {last_point}")
            
            # Sprawdź kolejność krajów w toll_data
            countries_order = []
            if toll_data and 'costs' in toll_data:
                for country in toll_data['costs'].get('countries', []):
                    code = country.get('countryCode', '').upper()
                    if code:
                        countries_order.append(code)
            
            logger.info(f"_calculate_distance_in_gb: kolejność krajów: {countries_order}")
            
            if 'GB' not in countries_order:
                return 0
            
            # Określ czy GB jest na początku czy na końcu trasy
            gb_at_start = countries_order[0] == 'GB' if countries_order else False
            gb_at_end = countries_order[-1] == 'GB' if countries_order else False
            
            # Wybierz punkty do zapytania API
            if gb_at_start:
                # Trasa zaczyna się w GB - oblicz dystans od startu do Dover
                gb_point = first_point
                logger.info(f"GB na początku trasy - obliczam dystans {gb_point} → Dover")
            elif gb_at_end:
                # Trasa kończy się w GB - oblicz dystans od Dover do końca
                gb_point = last_point
                logger.info(f"GB na końcu trasy - obliczam dystans Dover → {gb_point}")
            else:
                logger.warning("GB nie jest ani na początku ani na końcu trasy")
                return 0
            
            # Zapytanie do PTV API o dystans w GB
            base_url = "https://api.myptv.com/routing/v1/routes"
            headers = {"apiKey": self.api_key}
            
            if gb_at_start:
                params = [
                    ("waypoints", f"{gb_point[0]},{gb_point[1]}"),
                    ("waypoints", f"{DOVER_COORDS[0]},{DOVER_COORDS[1]}"),
                    ("options[routingMode]", "FAST")
                ]
            else:
                params = [
                    ("waypoints", f"{DOVER_COORDS[0]},{DOVER_COORDS[1]}"),
                    ("waypoints", f"{gb_point[0]},{gb_point[1]}"),
                    ("options[routingMode]", "FAST")
                ]
            
            # Nie dodajemy prohibitedCountries dla tras w GB (zawsze jesteśmy w UK)
            
            logger.info(f"_calculate_distance_in_gb: wysyłam zapytanie do PTV API: {params}")
            response = requests.get(base_url, params=params, headers=headers, timeout=(5, 30))
            
            if response.status_code == 200:
                data = response.json()
                gb_distance = data.get('distance', 0)
                logger.info(f"_calculate_distance_in_gb: PTV API zwróciło dystans w GB = {gb_distance/1000:.0f}km")
                return gb_distance
            else:
                logger.warning(f"_calculate_distance_in_gb: błąd API {response.status_code}: {response.text[:500]}")
                return 0
            
        except Exception as e:
            logger.warning(f"Błąd podczas obliczania dystansu w GB: {e}")
            return 0

    def _calculate_uk_levy_days(self, toll_data, legs_data=None, polyline_str=None):
        """
        Oblicza liczbę dni winiety UK HGV Levy na podstawie dystansu w GB.
        
        UK HGV Levy jest dzienną opłatą - każdy rozpoczęty dzień = 1 opłata.
        
        Używa tej samej logiki co transit_time w appGPT.py:
        - 0-350km = 1 dzień
        - 351-500km = 1.25 dnia → 2 dni winiety
        - 501-700km = 1.5 dnia → 2 dni winiety
        - 701-1100km = 2 dni
        - itd.
        
        Args:
            toll_data: Dane toll z odpowiedzi API
            legs_data: Dane legs z odpowiedzi API
            polyline_str: Zakodowany polyline do obliczenia dystansu w GB
        
        Returns:
            int: Liczba dni winiety (0 jeśli nie można obliczyć lub trasa nie przechodzi przez GB)
        """
        logger.info(f"_calculate_uk_levy_days: START, polyline_str len={len(polyline_str) if polyline_str else 0}")
        
        if not toll_data:
            logger.info("_calculate_uk_levy_days: brak toll_data")
            return 0
        
        # Sprawdź czy trasa przechodzi przez GB
        has_gb = False
        if 'costs' in toll_data:
            for country in toll_data['costs'].get('countries', []):
                if country.get('countryCode', '').upper() == 'GB':
                    has_gb = True
                    break
        
        logger.info(f"_calculate_uk_levy_days: has_gb={has_gb}")
        
        if not has_gb:
            return 0
        
        # Oblicz dystans w GB - dodatkowe zapytanie do PTV API
        gb_distance_m = self._calculate_distance_in_gb(polyline_str, toll_data)
        logger.info(f"_calculate_uk_levy_days: gb_distance_m={gb_distance_m}")
        
        if gb_distance_m <= 0:
            logger.warning(f"UK HGV Levy: nie można obliczyć dystansu w GB - brak polyline lub brak punktów w GB")
            return 0
        
        # Konwersja na km
        gb_distance_km = gb_distance_m / 1000
        
        # Oblicz liczbę dni według tej samej logiki co transit_time w appGPT.py
        if gb_distance_km <= 350:
            transit_days = 1
        elif gb_distance_km <= 500:
            transit_days = 1.25
        elif gb_distance_km <= 700:
            transit_days = 1.5
        elif gb_distance_km <= 1100:
            transit_days = 2
        elif gb_distance_km <= 1700:
            transit_days = 3
        elif gb_distance_km <= 2300:
            transit_days = 4
        elif gb_distance_km <= 2900:
            transit_days = 5
        elif gb_distance_km <= 3500:
            transit_days = 6
        else:
            transit_days = math.ceil(gb_distance_km / 500)
        
        # Zaokrąglij w górę - każdy rozpoczęty dzień = opłata winiety
        levy_days = math.ceil(transit_days)
        
        logger.info(f"UK HGV Levy: dystans w GB = {gb_distance_km:.0f}km, transit_days = {transit_days}, levy_days = {levy_days}")
        return levy_days

    def _extract_combined_transport_info(self, events_data):
        """
        Wyciąga informacje o przeprawach promowych z COMBINED_TRANSPORT_EVENTS.
        
        Oficjalne rozwiązanie PTV Developer API - zgodne z dokumentacją:
        https://developer.myptv.com/en/documentation/routing-api/concepts/events
        
        Args:
            events_data: Lista eventów z odpowiedzi API (data.get('events', []))
        
        Returns:
            dict: {
                'has_ferry': bool,           # Czy wykryto przeprawę promową
                'ferries': list,             # Lista przepraw promowych
                'total_ferry_duration': int, # Całkowity czas przepraw (s)
                'ferry_names': list          # Nazwy przepraw
            }
        """
        result = {
            'has_ferry': False,
            'ferries': [],
            'total_ferry_duration': 0,
            'ferry_names': []
        }
        
        if not events_data or not isinstance(events_data, list):
            return result
        
        logger.info(f"🔍 Analizuję {len(events_data)} eventów z API PTV...")
        
        # Najpierw znajdź wszystkie pary ENTER/EXIT
        ferry_pairs = []
        enter_events = {}  # {index: event}
        
        for i, event in enumerate(events_data):
            if 'combinedTransport' not in event:
                continue
                
            ct = event.get('combinedTransport', {})
            ct_type = ct.get('type', '')
            access_type = ct.get('accessType', '')
            
            # Sprawdź czy to prom
            is_ferry = (
                ct_type == 'BOAT' or 
                ct_type == 1 or 
                str(ct_type).upper() == 'FERRY'
            )
            
            if not is_ferry:
                continue
            
            logger.debug(
                f"Event {i}: {access_type} - {ct.get('name')} "
                f"at {event.get('distanceFromStart', 0)}m, "
                f"time={event.get('travelTimeFromStart', 0)}s"
            )
            
            if access_type == 'ENTER':
                enter_events[i] = event
            elif access_type == 'EXIT':
                # Znajdź odpowiadający ENTER
                related_idx = ct.get('relatedEventIndex')
                if related_idx is not None and related_idx in enter_events:
                    enter_event = enter_events[related_idx]
                    ferry_pairs.append((enter_event, event))
                    del enter_events[related_idx]
        
        # Przetwórz pary ENTER/EXIT
        ferry_count = 0
        for enter_event, exit_event in ferry_pairs:
            ferry_count += 1
            
            enter_ct = enter_event.get('combinedTransport', {})
            exit_ct = exit_event.get('combinedTransport', {})
            
            # Oblicz rzeczywisty czas przeprawy z różnicy czasów
            enter_time = enter_event.get('travelTimeFromStart', 0)
            exit_time = exit_event.get('travelTimeFromStart', 0)
            ferry_duration = exit_time - enter_time
            
            # Dystans od startu trasy
            enter_distance = enter_event.get('distanceFromStart', 0)
            
            ferry_info = {
                'name': enter_ct.get('name', 'Unknown Ferry'),
                'duration': ferry_duration,  # RZECZYWISTY czas przeprawy
                'distance': 0,  # PTV celowo daje 0
                'distance_from_start': enter_distance,
                'travel_time_from_start': enter_time,
                'latitude': enter_event.get('latitude'),
                'longitude': enter_event.get('longitude'),
                'start': {'latitude': enter_event.get('latitude'), 'longitude': enter_event.get('longitude')},
                'destination': {'latitude': exit_event.get('latitude'), 'longitude': exit_event.get('longitude')}
            }
            
            result['ferries'].append(ferry_info)
            result['total_ferry_duration'] += ferry_duration
            
            if ferry_info['name'] and ferry_info['name'] != 'Unknown Ferry':
                result['ferry_names'].append(ferry_info['name'])
            
            # Szczegółowe logowanie
            duration_hours = ferry_duration / 3600
            duration_mins = (ferry_duration % 3600) / 60
            distance_from_start_km = enter_distance / 1000
            
            logger.info(
                f"🚢 PROM #{ferry_count}: {ferry_info['name']}\n"
                f"   ├─ ENTER: ({enter_event.get('latitude'):.4f}, {enter_event.get('longitude'):.4f})\n"
                f"   ├─ EXIT:  ({exit_event.get('latitude'):.4f}, {exit_event.get('longitude'):.4f})\n"
                f"   ├─ Czas przeprawy: {int(duration_hours)}h {int(duration_mins)}min ({ferry_duration}s)\n"
                f"   ├─ Dystans z API: 0 km (celowo - żeby nie dublować)\n"
                f"   └─ Pozycja na trasie: {distance_from_start_km:.1f} km od startu"
            )
        
        result['has_ferry'] = len(result['ferries']) > 0
        
        if result['has_ferry']:
            total_hours = result['total_ferry_duration'] / 3600
            total_mins = (result['total_ferry_duration'] % 3600) / 60
            logger.info(
                f"{'='*70}\n"
                f"📊 PODSUMOWANIE PROMÓW:\n"
                f"   ├─ Liczba promów: {len(result['ferries'])}\n"
                f"   ├─ Łączny czas przepraw: {int(total_hours)}h {int(total_mins)}min\n"
                f"   └─ Użyte promy: {', '.join(result['ferry_names'])}\n"
                f"{'='*70}"
            )
        else:
            logger.info("ℹ️  Brak przepraw promowych na tej trasie")
        
        return result

    def _calculate_road_distance(self, total_distance_m, ferry_info):
        """
        Oblicza dystans drogowy (na kołach) odejmując dystans promowy.
        
        Dystans promowy nie powinien być wliczany do kosztów paliwa/emisji,
        ponieważ pojazd nie jedzie na własnych kołach podczas przeprawy.
        
        Args:
            total_distance_m: Całkowity dystans trasy w metrach (z API)
            ferry_info: Dict z informacjami o promach z _extract_combined_transport_info()
        
        Returns:
            dict: {
                'total_distance_km': float,     # Całkowity dystans [km]
                'road_distance_km': float,      # Dystans na drogach [km]
                'ferry_distance_km': float,     # Dystans na promach [km]
                'ferry_segments': list          # Lista segmentów promowych z szczegółami
            }
        """
        result = {
            'total_distance_km': total_distance_m / 1000.0,
            'road_distance_km': total_distance_m / 1000.0,
            'ferry_distance_km': 0.0,
            'ferry_segments': []
        }
        
        if not ferry_info or not ferry_info.get('has_ferry'):
            logger.debug(f"📏 Dystans drogowy = dystans całkowity = {result['total_distance_km']:.2f} km (brak promów)")
            return result
        
        # Oblicz dystans promowy z FERRY_SEA_DISTANCES
        total_ferry_distance_km = 0.0
        
        for ferry in ferry_info.get('ferries', []):
            ferry_name = ferry.get('name', 'Unknown Ferry')
            
            # Spróbuj znaleźć dystans morski w słowniku
            sea_distance_km = FERRY_SEA_DISTANCES.get(ferry_name, 0)
            
            if sea_distance_km > 0:
                logger.info(f"🌊 Prom '{ferry_name}': dystans morski = {sea_distance_km} km (ze słownika)")
            else:
                # Fallback: użyj dystansu z API (może być 0)
                api_distance_km = ferry.get('distance', 0) / 1000.0
                if api_distance_km > 0:
                    sea_distance_km = api_distance_km
                    logger.warning(
                        f"⚠️  Prom '{ferry_name}': brak w słowniku FERRY_SEA_DISTANCES, "
                        f"używam dystansu z API = {sea_distance_km:.2f} km"
                    )
                else:
                    # Estimate z czasu przeprawy (średnia prędkość promu ≈ 30 km/h)
                    duration_hours = ferry.get('duration', 0) / 3600.0
                    if duration_hours > 0:
                        sea_distance_km = duration_hours * 30.0
                        logger.warning(
                            f"⚠️  Prom '{ferry_name}': szacuję dystans z czasu przeprawy "
                            f"({duration_hours:.1f}h × 30km/h) = {sea_distance_km:.1f} km"
                        )
                    else:
                        logger.error(f"❌ Prom '{ferry_name}': nie można określić dystansu morskiego!")
                        sea_distance_km = 0
            
            total_ferry_distance_km += sea_distance_km
            
            result['ferry_segments'].append({
                'name': ferry_name,
                'distance_km': sea_distance_km,
                'duration_hours': ferry.get('duration', 0) / 3600.0
            })
        
        # Oblicz dystans drogowy
        result['ferry_distance_km'] = total_ferry_distance_km
        result['road_distance_km'] = result['total_distance_km'] - total_ferry_distance_km
        
        # Sprawdź czy wynik ma sens
        if result['road_distance_km'] < 0:
            logger.error(
                f"❌ BŁĄD: Dystans drogowy < 0! "
                f"total={result['total_distance_km']:.1f}km, "
                f"ferry={total_ferry_distance_km:.1f}km"
            )
            result['road_distance_km'] = result['total_distance_km']
            result['ferry_distance_km'] = 0
        
        logger.info(
            f"\n{'='*70}\n"
            f"📏 ANALIZA DYSTANSU:\n"
            f"   ├─ Dystans CAŁKOWITY: {result['total_distance_km']:.2f} km\n"
            f"   ├─ Dystans DROGOWY (na kołach): {result['road_distance_km']:.2f} km\n"
            f"   ├─ Dystans PROMOWY (morski): {result['ferry_distance_km']:.2f} km\n"
            f"   └─ Liczba promów: {len(result['ferry_segments'])}\n"
            f"{'='*70}"
        )
        
        return result

    def _detect_channel_ferry(self, toll_data, legs_data=None, avoid_eurotunnel=True, events_data=None):
        """
        Wykrywa przeprawę promową przez Kanał La Manche (Dover-Calais lub podobne).
        
        Metoda używa dwóch strategii wykrywania:
        1. OFICJALNA (priorytetowa): COMBINED_TRANSPORT_EVENTS z API PTV
        2. FALLBACK (heurystyczna): Gdy brak eventów - analiza krajów na trasie
        
        Args:
            toll_data: Dane toll z odpowiedzi API
            legs_data: Opcjonalne dane legs z odpowiedzi API
            avoid_eurotunnel: Czy Eurotunel jest zablokowany (=musi być prom)
            events_data: Opcjonalne eventy z odpowiedzi API (COMBINED_TRANSPORT_EVENTS)
        
        Returns:
            dict: {
                'detected': bool,        # Czy wykryto przeprawę
                'method': str,           # 'official' lub 'heuristic'
                'ferry_info': dict|None  # Szczegóły z COMBINED_TRANSPORT_EVENTS
            }
        """
        result = {
            'detected': False,
            'method': None,
            'ferry_info': None
        }
        
        # === STRATEGIA 1: Oficjalna - COMBINED_TRANSPORT_EVENTS ===
        if events_data:
            ct_info = self._extract_combined_transport_info(events_data)
            if ct_info['has_ferry']:
                logger.info(
                    f"Wykryto przeprawę promową OFICJALNIE przez COMBINED_TRANSPORT_EVENTS: "
                    f"{ct_info['ferry_names']}"
                )
                result['detected'] = True
                result['method'] = 'official'
                result['ferry_info'] = ct_info
                return result
        
        # === STRATEGIA 2: Fallback heurystyczny ===
        # Używana gdy API nie zwróciło COMBINED_TRANSPORT_EVENTS
        if not toll_data:
            return result
        
        # Pobierz kraje na trasie
        countries = set()
        if 'costs' in toll_data:
            for country in toll_data['costs'].get('countries', []):
                code = country.get('countryCode', '').upper()
                if code:
                    countries.add(code)
        
        # GB i kraj kontynentalny = przeprawa przez Kanał
        continental_countries = {'FR', 'BE', 'NL', 'DE'}
        has_gb = 'GB' in countries
        has_continental = bool(countries & continental_countries)
        
        if has_gb and has_continental:
            # Trasa GB <-> kontynent
            # Jeśli unikamy Eurotunelu, to MUSI być prom!
            if avoid_eurotunnel:
                logger.info(
                    f"Wykryto przeprawę promową HEURYSTYCZNIE przez analizę krajów "
                    f"(kraje: {countries}, avoid_eurotunnel={avoid_eurotunnel})"
                )
                result['detected'] = True
                result['method'] = 'heuristic'
                return result
            else:
                # Eurotunel dozwolony - nie wiemy czy to prom czy tunel
                logger.info(f"Trasa GB-kontynent, ale Eurotunel dozwolony - nie dodajemy kosztu promu")
                return result
        
        return result

    def process_toll_costs(self, toll_data, legs_data=None, avoid_eurotunnel=True, polyline_str=None, events_data=None):
        """
        Process toll costs from API response.
        
        Args:
            toll_data: Dane toll z odpowiedzi API
            legs_data: Dane legs z odpowiedzi API
            avoid_eurotunnel: Czy unikać Eurotunelu
            polyline_str: Polyline trasy (do obliczenia dystansu w GB)
            events_data: Eventy z odpowiedzi API (COMBINED_TRANSPORT_EVENTS)
        """
        result = {
            'total_cost': 0,
            'total_cost_by_country': {},
            'costs_by_type': {
                'ROAD': {'EUR': 0},
                'TUNNEL': {'EUR': 0},
                'BRIDGE': {'EUR': 0},
                'FERRY': {'EUR': 0}
            },
            'special_systems': [],  # Lista systemów specjalnych (tunele, mosty, promy)
            'has_channel_ferry': False  # Flaga przeprawy przez Kanał La Manche
        }
        
        if not toll_data:
            return result
        
        # DEBUG: Pełna struktura toll_data
        import json
        logger.info(f"🔍 DEBUG TOLL_DATA FULL STRUCTURE:\n{json.dumps(toll_data, indent=2, default=str)[:5000]}")
            
        total_cost = 0

        # Pobierz całkowity koszt i koszty według krajów
        if 'costs' in toll_data:
            total_cost = toll_data['costs'].get('convertedPrice', {}).get('price', 0)
            result['total_cost'] = total_cost
            
            # Koszty według krajów
            for country in toll_data['costs'].get('countries', []):
                code = country.get('countryCode')
                cost = country.get('convertedPrice', {}).get('price', 0)
                if code and cost is not None:
                    result['total_cost_by_country'][code] = cost

        # Analiza sekcji dla klasyfikacji kosztów
        road_toll = 0
        tunnel_toll = 0
        bridge_toll = 0
        ferry_toll = 0
        
        # Słownik do mapowania nazw systemów do kosztów z sekcji
        system_name_to_cost = {}

        # Najpierw sprawdź sekcje
        all_sections = toll_data.get('sections', [])
        logger.debug(f"📋 Liczba sekcji TOLL: {len(all_sections)}")
        ferry_sections_found = [s for s in all_sections if s.get('tollRoadType') == 'FERRY']
        if ferry_sections_found:
            logger.info(f"🚢 Znaleziono {len(ferry_sections_found)} sekcji typu FERRY w toll_data")
        
        for section in all_sections:
            section_cost = section.get('costs', [{}])[0].get('convertedPrice', {}).get('price', 0)
            section_type = section.get('tollRoadType', '').upper()
            # PTV API używa 'displayName' dla nazwy sekcji, nie 'name'
            section_name = section.get('displayName') or section.get('name')
            #print(f"DEBUG section: name='{section_name}', type='{section_type}', cost={section_cost}")
            
            if section_type == 'TUNNEL':
                tunnel_toll += section_cost
                # Zapisz koszt dla tuneli, nawet jeśli nie ma nazwy sekcji
                # Nazwa może być w systemach
                if section_cost > 0:
                    # Spróbuj znaleźć odpowiadający system na podstawie kosztu
                    for sys in toll_data.get('systems', []):
                        sys_name = sys.get('name', '')
                        if 'TUNNEL' in sys_name.upper() or 'MONT-BLANC' in sys_name.upper():
                            system_name_to_cost[sys_name] = section_cost
                            break
                # Dodaj tylko jeśli ma rzeczywistą nazwę
                if section_name:
                    system_name_to_cost[section_name] = section_cost
                    result['special_systems'].append({
                        'name': section_name,
                        'type': 'TUNNEL',
                        'cost': section_cost,
                        'operator': section.get('operatorName', '')
                    })
            elif section_type == 'BRIDGE':
                bridge_toll += section_cost
                # Zapisz koszt dla mostów, nawet jeśli nie ma nazwy sekcji
                if section_cost > 0:
                    for sys in toll_data.get('systems', []):
                        sys_name = sys.get('name', '')
                        if 'BRIDGE' in sys_name.upper():
                            system_name_to_cost[sys_name] = section_cost
                            break
                # Dodaj tylko jeśli ma rzeczywistą nazwę
                if section_name:
                    system_name_to_cost[section_name] = section_cost
                    result['special_systems'].append({
                        'name': section_name,
                        'type': 'BRIDGE',
                        'cost': section_cost,
                        'operator': section.get('operatorName', '')
                    })
            elif section_type == 'FERRY':
                ferry_toll += section_cost
                operator = section.get('operatorName', 'Unknown operator')
                
                # Loguj koszt promu
                if section_cost > 0:
                    logger.info(
                        f"💰 KOSZT PROMU (z TOLL_COSTS):\n"
                        f"   ├─ Nazwa: {section_name or 'Unnamed Ferry'}\n"
                        f"   ├─ Operator: {operator}\n"
                        f"   └─ Koszt: {section_cost:.2f} EUR"
                    )
                
                # Zapisz koszt dla promów, nawet jeśli nie ma nazwy sekcji
                if section_cost > 0:
                    for sys in toll_data.get('systems', []):
                        sys_name = sys.get('name', '')
                        if 'FERRY' in sys_name.upper():
                            system_name_to_cost[sys_name] = section_cost
                            break
                # Dodaj tylko jeśli ma rzeczywistą nazwę
                if section_name:
                    system_name_to_cost[section_name] = section_cost
                    result['special_systems'].append({
                        'name': section_name,
                        'type': 'FERRY',
                        'cost': section_cost,
                        'operator': operator
                    })
            else:
                road_toll += section_cost

        # Sprawdź systemy opłat - zawsze dla nazw, ale koszty tylko jeśli nie ma sekcji
        has_section_costs = (road_toll + tunnel_toll + bridge_toll + ferry_toll) > 0
        
        for system in toll_data.get('systems', []):
                system_cost = system.get('costs', {}).get('convertedPrice', {}).get('price', 0)
                system_name = system.get('name', '').upper()
                system_type = system.get('type', '').upper()
                operator_name = system.get('operatorName', '').upper()
                ##print(f"DEBUG system: name='{system.get('name')}', type='{system_type}', cost={system_cost}")
                print(f"DEBUG system: name='{system.get('name')}', type='{system_type}', cost={system_cost}")

                # Sprawdź czy system już został dodany z sekcji
                system_real_name = system.get('name')
                already_added = any(sys['name'] == system_real_name for sys in result['special_systems'])
                
                # Klasyfikacja na podstawie nazwy systemu i typu
                if 'TUNNEL' in system_name or 'TUNNEL' in system_type:
                    if not has_section_costs:  # Dodaj koszt tylko jeśli nie ma kosztów z sekcji
                        tunnel_toll += system_cost
                    # Dodaj informację o nazwie systemu tylko jeśli jeszcze nie został dodany
                    if system_real_name and not already_added:
                        # Użyj kosztu z mapowania jeśli dostępny, w przeciwnym razie koszt systemowy
                        display_cost = system_name_to_cost.get(system_real_name, system_cost)
                        print(f"DEBUG mapping: system_real_name='{system_real_name}', mapped_cost={system_name_to_cost.get(system_real_name)}, system_cost={system_cost}, display_cost={display_cost}")
                        result['special_systems'].append({
                            'name': system_real_name,
                            'type': 'TUNNEL',
                            'cost': display_cost,
                            'operator': system.get('operatorName', '')
                        })
                elif 'BRIDGE' in system_name or 'BRIDGE' in system_type:
                    if not has_section_costs:
                        bridge_toll += system_cost
                    # Dodaj informację o nazwie systemu tylko jeśli jeszcze nie został dodany
                    if system_real_name and not already_added:
                        display_cost = system_name_to_cost.get(system_real_name, system_cost)
                        result['special_systems'].append({
                            'name': system_real_name,
                            'type': 'BRIDGE',
                            'cost': display_cost,
                            'operator': system.get('operatorName', '')
                        })
                elif 'FERRY' in system_name or 'FERRY' in system_type:
                    if not has_section_costs:
                        ferry_toll += system_cost
                    # Dodaj informację o nazwie systemu tylko jeśli jeszcze nie został dodany
                    if system_real_name and not already_added:
                        display_cost = system_name_to_cost.get(system_real_name, system_cost)
                        result['special_systems'].append({
                            'name': system_real_name,
                            'type': 'FERRY',
                            'cost': display_cost,
                            'operator': system.get('operatorName', '')
                        })
                elif system_type in ["DISTANCE_BASED", "TIME_BASED", "SECTION_BASED"]:
                    if not has_section_costs:
                        road_toll += system_cost
                else:
                    # Jeśli typ nie jest znany, sprawdź znane systemy
                    if 'MONT-BLANC' in system_name or 'MONT BLANC' in system_name:
                        if not has_section_costs:
                            tunnel_toll += system_cost
                        # Dla Mont-Blanc zawsze dodaj informację o nazwie jeśli nie został już dodany
                        if not already_added:
                            final_name = system_real_name or 'Mont-Blanc Tunnel'
                            display_cost = system_name_to_cost.get(final_name, system_cost)
                            result['special_systems'].append({
                                'name': final_name,
                                'type': 'TUNNEL',
                                'cost': display_cost,
                                'operator': system.get('operatorName', '')
                            })
                    else:
                        if not has_section_costs:
                            road_toll += system_cost

        # Jeśli wciąż nie mamy kosztów, ale mamy całkowity koszt, spróbuj oszacować
        logger.info(f"🔍 DEBUG FALLBACK CHECK: road_toll={road_toll}, tunnel_toll={tunnel_toll}, bridge_toll={bridge_toll}, ferry_toll={ferry_toll}, total_cost={total_cost}")
        if (road_toll + tunnel_toll + bridge_toll + ferry_toll) == 0 and total_cost > 0:
            logger.info(f"🔍 DEBUG FALLBACK: Wchodzę do fallback, ustawiam road_toll={total_cost}")
            # Sprawdź znane systemy w danych
            for system in toll_data.get('systems', []):
                system_name = system.get('name', '').upper()
                if 'MONT-BLANC' in system_name or 'MONT BLANC' in system_name:
                    tunnel_toll = 333.42  # Znana stała cena za tunel Mont Blanc
                    road_toll = total_cost - tunnel_toll
                    break
            else:
                # Jeśli nie znaleziono znanych systemów, wszystko idzie do opłat drogowych
                road_toll = total_cost
                logger.info(f"🔍 DEBUG FALLBACK: road_toll ustawione na total_cost={total_cost}")

        # Wykryj przeprawę promową i dodaj koszt TYLKO gdy PTV API nie zwróciło żadnego (ferry_toll == 0)
        ferry_detection = self._detect_channel_ferry(toll_data, legs_data, avoid_eurotunnel, events_data)
        
        if ferry_detection['detected'] and ferry_toll == 0:
            result['has_channel_ferry'] = True
            detection_method = ferry_detection['method']
            ferry_info = ferry_detection.get('ferry_info')
            
            if detection_method == 'official' and ferry_info and ferry_info.get('ferry_names'):
                # Oficjalne wykrycie - użyj nazwy z API i znajdź koszt w słowniku
                ferry_name = ferry_info['ferry_names'][0] if ferry_info['ferry_names'] else 'Unknown Ferry'
                ferry_duration_min = ferry_info.get('total_ferry_duration', 0) / 60
                
                # Sprawdź czy prom jest w słowniku FERRY_COSTS
                if ferry_name in FERRY_COSTS:
                    ferry_cost = FERRY_COSTS[ferry_name]
                    cost_source = 'FERRY_COSTS dictionary'
                else:
                    ferry_cost = 200  # Fallback dla nieznanych promów
                    cost_source = 'fallback (unknown ferry)'
                    logger.warning(
                        f"⚠️  Prom '{ferry_name}' nie znaleziony w FERRY_COSTS! "
                        f"Używam fallback 200€. Rozważ dodanie tego promu do słownika."
                    )
                
                ferry_toll += ferry_cost
                total_cost += ferry_cost
                result['total_cost'] = total_cost
                
                result['special_systems'].append({
                    'name': ferry_name,
                    'type': 'FERRY',
                    'cost': ferry_cost,
                    'operator': 'Ferry Operator',
                    'detection_method': 'official',
                    'duration_minutes': ferry_duration_min,
                    'source': cost_source
                })
                logger.info(
                    f"Dodano koszt przeprawy promowej '{ferry_name}': {ferry_cost}€ "
                    f"(wykrycie: COMBINED_TRANSPORT_EVENTS, źródło ceny: {cost_source}, czas: {ferry_duration_min:.0f} min)"
                )
            else:
                # Heurystyczne wykrycie - zakładamy Dover-Calais dla GB↔FR/BE
                ferry_name = 'Dover-Calais'
                ferry_cost = FERRY_COSTS.get(ferry_name, 200)
                
                ferry_toll += ferry_cost
                total_cost += ferry_cost
                result['total_cost'] = total_cost
                
                result['special_systems'].append({
                    'name': ferry_name,
                    'type': 'FERRY',
                    'cost': ferry_cost,
                    'operator': 'Channel Ferry',
                    'detection_method': 'heuristic',
                    'source': 'FERRY_COSTS (heuristic)'
                })
                logger.info(
                    f"Dodano koszt przeprawy promowej '{ferry_name}': {ferry_cost}€ "
                    f"(wykrycie: HEURYSTYCZNE przez analizę krajów GB↔FR/BE, źródło ceny: FERRY_COSTS)"
                )
        elif ferry_detection['detected'] and ferry_toll > 0:
            logger.info(
                f"ℹ️  Prom wykryty przez COMBINED_TRANSPORT_EVENTS, "
                f"ale PTV API już zwróciło koszt promu ({ferry_toll:.2f}€), więc nie dodajemy własnego"
            )
        
        # Dodaj UK HGV Levy (dzienna winieta) jeśli trasa przechodzi przez GB
        uk_levy_days = self._calculate_uk_levy_days(toll_data, legs_data, polyline_str)
        if uk_levy_days > 0:
            uk_levy_cost = uk_levy_days * UK_HGV_LEVY_DAILY_EUR
            road_toll += uk_levy_cost
            total_cost += uk_levy_cost
            result['total_cost'] = total_cost
            
            # Dodaj informację o winiecie UK do total_cost_by_country
            if 'GB' in result['total_cost_by_country']:
                result['total_cost_by_country']['GB'] += uk_levy_cost
            else:
                result['total_cost_by_country']['GB'] = uk_levy_cost
            
            # Dodaj UK Levy do special_systems
            result['special_systems'].append({
                'name': f'UK HGV Levy ({uk_levy_days} dzień/dni)',
                'type': 'ROAD',
                'cost': uk_levy_cost,
                'operator': 'UK Government'
            })
            logger.info(f"Dodano UK HGV Levy: {uk_levy_days} dzień/dni × {UK_HGV_LEVY_DAILY_EUR}€ = {uk_levy_cost}€")
        
        # Zapisz wyniki
        result['costs_by_type']['ROAD']['EUR'] = road_toll
        result['costs_by_type']['TUNNEL']['EUR'] = tunnel_toll
        result['costs_by_type']['BRIDGE']['EUR'] = bridge_toll
        result['costs_by_type']['FERRY']['EUR'] = ferry_toll
        
        # Podsumowanie promów (jeśli są jakieś na trasie)
        ferry_systems = [s for s in result['special_systems'] if s['type'] == 'FERRY']
        if ferry_systems:
            logger.info(
                f"\n{'='*70}\n"
                f"💰 PODSUMOWANIE KOSZTÓW PROMÓW:\n"
                f"   ├─ Liczba promów: {len(ferry_systems)}\n"
                f"   ├─ Łączny koszt: {ferry_toll:.2f} EUR\n"
                f"   └─ Szczegóły:"
            )
            for i, ferry in enumerate(ferry_systems, 1):
                operator = ferry.get('operator', 'Unknown')
                cost = ferry.get('cost', 0)
                duration = ferry.get('duration_minutes')
                duration_str = f", czas: {duration:.0f} min" if duration else ""
                logger.info(
                    f"      {i}. {ferry['name']} ({operator}): {cost:.2f} EUR{duration_str}"
                )
            logger.info(f"{'='*70}")
        
        return result

    def get_excel_formats(self, workbook):
        """Get Excel formats for different cell types"""
        formats = {
            'header': workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#D9D9D9'
            }),
            'number': workbook.add_format({
                'num_format': '0.00',
                'align': 'right'
            }),
            'cost': workbook.add_format({
                'num_format': '0.00 €',
                'align': 'right'
            }),
            'zero_cost': workbook.add_format({
                'num_format': '0.00 €',
                'align': 'right',
                'color': '#808080'  # szary kolor dla zerowych kosztów
            })
        }
        return formats

    def prepare_excel_header(self, worksheet, include_toll_costs=True):
        """Prepare Excel header with new cost breakdown columns"""
        formats = self.get_excel_formats(worksheet.book)
        headers = ['ID', 'Dystans [km]', 'Czas [h]']
        
        if include_toll_costs:
            headers.extend([
                'Opłaty drogowe [EUR]',
                'Koszt/km [EUR]',
                'Dodatkowe opłaty [EUR]',
                'w tym - Tunele [EUR]',
                'w tym - Mosty [EUR]',
                'w tym - Promy [EUR]',
                'Suma kosztów [EUR]'
            ])
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, formats['header'])
            worksheet.set_column(col, col, len(header) + 2)
        
        return worksheet

    def process_route_result(self, route_result, worksheet, row, include_toll_costs=True):
        """Process single route result and write to worksheet"""
        if not route_result or 'error' in route_result:
            return row

        # Existing distance and time calculations
        distance = route_result.get('distance', 0) / 1000  # km
        travel_time = route_result.get('travelTime', 0) / 3600  # hours

        # Process toll costs with new breakdown
        toll_info = self.process_toll_costs(route_result.get('toll', {}))
        total_cost = toll_info['total_cost']
        costs_by_type = toll_info['costs_by_type']
        
        # Rozdzielenie kosztów
        road_cost = costs_by_type['ROAD']['EUR']
        tunnel_cost = costs_by_type['TUNNEL']['EUR']
        bridge_cost = costs_by_type['BRIDGE']['EUR']
        ferry_cost = costs_by_type['FERRY']['EUR']
        
        # Suma kosztów specjalnych
        special_costs = tunnel_cost + bridge_cost + ferry_cost
        
        # Obliczenie kosztu na km (tylko z opłat drogowych)
        cost_per_km = road_cost / distance if distance > 0 else 0

        # Update Excel columns
        formats = self.get_excel_formats(worksheet.book)
        col = 0
        
        # ID
        worksheet.write(row, col, row)
        col += 1
        
        # Dystans
        worksheet.write(row, col, distance, formats['number'])
        col += 1
        
        # Czas
        worksheet.write(row, col, travel_time, formats['number'])
        col += 1
        
        if include_toll_costs:
            # Opłaty drogowe
            worksheet.write(row, col, road_cost, formats['cost'])
            col += 1
            
            # Koszt na km (tylko z opłat drogowych)
            worksheet.write(row, col, cost_per_km, formats['cost'])
            col += 1
            
            # Dodatkowe opłaty (suma tuneli, mostów, promów)
            worksheet.write(row, col, special_costs, formats['cost'])
            col += 1
            
            # Szczegóły dodatkowych opłat
            worksheet.write(row, col, tunnel_cost, formats['cost'])
            col += 1
            worksheet.write(row, col, bridge_cost, formats['cost'])
            col += 1
            worksheet.write(row, col, ferry_cost, formats['cost'])
            col += 1
            
            # Suma wszystkich kosztów
            worksheet.write(row, col, total_cost, formats['cost'])
            col += 1

        return row + 1 