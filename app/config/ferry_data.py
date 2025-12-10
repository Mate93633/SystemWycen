"""
Dane promów i połączeń morskich.

Zawiera koszty promów, dystanse morskie oraz obowiązkowe trasy promowe
dla kalkulacji kosztów transportu międzynarodowego.
"""

from typing import Dict, Tuple, Any

# UK HGV Road User Levy - dzienna winieta dla ciężarówek >38t, Euro VI (w EUR)
# Źródło: UK Government HGV Levy rates 2024/2025 - £9.69/dzień ≈ 11€
UK_HGV_LEVY_DAILY_EUR = 11.0

# =============================================================================
# KOSZTY PROMÓW (w EUR)
# =============================================================================
# Na podstawie faktycznych danych z promy.csv (2024/2025)
# Ceny dla ciężarówek 40t - zaktualizowane na podstawie historii przejazdów

FERRY_COSTS: Dict[str, float] = {
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


# =============================================================================
# DYSTANSE MORSKIE PROMÓW (w km)
# =============================================================================
# Używane do odróżnienia dystansu "na kołach" od dystansu na promie
# Wartości są przybliżone na podstawie rzeczywistych tras morskich

FERRY_SEA_DISTANCES: Dict[str, float] = {
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


# =============================================================================
# OBOWIĄZKOWE TRASY PROMOWE
# =============================================================================
# Dla par krajów, gdzie prom jest jedyną opcją (np. wyspy, brak połączenia lądowego)
# Klucz: (kraj_początkowy, kraj_docelowy) - kody ISO 2-literowe
# Wartość: dict z informacjami o promie

FerryRouteInfo = Dict[str, Any]
MANDATORY_FERRY_ROUTES: Dict[Tuple[str, str], FerryRouteInfo] = {

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
    # FINLANDIA ↔ ESTONIA (brak połączenia lądowego - prom obowiązkowy)
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


# =============================================================================
# FUNKCJE POMOCNICZE
# =============================================================================

def is_ferry_mandatory(country_from: str, country_to: str) -> bool:
    """
    Sprawdza czy dla danej pary krajów prom jest obowiązkowy.
    
    Args:
        country_from: Kod kraju początkowego (np. 'GR', 'IT', 'GB')
        country_to: Kod kraju docelowego
        
    Returns:
        True jeśli prom jest obowiązkowy, False w przeciwnym razie
    """
    country_from = country_from.upper()
    country_to = country_to.upper()
    
    return (country_from, country_to) in MANDATORY_FERRY_ROUTES


def get_best_ferry_for_countries(country_from: str, country_to: str) -> FerryRouteInfo:
    """
    Zwraca najlepszą trasę promową dla pary krajów.
    
    Args:
        country_from: Kod kraju początkowego
        country_to: Kod kraju docelowego
        
    Returns:
        Słownik z informacjami o promie lub None jeśli brak trasy
    """
    country_from = country_from.upper()
    country_to = country_to.upper()
    
    return MANDATORY_FERRY_ROUTES.get((country_from, country_to))


def get_ferry_cost(ferry_name: str, fallback: float = 200.0) -> float:
    """
    Zwraca koszt promu po nazwie.
    
    Args:
        ferry_name: Nazwa promu (np. 'Dover-Calais')
        fallback: Wartość domyślna jeśli prom nie znaleziony
        
    Returns:
        Koszt promu w EUR
    """
    return FERRY_COSTS.get(ferry_name, fallback)


def get_ferry_sea_distance(ferry_name: str, fallback: float = 0.0) -> float:
    """
    Zwraca dystans morski promu po nazwie.
    
    Args:
        ferry_name: Nazwa promu (np. 'Dover-Calais')
        fallback: Wartość domyślna jeśli prom nie znaleziony
        
    Returns:
        Dystans morski w km
    """
    return FERRY_SEA_DISTANCES.get(ferry_name, fallback)

