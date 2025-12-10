"""
Wyjątki aplikacji.

Zawiera niestandardowe klasy wyjątków używane w całej aplikacji.
"""


class GeocodeException(Exception):
    """
    Wyjątek sygnalizujący potrzebę ręcznego geokodowania.
    
    Rzucany gdy automatyczne geokodowanie nie może znaleźć
    współrzędnych dla podanej lokalizacji.
    
    Attributes:
        ungeocoded_locations: Lista lokalizacji, które nie zostały zgeokodowane
    """

    def __init__(self, ungeocoded_locations):
        self.ungeocoded_locations = ungeocoded_locations
        super().__init__("Znaleziono nierozpoznane lokalizacje")


class LocationVerificationRequired(Exception):
    """
    Wyjątek sygnalizujący potrzebę weryfikacji lokalizacji przez użytkownika.
    
    Rzucany gdy geokodowanie zwróciło wyniki, ale wymagają one
    potwierdzenia przez użytkownika (np. niejednoznaczne dopasowanie).
    
    Attributes:
        locations_to_verify: Lista lokalizacji wymagających weryfikacji
    """

    def __init__(self, locations_to_verify):
        self.locations_to_verify = locations_to_verify
        super().__init__("Znaleziono lokalizacje wymagające weryfikacji")

