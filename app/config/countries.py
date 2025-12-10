"""
Mapowania krajów i kodów ISO.

Zawiera słowniki do konwersji między różnymi formatami nazw krajów.
"""

# Słownik kodów ISO krajów (nazwa angielska -> kod ISO)
ISO_CODES = {
    "Poland": "pl",
    "Germany": "de",
    "France": "fr",
    "Italy": "it",
    "Spain": "es",
    "Netherlands": "nl",
    "Belgium": "be",
    "Czech Republic": "cz",
    "Austria": "at",
    "Slovakia": "sk",
    "Slovenia": "si",
    "Hungary": "hu",
    "Portugal": "pt",
    "Greece": "gr",
    "Switzerland": "ch",
    "Sweden": "se",
    "Finland": "fi",
    "Norway": "no",
    "Denmark": "dk",
    "Luxembourg": "lu"
}

# Mapowanie krajów – ujednolicone nazwy (różne formaty -> pełna nazwa angielska)
COUNTRY_MAPPING = {
    # Kody ISO -> pełne nazwy
    'PL': 'Poland', 'Polska': 'Poland',
    'DE': 'Germany', 'Niemcy': 'Germany',
    'FR': 'France', 'Francja': 'France',
    'IT': 'Italy', 'Włochy': 'Italy',
    'ES': 'Spain', 'Hiszpania': 'Spain',
    'NL': 'Netherlands', 'Holandia': 'Netherlands',
    'BE': 'Belgium', 'Belgia': 'Belgium',
    'CZ': 'Czech Republic', 'Czechy': 'Czech Republic',
    'AT': 'Austria', 'Austria': 'Austria',
    'SK': 'Slovakia', 'Słowacja': 'Slovakia',
    'SI': 'Slovenia', 'Słowenia': 'Slovenia',
    'HU': 'Hungary', 'Węgry': 'Hungary',
    'PT': 'Portugal', 'Portugalia': 'Portugal',
    'GR': 'Greece', 'Grecja': 'Greece',
    'CH': 'Switzerland', 'Szwajcaria': 'Switzerland',
    'SE': 'Sweden', 'Szwecja': 'Sweden',
    'FI': 'Finland', 'Finlandia': 'Finland',
    'NO': 'Norway', 'Norwegia': 'Norway',
    'DK': 'Denmark', 'Dania': 'Denmark',
    'BG': 'Bulgaria', 'Bułgaria': 'Bulgaria',
    'EE': 'Estonia', 'Estonia': 'Estonia',
    'HR': 'Croatia', 'Chorwacja': 'Croatia',
    'IE': 'Ireland', 'Irlandia': 'Ireland',
    'LT': 'Lithuania', 'Litwa': 'Lithuania',
    'LV': 'Latvia', 'Łotwa': 'Latvia',
    'RO': 'Romania', 'Rumunia': 'Romania',
    'GB': 'United Kingdom', 'UK': 'United Kingdom', 'Wielka Brytania': 'United Kingdom',
    'Great Britain': 'United Kingdom', 'England': 'United Kingdom',
    'LU': 'Luxembourg', 'Luksemburg': 'Luxembourg'
}

# Mapowanie pełnych nazw krajów -> kody ISO (dla waypoints)
# Używane do konwersji nazw krajów wprowadzonych przez użytkownika
COUNTRY_TO_ISO = {
    'POLAND': 'PL', 'POLSKA': 'PL',
    'GERMANY': 'DE', 'NIEMCY': 'DE',
    'FRANCE': 'FR', 'FRANCJA': 'FR',
    'ITALY': 'IT', 'WŁOCHY': 'IT', 'WLOCHY': 'IT',
    'SPAIN': 'ES', 'HISZPANIA': 'ES',
    'NETHERLANDS': 'NL', 'HOLANDIA': 'NL',
    'BELGIUM': 'BE', 'BELGIA': 'BE',
    'CZECH REPUBLIC': 'CZ', 'CZECHY': 'CZ',
    'AUSTRIA': 'AT',
    'SLOVAKIA': 'SK', 'SŁOWACJA': 'SK', 'SLOWACJA': 'SK',
    'SLOVENIA': 'SI', 'SŁOWENIA': 'SI', 'SLOWENIA': 'SI',
    'HUNGARY': 'HU', 'WĘGRY': 'HU', 'WEGRY': 'HU',
    'PORTUGAL': 'PT', 'PORTUGALIA': 'PT',
    'GREECE': 'GR', 'GRECJA': 'GR',
    'SWITZERLAND': 'CH', 'SZWAJCARIA': 'CH',
    'SWEDEN': 'SE', 'SZWECJA': 'SE',
    'FINLAND': 'FI', 'FINLANDIA': 'FI',
    'NORWAY': 'NO', 'NORWEGIA': 'NO',
    'DENMARK': 'DK', 'DANIA': 'DK',
    'BULGARIA': 'BG', 'BUŁGARIA': 'BG',
    'ESTONIA': 'EE',
    'CROATIA': 'HR', 'CHORWACJA': 'HR',
    'IRELAND': 'IE', 'IRLANDIA': 'IE',
    'LITHUANIA': 'LT', 'LITWA': 'LT',
    'LATVIA': 'LV', 'ŁOTWA': 'LV', 'LOTWA': 'LV',
    'ROMANIA': 'RO', 'RUMUNIA': 'RO',
    'UNITED KINGDOM': 'GB', 'WIELKA BRYTANIA': 'GB', 'UK': 'GB', 'GB': 'GB',
    'GREAT BRITAIN': 'GB', 'ENGLAND': 'GB', 'ANGLIA': 'GB',
    'SCOTLAND': 'GB', 'SZKOCJA': 'GB', 'WALES': 'GB', 'WALIA': 'GB',
    'LUXEMBOURG': 'LU', 'LUKSEMBURG': 'LU'
}


def normalize_country(country: str) -> str:
    """
    Normalizuje nazwę kraju do pełnej angielskiej nazwy.
    
    Args:
        country: Nazwa kraju w dowolnym formacie (kod ISO, polska nazwa, angielska nazwa)
    
    Returns:
        Pełna angielska nazwa kraju lub oryginalna wartość jeśli nie znaleziono mapowania
    """
    return COUNTRY_MAPPING.get(str(country).strip(), str(country).strip())


def get_iso_code(country: str) -> str:
    """
    Pobiera kod ISO dla podanej nazwy kraju.
    
    Args:
        country: Nazwa kraju (może być w różnych formatach)
    
    Returns:
        Dwuliterowy kod ISO kraju (uppercase) lub oryginalna wartość
    """
    country_upper = str(country).strip().upper()
    
    # Jeśli już jest kodem ISO (2 litery)
    if len(country_upper) == 2 and country_upper.isalpha():
        return country_upper
    
    # Szukaj w mapowaniu
    return COUNTRY_TO_ISO.get(country_upper, country_upper)

