import pandas as pd
from flask import Flask, request, send_file, jsonify, render_template_string
import io
import time
import requests
from geopy.geocoders import Nominatim
import math
import threading
import concurrent.futures
from diskcache import Cache
import logging
import os
import joblib
import polyline
import json
from functools import wraps
import re
import unicodedata
from rapidfuzz import process, fuzz
import csv

# Globalny słownik lookup
LOOKUP_DICT = {}

# Nowa zmienna globalna - słownik mapujący (kod kraju, kod pocztowy) -> region
REGION_MAPPING = {}

# Globalne zmienne
PTV_API_KEY = "RVVfZmQ1YTcyY2E4ZjNiNDhmOTlhYjE5NjRmNGZhYTdlNTc6NGUyM2VhMmEtZTc2YS00YmVkLWIyMTMtZDc2YjE0NWZjZjE1"
DEFAULT_ROUTING_MODE = "FAST"  # Stały tryb wyznaczania trasy

# Inicjalizacja geolokatora
geolocator = Nominatim(user_agent="wycena_transportu", timeout=15)

# Inicjalizacja pamięci podręcznych
geo_cache = Cache("geo_cache")
route_cache = Cache("route_cache")

# Zmienne globalne do śledzenia postępu
PROGRESS = 0
RESULT_EXCEL = None
CURRENT_ROW = 0
TOTAL_ROWS = 0

GEOCODING_TOTAL = 0
LOCATIONS_TO_VERIFY = []
VERIFICATION_IN_PROGRESS = False
FILE_TO_PROCESS = None
PROCESSING_PARAMS = {}
GEOCODING_CURRENT = 0

# Mapowanie krajów – ujednolicone nazwy
COUNTRY_MAPPING = {
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
    'IE': 'Ireland', 'Irlandia': 'Ireland',  # Użyto "Irlandia" jako poprawnej wersji
    'LT': 'Lithuania', 'Litwa': 'Lithuania',
    'LV': 'Latvia', 'Łotwa': 'Latvia',
    'RO': 'Romania', 'Rumunia': 'Romania',
    'UK': 'United Kingdom', 'Wielka Brytania': 'United Kingdom'

}


# Definicja wyjątku
class GeocodeException(Exception):
    """Wyjątek sygnalizujący potrzebę ręcznego geokodowania."""

    def __init__(self, ungeocoded_locations):
        self.ungeocoded_locations = ungeocoded_locations
        super().__init__("Znaleziono nierozpoznane lokalizacje")


class LocationVerificationRequired(Exception):
    """Wyjątek sygnalizujący potrzebę weryfikacji lokalizacji przez użytkownika."""

    def __init__(self, locations_to_verify):
        self.locations_to_verify = locations_to_verify
        super().__init__("Znaleziono lokalizacje wymagające weryfikacji")


def normalize_country(country):
    return COUNTRY_MAPPING.get(str(country).strip(), str(country).strip())


# Funkcja wczytująca mapowania regionów
def load_region_mapping():
    global REGION_MAPPING

    region_data = """ 
    ('10', 'AT', 'AT WSCHÓD'),
('11', 'AT', 'AT WSCHÓD'),
('12', 'AT', 'AT WSCHÓD'),
('13', 'AT', 'AT WSCHÓD'),
('14', 'AT', 'AT WSCHÓD'),
('15', 'AT', 'AT WSCHÓD'),
('16', 'AT', 'AT WSCHÓD'),
('17', 'AT', 'AT WSCHÓD'),
('18', 'AT', 'AT WSCHÓD'),
('19', 'AT', 'AT WSCHÓD'),
('20', 'AT', 'AT WSCHÓD'),
('21', 'AT', 'AT WSCHÓD'),
('22', 'AT', 'AT WSCHÓD'),
('23', 'AT', 'AT WSCHÓD'),
('24', 'AT', 'AT WSCHÓD'),
('25', 'AT', 'AT WSCHÓD'),
('26', 'AT', 'AT WSCHÓD'),
('27', 'AT', 'AT WSCHÓD'),
('28', 'AT', 'AT WSCHÓD'),
('29', 'AT', 'AT WSCHÓD'),
('30', 'AT', 'AT WSCHÓD'),
('31', 'AT', 'AT WSCHÓD'),
('32', 'AT', 'AT WSCHÓD'),
('33', 'AT', 'AT WSCHÓD'),
('34', 'AT', 'AT WSCHÓD'),
('35', 'AT', 'AT WSCHÓD'),
('36', 'AT', 'AT WSCHÓD'),
('37', 'AT', 'AT WSCHÓD'),
('38', 'AT', 'AT WSCHÓD'),
('39', 'AT', 'AT WSCHÓD'),
('40', 'AT', 'AT WSCHÓD'),
('41', 'AT', 'AT WSCHÓD'),
('42', 'AT', 'AT WSCHÓD'),
('43', 'AT', 'AT WSCHÓD'),
('44', 'AT', 'AT WSCHÓD'),
('45', 'AT', 'AT WSCHÓD'),
('46', 'AT', 'AT WSCHÓD'),
('47', 'AT', 'AT WSCHÓD'),
('48', 'AT', 'AT WSCHÓD'),
('49', 'AT', 'AT WSCHÓD'),
('50', 'AT', 'AT WSCHÓD'),
('51', 'AT', 'AT WSCHÓD'),
('52', 'AT', 'AT WSCHÓD'),
('53', 'AT', 'AT WSCHÓD'),
('54', 'AT', 'AT WSCHÓD'),
('55', 'AT', 'AT WSCHÓD'),
('56', 'AT', 'AT WSCHÓD'),
('57', 'AT', 'AT WSCHÓD'),
('58', 'AT', 'AT WSCHÓD'),
('59', 'AT', 'AT WSCHÓD'),
('60', 'AT', 'AT ZACHÓD'),
('61', 'AT', 'AT ZACHÓD'),
('62', 'AT', 'AT ZACHÓD'),
('63', 'AT', 'AT ZACHÓD'),
('64', 'AT', 'AT ZACHÓD'),
('65', 'AT', 'AT ZACHÓD'),
('66', 'AT', 'AT ZACHÓD'),
('67', 'AT', 'AT ZACHÓD'),
('68', 'AT', 'AT ZACHÓD'),
('69', 'AT', 'AT ZACHÓD'),
('70', 'AT', 'AT WSCHÓD'),
('71', 'AT', 'AT WSCHÓD'),
('72', 'AT', 'AT WSCHÓD'),
('73', 'AT', 'AT WSCHÓD'),
('74', 'AT', 'AT WSCHÓD'),
('75', 'AT', 'AT WSCHÓD'),
('76', 'AT', 'AT WSCHÓD'),
('77', 'AT', 'AT WSCHÓD'),
('78', 'AT', 'AT WSCHÓD'),
('79', 'AT', 'AT WSCHÓD'),
('80', 'AT', 'AT WSCHÓD'),
('81', 'AT', 'AT WSCHÓD'),
('82', 'AT', 'AT WSCHÓD'),
('83', 'AT', 'AT WSCHÓD'),
('84', 'AT', 'AT WSCHÓD'),
('85', 'AT', 'AT WSCHÓD'),
('86', 'AT', 'AT WSCHÓD'),
('87', 'AT', 'AT WSCHÓD'),
('88', 'AT', 'AT WSCHÓD'),
('89', 'AT', 'AT WSCHÓD'),
('90', 'AT', 'AT WSCHÓD'),
('91', 'AT', 'AT WSCHÓD'),
('92', 'AT', 'AT WSCHÓD'),
('93', 'AT', 'AT WSCHÓD'),
('94', 'AT', 'AT WSCHÓD'),
('95', 'AT', 'AT WSCHÓD'),
('96', 'AT', 'AT WSCHÓD'),
('97', 'AT', 'AT WSCHÓD'),
('98', 'AT', 'AT WSCHÓD'),
('99', 'AT', 'AT WSCHÓD'),
(NULL, 'BE', 'BE'),
(NULL, 'BG', 'BG'),
(NULL, 'CH', 'CH'),
('10', 'CZ', 'CZ PÓŁNOC'),
('11', 'CZ', 'CZ PÓŁNOC'),
('12', 'CZ', 'CZ PÓŁNOC'),
('13', 'CZ', 'CZ PÓŁNOC'),
('14', 'CZ', 'CZ PÓŁNOC'),
('15', 'CZ', 'CZ PÓŁNOC'),
('16', 'CZ', 'CZ PÓŁNOC'),
('17', 'CZ', 'CZ PÓŁNOC'),
('18', 'CZ', 'CZ PÓŁNOC'),
('19', 'CZ', 'CZ PÓŁNOC'),
('20', 'CZ', 'CZ PÓŁNOC'),
('21', 'CZ', 'CZ PÓŁNOC'),
('22', 'CZ', 'CZ PÓŁNOC'),
('23', 'CZ', 'CZ PÓŁNOC'),
('24', 'CZ', 'CZ PÓŁNOC'),
('25', 'CZ', 'CZ PÓŁNOC'),
('26', 'CZ', 'CZ PÓŁNOC'),
('27', 'CZ', 'CZ PÓŁNOC'),
('28', 'CZ', 'CZ PÓŁNOC'),
('29', 'CZ', 'CZ PÓŁNOC'),
('30', 'CZ', 'CZ PÓŁNOC'),
('31', 'CZ', 'CZ PÓŁNOC'),
('32', 'CZ', 'CZ PÓŁNOC'),
('33', 'CZ', 'CZ PÓŁNOC'),
('34', 'CZ', 'CZ PÓŁNOC'),
('35', 'CZ', 'CZ PÓŁNOC'),
('36', 'CZ', 'CZ PÓŁNOC'),
('37', 'CZ', 'CZ POŁUDNIE'),
('38', 'CZ', 'CZ POŁUDNIE'),
('39', 'CZ', 'CZ PÓŁNOC'),
('40', 'CZ', 'CZ PÓŁNOC'),
('41', 'CZ', 'CZ PÓŁNOC'),
('42', 'CZ', 'CZ PÓŁNOC'),
('43', 'CZ', 'CZ PÓŁNOC'),
('44', 'CZ', 'CZ PÓŁNOC'),
('45', 'CZ', 'CZ PÓŁNOC'),
('46', 'CZ', 'CZ PÓŁNOC'),
('47', 'CZ', 'CZ PÓŁNOC'),
('48', 'CZ', 'CZ PÓŁNOC'),
('49', 'CZ', 'CZ PÓŁNOC'),
('50', 'CZ', 'CZ PÓŁNOC'),
('51', 'CZ', 'CZ PÓŁNOC'),
('52', 'CZ', 'CZ PÓŁNOC'),
('53', 'CZ', 'CZ PÓŁNOC'),
('54', 'CZ', 'CZ PÓŁNOC'),
('55', 'CZ', 'CZ PÓŁNOC'),
('56', 'CZ', 'CZ PÓŁNOC'),
('57', 'CZ', 'CZ PÓŁNOC'),
('58', 'CZ', 'CZ PÓŁNOC'),
('59', 'CZ', 'CZ PÓŁNOC'),
('60', 'CZ', 'CZ PÓŁNOC'),
('61', 'CZ', 'CZ PÓŁNOC'),
('62', 'CZ', 'CZ PÓŁNOC'),
('63', 'CZ', 'CZ PÓŁNOC'),
('64', 'CZ', 'CZ PÓŁNOC'),
('65', 'CZ', 'CZ PÓŁNOC'),
('66', 'CZ', 'CZ POŁUDNIE'),
('67', 'CZ', 'CZ POŁUDNIE'),
('68', 'CZ', 'CZ POŁUDNIE'),
('69', 'CZ', 'CZ POŁUDNIE'),
('70', 'CZ', 'CZ PÓŁNOC'),
('71', 'CZ', 'CZ PÓŁNOC'),
('72', 'CZ', 'CZ PÓŁNOC'),
('73', 'CZ', 'CZ PÓŁNOC'),
('74', 'CZ', 'CZ PÓŁNOC'),
('75', 'CZ', 'CZ PÓŁNOC'),
('76', 'CZ', 'CZ POŁUDNIE'),
('77', 'CZ', 'CZ POŁUDNIE'),
('78', 'CZ', 'CZ POŁUDNIE'),
('79', 'CZ', 'CZ POŁUDNIE'),
('01', 'DE', 'DE0'),
('02', 'DE', 'DE0'),
('03', 'DE', 'DE0'),
('04', 'DE', 'DE0'),
('05', 'DE', 'DE0'),
('06', 'DE', 'DE0'),
('07', 'DE', 'DE0'),
('08', 'DE', 'DE0'),
('09', 'DE', 'DE0'),
('10', 'DE', 'DE1 POŁUDNIE'),
('11', 'DE', 'DE1 POŁUDNIE'),
('12', 'DE', 'DE1 POŁUDNIE'),
('13', 'DE', 'DE1 POŁUDNIE'),
('14', 'DE', 'DE1 POŁUDNIE'),
('15', 'DE', 'DE1 POŁUDNIE'),
('16', 'DE', 'DE1 POŁUDNIE'),
('17', 'DE', 'DE1 PÓŁNOC'),
('18', 'DE', 'DE1 PÓŁNOC'),
('19', 'DE', 'DE1 PÓŁNOC'),
('20', 'DE', 'DE2 POŁUDNIE'),
('21', 'DE', 'DE2 POŁUDNIE'),
('22', 'DE', 'DE2 POŁUDNIE'),
('23', 'DE', 'DE2 PÓŁNOC'),
('24', 'DE', 'DE2 PÓŁNOC'),
('25', 'DE', 'DE2 PÓŁNOC'),
('26', 'DE', 'DE2 POŁUDNIE'),
('27', 'DE', 'DE2 POŁUDNIE'),
('28', 'DE', 'DE2 POŁUDNIE'),
('29', 'DE', 'DE2 POŁUDNIE'),
('30', 'DE', 'DE3'),
('31', 'DE', 'DE3'),
('32', 'DE', 'DE3'),
('33', 'DE', 'DE3'),
('34', 'DE', 'DE3'),
('35', 'DE', 'DE3'),
('36', 'DE', 'DE3'),
('37', 'DE', 'DE3'),
('38', 'DE', 'DE3'),
('39', 'DE', 'DE3'),
('40', 'DE', 'DE4'),
('41', 'DE', 'DE4'),
('42', 'DE', 'DE4'),
('43', 'DE', 'DE4'),
('44', 'DE', 'DE4'),
('45', 'DE', 'DE4'),
('46', 'DE', 'DE4'),
('47', 'DE', 'DE4'),
('48', 'DE', 'DE4'),
('49', 'DE', 'DE4'),
('50', 'DE', 'DE5'),
('51', 'DE', 'DE5'),
('52', 'DE', 'DE5'),
('53', 'DE', 'DE5'),
('54', 'DE', 'DE5'),
('55', 'DE', 'DE5'),
('56', 'DE', 'DE5'),
('57', 'DE', 'DE5'),
('58', 'DE', 'DE5'),
('59', 'DE', 'DE5'),
('60', 'DE', 'DE6'),
('61', 'DE', 'DE6'),
('62', 'DE', 'DE6'),
('63', 'DE', 'DE6'),
('64', 'DE', 'DE6'),
('65', 'DE', 'DE6'),
('66', 'DE', 'DE6'),
('67', 'DE', 'DE6'),
('68', 'DE', 'DE6'),
('69', 'DE', 'DE6'),
('70', 'DE', 'DE7 PÓŁNOC'),
('71', 'DE', 'DE7 PÓŁNOC'),
('72', 'DE', 'DE7 PÓŁNOC'),
('73', 'DE', 'DE7 PÓŁNOC'),
('74', 'DE', 'DE7 PÓŁNOC'),
('75', 'DE', 'DE7 PÓŁNOC'),
('76', 'DE', 'DE7 PÓŁNOC'),
('77', 'DE', 'DE7 POŁUDNIE'),
('78', 'DE', 'DE7 POŁUDNIE'),
('79', 'DE', 'DE7 POŁUDNIE'),
('80', 'DE', 'DE8 PÓŁNOC'),
('81', 'DE', 'DE8 PÓŁNOC'),
('82', 'DE', 'DE8 PÓŁNOC'),
('83', 'DE', 'DE8 POŁUDNIE'),
('84', 'DE', 'DE8 PÓŁNOC'),
('85', 'DE', 'DE8 PÓŁNOC'),
('86', 'DE', 'DE8 PÓŁNOC'),
('87', 'DE', 'DE8 POŁUDNIE'),
('88', 'DE', 'DE8 POŁUDNIE'),
('89', 'DE', 'DE8 PÓŁNOC'),
('90', 'DE', 'DE9 PÓŁNOC'),
('91', 'DE', 'DE9 PÓŁNOC'),
('92', 'DE', 'DE9 PÓŁNOC'),
('93', 'DE', 'DE9 POŁUDNIE'),
('94', 'DE', 'DE9 POŁUDNIE'),
('95', 'DE', 'DE9 PÓŁNOC'),
('96', 'DE', 'DE9 PÓŁNOC'),
('97', 'DE', 'DE9 PÓŁNOC'),
('98', 'DE', 'DE9 PÓŁNOC'),
('99', 'DE', 'DE9 PÓŁNOC'),
(NULL, 'DK', 'DK'),
(NULL, 'EE', 'EE'),
('01', 'ES', 'ES PÓŁNOC'),
('02', 'ES', 'ES CENTRUM'),
('03', 'ES', 'ES POŁUDNIE'),
('04', 'ES', 'ES POŁUDNIE'),
('05', 'ES', 'ES CENTRUM'),
('06', 'ES', 'ES POŁUDNIE'),
('08', 'ES', 'ES PÓŁNOC'),
('09', 'ES', 'ES PÓŁNOC'),
('10', 'ES', 'ES POŁUDNIE'),
('11', 'ES', 'ES POŁUDNIE'),
('12', 'ES', 'ES CENTRUM'),
('13', 'ES', 'ES CENTRUM'),
('14', 'ES', 'ES POŁUDNIE'),
('15', 'ES', 'ES POŁUDNIE'),
('16', 'ES', 'ES CENTRUM'),
('17', 'ES', 'ES PÓŁNOC'),
('18', 'ES', 'ES POŁUDNIE'),
('19', 'ES', 'ES CENTRUM'),
('20', 'ES', 'ES PÓŁNOC'),
('21', 'ES', 'ES POŁUDNIE'),
('22', 'ES', 'ES PÓŁNOC'),
('23', 'ES', 'ES POŁUDNIE'),
('24', 'ES', 'ES PÓŁNOC'),
('25', 'ES', 'ES PÓŁNOC'),
('26', 'ES', 'ES PÓŁNOC'),
('27', 'ES', 'ES POŁUDNIE'),
('28', 'ES', 'ES CENTRUM'),
('29', 'ES', 'ES POŁUDNIE'),
('30', 'ES', 'ES POŁUDNIE'),
('31', 'ES', 'ES PÓŁNOC'),
('32', 'ES', 'ES POŁUDNIE'),
('33', 'ES', 'ES PÓŁNOC'),
('34', 'ES', 'ES PÓŁNOC'),
('35', 'ES', 'ES POŁUDNIE'),
('36', 'ES', 'ES POŁUDNIE'),
('37', 'ES', 'ES POŁUDNIE'),
('38', 'ES', 'ES POŁUDNIE'),
('39', 'ES', 'ES PÓŁNOC'),
('40', 'ES', 'ES CENTRUM'),
('41', 'ES', 'ES POŁUDNIE'),
('42', 'ES', 'ES PÓŁNOC'),
('43', 'ES', 'ES PÓŁNOC'),
('44', 'ES', 'ES CENTRUM'),
('45', 'ES', 'ES CENTRUM'),
('46', 'ES', 'ES CENTRUM'),
('47', 'ES', 'ES CENTRUM'),
('48', 'ES', 'ES PÓŁNOC'),
('49', 'ES', 'ES POŁUDNIE'),
('50', 'ES', 'ES PÓŁNOC'),
('52', 'ES', 'ES POŁUDNIE'),
(NULL, 'FI', 'FI'),
('01', 'FR', 'FR WSCHÓD'),
('02', 'FR', 'FR PÓŁNOC'),
('03', 'FR', 'FR WSCHÓD'),
('04', 'FR', 'FR POŁUDNIE'),
('05', 'FR', 'FR WSCHÓD'),
('06', 'FR', 'FR POŁUDNIE'),
('07', 'FR', 'FR WSCHÓD'),
('08', 'FR', 'FR PÓŁNOC'),
('09', 'FR', 'FR POŁUDNIE'),
('10', 'FR', 'FR WSCHÓD'),
('11', 'FR', 'FR POŁUDNIE'),
('12', 'FR', 'FR POŁUDNIE'),
('13', 'FR', 'FR POŁUDNIE'),
('14', 'FR', 'FR ZACHÓD'),
('15', 'FR', 'FR WSCHÓD'),
('16', 'FR', 'FR ZACHÓD'),
('17', 'FR', 'FR ZACHÓD'),
('18', 'FR', 'FR CENTRUM'),
('19', 'FR', 'FR ZACHÓD'),
('20', 'FR', 'FR POŁUDNIE'),
('21', 'FR', 'FR WSCHÓD'),
('22', 'FR', 'FR ZACHÓD'),
('23', 'FR', 'FR ZACHÓD'),
('24', 'FR', 'FR ZACHÓD'),
('25', 'FR', 'FR WSCHÓD'),
('26', 'FR', 'FR WSCHÓD'),
('27', 'FR', 'FR ZACHÓD'),
('28', 'FR', 'FR CENTRUM'),
('29', 'FR', 'FR ZACHÓD'),
('30', 'FR', 'FR POŁUDNIE'),
('31', 'FR', 'FR POŁUDNIE'),
('32', 'FR', 'FR POŁUDNIE'),
('33', 'FR', 'FR ZACHÓD'),
('34', 'FR', 'FR POŁUDNIE'),
('35', 'FR', 'FR ZACHÓD'),
('36', 'FR', 'FR CENTRUM'),
('37', 'FR', 'FR CENTRUM'),
('38', 'FR', 'FR WSCHÓD'),
('39', 'FR', 'FR WSCHÓD'),
('40', 'FR', 'FR POŁUDNIE'),
('41', 'FR', 'FR CENTRUM'),
('42', 'FR', 'FR WSCHÓD'),
('43', 'FR', 'FR WSCHÓD'),
('44', 'FR', 'FR ZACHÓD'),
('45', 'FR', 'FR CENTRUM'),
('46', 'FR', 'FR POŁUDNIE'),
('47', 'FR', 'FR POŁUDNIE'),
('48', 'FR', 'FR POŁUDNIE'),
('49', 'FR', 'FR ZACHÓD'),
('50', 'FR', 'FR ZACHÓD'),
('51', 'FR', 'FR PÓŁNOC'),
('52', 'FR', 'FR WSCHÓD'),
('53', 'FR', 'FR ZACHÓD'),
('54', 'FR', 'FR PÓŁNOC'),
('55', 'FR', 'FR PÓŁNOC'),
('56', 'FR', 'FR ZACHÓD'),
('57', 'FR', 'FR PÓŁNOC'),
('58', 'FR', 'FR CENTRUM'),
('59', 'FR', 'FR PÓŁNOC'),
('60', 'FR', 'FR PÓŁNOC'),
('61', 'FR', 'FR ZACHÓD'),
('62', 'FR', 'FR PÓŁNOC'),
('63', 'FR', 'FR WSCHÓD'),
('64', 'FR', 'FR POŁUDNIE'),
('65', 'FR', 'FR POŁUDNIE'),
('66', 'FR', 'FR POŁUDNIE'),
('67', 'FR', 'FR WSCHÓD'),
('68', 'FR', 'FR WSCHÓD'),
('69', 'FR', 'FR WSCHÓD'),
('70', 'FR', 'FR WSCHÓD'),
('71', 'FR', 'FR WSCHÓD'),
('72', 'FR', 'FR ZACHÓD'),
('73', 'FR', 'FR WSCHÓD'),
('74', 'FR', 'FR WSCHÓD'),
('75', 'FR', 'FR CENTRUM'),
('76', 'FR', 'FR PÓŁNOC'),
('77', 'FR', 'FR CENTRUM'),
('78', 'FR', 'FR CENTRUM'),
('79', 'FR', 'FR ZACHÓD'),
('80', 'FR', 'FR PÓŁNOC'),
('81', 'FR', 'FR POŁUDNIE'),
('82', 'FR', 'FR POŁUDNIE'),
('83', 'FR', 'FR POŁUDNIE'),
('84', 'FR', 'FR POŁUDNIE'),
('85', 'FR', 'FR ZACHÓD'),
('86', 'FR', 'FR ZACHÓD'),
('87', 'FR', 'FR ZACHÓD'),
('88', 'FR', 'FR WSCHÓD'),
('89', 'FR', 'FR CENTRUM'),
('90', 'FR', 'FR WSCHÓD'),
('91', 'FR', 'FR CENTRUM'),
('92', 'FR', 'FR CENTRUM'),
('93', 'FR', 'FR CENTRUM'),
('94', 'FR', 'FR CENTRUM'),
('95', 'FR', 'FR CENTRUM'),
('98', 'FR', 'FR POŁUDNIE'),
('AB', 'GB', 'GB PÓŁNOC'),
('AL', 'GB', 'GB POŁUDNIE'),
('B', 'GB', 'GB CENTRUM'),
('B1', 'GB', 'GB CENTRUM'),
('B2', 'GB', 'GB CENTRUM'),
('B4', 'GB', 'GB CENTRUM'),
('B7', 'GB', 'GB CENTRUM'),
('B9', 'GB', 'GB CENTRUM'),
('BA', 'GB', 'GB CENTRUM'),
('BB', 'GB', 'GB CENTRUM'),
('BD', 'GB', 'GB CENTRUM'),
('BH', 'GB', 'GB CENTRUM'),
('BL', 'GB', 'GB CENTRUM'),
('BN', 'GB', 'GB POŁUDNIE'),
('BR', 'GB', 'GB POŁUDNIE'),
('BS', 'GB', 'GB CENTRUM'),
('CA', 'GB', 'GB PÓŁNOC'),
('CB', 'GB', 'GB POŁUDNIE'),
('CF', 'GB', 'GB CENTRUM'),
('CH', 'GB', 'GB CENTRUM'),
('CM', 'GB', 'GB POŁUDNIE'),
('CO', 'GB', 'GB POŁUDNIE'),
('CR', 'GB', 'GB POŁUDNIE'),
('CT', 'GB', 'GB POŁUDNIE'),
('CV', 'GB', 'GB CENTRUM'),
('CW', 'GB', 'GB CENTRUM'),
('DA', 'GB', 'GB POŁUDNIE'),
('DD', 'GB', 'GB PÓŁNOC'),
('DE', 'GB', 'GB CENTRUM'),
('DG', 'GB', 'GB PÓŁNOC'),
('DH', 'GB', 'GB PÓŁNOC'),
('DL', 'GB', 'GB CENTRUM'),
('DN', 'GB', 'GB CENTRUM'),
('DT', 'GB', 'GB CENTRUM'),
('DY', 'GB', 'GB CENTRUM'),
('E', 'GB', 'GB POŁUDNIE'),
('E1', 'GB', 'GB POŁUDNIE'),
('EC', 'GB', 'GB POŁUDNIE'),
('EH', 'GB', 'GB PÓŁNOC'),
('EN', 'GB', 'GB POŁUDNIE'),
('EX', 'GB', 'GB CENTRUM'),
('FK', 'GB', 'GB PÓŁNOC'),
('FY', 'GB', 'GB CENTRUM'),
('G', 'GB', 'GB PÓŁNOC'),
('G3', 'GB', 'GB PÓŁNOC'),
('G7', 'GB', 'GB PÓŁNOC'),
('GL', 'GB', 'GB CENTRUM'),
('GU', 'GB', 'GB POŁUDNIE'),
('HA', 'GB', 'GB POŁUDNIE'),
('HD', 'GB', 'GB CENTRUM'),
('HG', 'GB', 'GB CENTRUM'),
('HP', 'GB', 'GB POŁUDNIE'),
('HR', 'GB', 'GB CENTRUM'),
('HU', 'GB', 'GB CENTRUM'),
('HX', 'GB', 'GB CENTRUM'),
('IG', 'GB', 'GB POŁUDNIE'),
('IP', 'GB', 'GB POŁUDNIE'),
('IV', 'GB', 'GB PÓŁNOC'),
('KT', 'GB', 'GB POŁUDNIE'),
('KW', 'GB', 'GB PÓŁNOC'),
('KY', 'GB', 'GB PÓŁNOC'),
('L', 'GB', 'GB CENTRUM'),
('L2', 'GB', 'GB CENTRUM'),
('L3', 'GB', 'GB CENTRUM'),
('LA', 'GB', 'GB CENTRUM'),
('LD', 'GB', 'GB CENTRUM'),
('LE', 'GB', 'GB CENTRUM'),
('LL', 'GB', 'GB CENTRUM'),
('LN', 'GB', 'GB CENTRUM'),
('LS', 'GB', 'GB CENTRUM'),
('LU', 'GB', 'GB POŁUDNIE'),
('M', 'GB', 'GB CENTRUM'),
('M2', 'GB', 'GB CENTRUM'),
('M3', 'GB', 'GB CENTRUM'),
('M9', 'GB', 'GB CENTRUM'),
('ME', 'GB', 'GB POŁUDNIE'),
('MK', 'GB', 'GB CENTRUM'),
('ML', 'GB', 'GB PÓŁNOC'),
('N', 'GB', 'GB POŁUDNIE'),
('N1', 'GB', 'GB POŁUDNIE'),
('NE', 'GB', 'GB PÓŁNOC'),
('NG', 'GB', 'GB CENTRUM'),
('NN', 'GB', 'GB CENTRUM'),
('NP', 'GB', 'GB CENTRUM'),
('NR', 'GB', 'GB POŁUDNIE'),
('NW', 'GB', 'GB POŁUDNIE'),
('OL', 'GB', 'GB CENTRUM'),
('OX', 'GB', 'GB CENTRUM'),
('PA', 'GB', 'GB PÓŁNOC'),
('PE', 'GB', 'GB CENTRUM'),
('PH', 'GB', 'GB PÓŁNOC'),
('PL', 'GB', 'GB CENTRUM'),
('PO', 'GB', 'GB POŁUDNIE'),
('PR', 'GB', 'GB CENTRUM'),
('RG', 'GB', 'GB POŁUDNIE'),
('RH', 'GB', 'GB POŁUDNIE'),
('RM', 'GB', 'GB POŁUDNIE'),
('S', 'GB', 'GB CENTRUM'),
('S2', 'GB', 'GB CENTRUM'),
('S6', 'GB', 'GB CENTRUM'),
('S7', 'GB', 'GB CENTRUM'),
('SA', 'GB', 'GB CENTRUM'),
('SE', 'GB', 'GB POŁUDNIE'),
('SG', 'GB', 'GB POŁUDNIE'),
('SK', 'GB', 'GB CENTRUM'),
('SL', 'GB', 'GB POŁUDNIE'),
('SM', 'GB', 'GB POŁUDNIE'),
('SN', 'GB', 'GB CENTRUM'),
('SO', 'GB', 'GB POŁUDNIE'),
('SP', 'GB', 'GB CENTRUM'),
('SP', 'GB', 'GB CENTRUM'),
('SS', 'GB', 'GB POŁUDNIE'),
('ST', 'GB', 'GB CENTRUM'),
('SW', 'GB', 'GB POŁUDNIE'),
('SY', 'GB', 'GB CENTRUM'),
('TA', 'GB', 'GB CENTRUM'),
('TD', 'GB', 'GB PÓŁNOC'),
('TF', 'GB', 'GB CENTRUM'),
('TN', 'GB', 'GB POŁUDNIE'),
('TQ', 'GB', 'GB CENTRUM'),
('TR', 'GB', 'GB CENTRUM'),
('TS', 'GB', 'GB CENTRUM'),
('TW', 'GB', 'GB POŁUDNIE'),
('UB', 'GB', 'GB POŁUDNIE'),
('W', 'GB', 'GB POŁUDNIE'),
('WA', 'GB', 'GB CENTRUM'),
('WD', 'GB', 'GB POŁUDNIE'),
('WF', 'GB', 'GB CENTRUM'),
('WN', 'GB', 'GB CENTRUM'),
('WR', 'GB', 'GB CENTRUM'),
('WS', 'GB', 'GB CENTRUM'),
('WV', 'GB', 'GB CENTRUM'),
('YO', 'GB', 'GB CENTRUM'),
(NULL, 'GR', 'GR'),
(NULL, 'HR', 'HR'),
(NULL, 'HU', 'HU'),
(NULL, 'IE', 'IE'),
('0', 'IT', 'IT CENTRUM'),
('1', 'IT', 'IT CENTRUM'),
('2', 'IT', 'IT PÓŁNOC'),
('3', 'IT', 'IT PÓŁNOC'),
('4', 'IT', 'IT PÓŁNOC'),
('5', 'IT', 'IT CENTRUM'),
('6', 'IT', 'IT POŁUDNIE'),
('7', 'IT', 'IT POŁUDNIE'),
('8', 'IT', 'IT POŁUDNIE'),
('9', 'IT', 'IT POŁUDNIE'),
(NULL, 'LI', 'LI'),
(NULL, 'LU', 'LU'),
(NULL, 'MC', 'FR POŁUDNIE'),
(NULL, 'NL', 'NL'),
('0', 'PL', 'PL WSCHÓD'),
('1', 'PL', 'PL WSCHÓD'),
('2', 'PL', 'PL WSCHÓD'),
('3', 'PL', 'PL WSCHÓD'),
('4', 'PL', 'PL WSCHÓD'),
('5', 'PL', 'PL ZACHÓD'),
('6', 'PL', 'PL ZACHÓD'),
('7', 'PL', 'PL ZACHÓD'),
('8', 'PL', 'PL WSCHÓD'),
('9', 'PL', 'PL WSCHÓD'),
(NULL, 'PT', 'PT'),
(NULL, 'RO', 'RO'),
(NULL, 'SE', 'SE'),
('1', 'SI', 'SI ZACHÓD'),
('2', 'SI', 'SI WSCHÓD'),
('3', 'SI', 'SI WSCHÓD'),
('4', 'SI', 'SI ZACHÓD'),
('5', 'SI', 'SI ZACHÓD'),
('6', 'SI', 'SI ZACHÓD'),
('7', 'SI', 'SI WSCHÓD'),
('8', 'SI', 'SI WSCHÓD'),
('9', 'SI', 'SI WSCHÓD'),
(NULL, 'SK', 'SK'),
('M1', 'GB', 'GB CENTRUM'),
('L1', 'GB', 'GB CENTRUM'),
('L4', 'GB', 'GB CENTRUM'),
('W3', 'GB', 'GB POŁUDNIE'),
('G8', 'GB', 'GB PÓŁNOC'),
('N9', 'GB', 'GB POŁUDNIE'),
('WA', 'GB', 'GB CENTRUM'),
('G6', 'GB', 'GB PÓŁNOC')
    """

    # wyrażenie do złapania trójek (kod pocztowy, kod kraju, nazwa regionu)
    pattern = r"\('([^']*)',\s*'([^']*)',\s*'([^']*)'\)"
    matches = re.findall(pattern, region_data)

    for postal_code, country_code, region in matches:
        # null -> pusta stringa
        if postal_code.lower() == "null":
            postal_code = ""
        # normalizacja kraju tak, jak w normalize_country
        norm_country = normalize_country(country_code)
        # zapisujemy pod ujednoliconym kluczem
        REGION_MAPPING[(norm_country, postal_code)] = region

    print(f"Wczytano {len(REGION_MAPPING)} mapowań regionów.")

# Funkcja określająca region na podstawie kodu kraju i kodu pocztowego
def get_region(country, postal_code):
    postal_code = str(postal_code).strip()
    prefix2 = postal_code[:2] if len(postal_code) >= 2 else postal_code

    # 1) spróbuj dwu-cyfrowego
    region = REGION_MAPPING.get((country, prefix2))
    if region:
        return region

    # 2) spróbuj jednocyfrowego
    if len(postal_code) >= 1:
        prefix1 = postal_code[0]
        region = REGION_MAPPING.get((country, prefix1))
        if region:
            return region

    # 3) fallback na kraj-bez-prefixu
    return REGION_MAPPING.get((country, ""), None)


# Funkcja pobierająca stawki na podstawie relacji region-region
def get_region_based_rates(lc, lp, uc, up):
    """Pobiera stawki na podstawie relacji region–region oraz sumę zleceń."""
    # Określ regiony dla kodów pocztowych
    lc_region = get_region(normalize_country(lc), lp)
    uc_region = get_region(normalize_country(uc), up)

    if not lc_region or not uc_region:
        # Nie można określić regionów
        return {
            'region_gielda_stawka_3m': None,
            'region_gielda_stawka_6m': None,
            'region_gielda_stawka_12m': None,
            'region_klient_stawka_3m': None,
            'region_klient_stawka_6m': None,
            'region_klient_stawka_12m': None,
            'region_relacja': f"{lc_region or lc} - {uc_region or uc}",
            'region_dopasowanie': "Brak dopasowania regionalnego"
        }

    try:
        hist_df = pd.read_excel("historical_rates.xlsx",
                                dtype={'kod pocztowy zaladunku': str, 'kod pocztowy rozladunku': str})
        gielda_df = pd.read_excel("historical_rates_gielda.xlsx",
                                  dtype={'kod pocztowy zaladunku': str, 'kod pocztowy rozladunku': str})
    except Exception as e:
        return {
            'region_gielda_stawka_3m': None,
            'region_gielda_stawka_6m': None,
            'region_gielda_stawka_12m': None,
            'region_klient_stawka_3m': None,
            'region_klient_stawka_6m': None,
            'region_klient_stawka_12m': None,
            'region_relacja': f"{lc_region} - {uc_region}",
            'region_dopasowanie': f"Błąd: {e}"
        }

    # Dodaj kolumny regionów
    hist_df['region_zaladunku'] = hist_df.apply(
        lambda r: get_region(normalize_country(r['kraj zaladunku']), r['kod pocztowy zaladunku']), axis=1)
    hist_df['region_rozladunku'] = hist_df.apply(
        lambda r: get_region(normalize_country(r['kraj rozladunku']), r['kod pocztowy rozladunku']), axis=1)

    gielda_df['region_zaladunku'] = gielda_df.apply(
        lambda r: get_region(normalize_country(r['kraj zaladunku']), r['kod pocztowy zaladunku']), axis=1)
    gielda_df['region_rozladunku'] = gielda_df.apply(
        lambda r: get_region(normalize_country(r['kraj rozladunku']), r['kod pocztowy rozladunku']), axis=1)

    # Filtruj po regionach
    hist_matches = hist_df[
        (hist_df['region_zaladunku'] == lc_region) &
        (hist_df['region_rozladunku'] == uc_region)
    ]
    gielda_matches = gielda_df[
        (gielda_df['region_zaladunku'] == lc_region) &
        (gielda_df['region_rozladunku'] == uc_region)
    ]

    # Przygotuj wynik
    result = {
        'region_gielda_stawka_3m': None,
        'region_gielda_stawka_6m': None,
        'region_gielda_stawka_12m': None,
        'region_klient_stawka_3m': None,
        'region_klient_stawka_6m': None,
        'region_klient_stawka_12m': None,
        'region_relacja': f"{lc_region} - {uc_region}",
        'region_dopasowanie': "Brak dopasowań"
    }

    # --- Klient (historyczne) ---
    if not hist_matches.empty:
        # suma zleceń
        if 'Liczba zlecen' in hist_matches.columns:
            total_orders_hist = hist_matches['Liczba zlecen'].sum()
        else:
            total_orders_hist = len(hist_matches)
        result['region_dopasowanie'] = f"Dopasowano {total_orders_hist} zleceń (klient)"

        # średnie ważone stawek
        for period, col in [('3m', 'stawka_3m'), ('6m', 'stawka_6m'), ('12m', 'stawka_12m')]:
            if col in hist_matches.columns:
                valid = hist_matches.dropna(subset=[col])
                if not valid.empty:
                    if 'Liczba zlecen' in valid.columns:
                        orders = valid['Liczba zlecen'].sum()
                        weights = valid['Liczba zlecen'] / orders if orders else None
                    else:
                        weights = pd.Series(1 / len(valid), index=valid.index)
                    if weights is not None:
                        result[f'region_klient_stawka_{period}'] = (valid[col] * weights).sum()

    # --- Giełda ---
    if not gielda_matches.empty:
        # suma zleceń
        if 'Liczba zlecen' in gielda_matches.columns:
            total_orders_gielda = gielda_matches['Liczba zlecen'].sum()
        else:
            total_orders_gielda = len(gielda_matches)
        if result['region_dopasowanie'] == "Brak dopasowań":
            result['region_dopasowanie'] = f"Dopasowano {total_orders_gielda} zleceń (giełda)"
        else:
            result['region_dopasowanie'] += f", {total_orders_gielda} zleceń (giełda)"

        # średnie ważone stawek giełdowych
        for period, col in [('3m', 'stawka_3m'), ('6m', 'stawka_6m'), ('12m', 'stawka_12m')]:
            if col in gielda_matches.columns:
                valid = gielda_matches.dropna(subset=[col])
                if not valid.empty:
                    if 'Liczba zlecen' in valid.columns:
                        orders = valid['Liczba zlecen'].sum()
                        weights = valid['Liczba zlecen'] / orders if orders else None
                    else:
                        weights = pd.Series(1 / len(valid), index=valid.index)
                    if weights is not None:
                        result[f'region_gielda_stawka_{period}'] = (valid[col] * weights).sum()

    return result


# Funkcja wczytująca dane z global_data.csv – klucze tworzymy jako stringi, np. "Poland_36"
def load_global_data(filepath):
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=",")
        for row in reader:
            country_norm = normalize_country(row['country'].strip())
            prefix = row['prefix'].strip()
            try:
                lat = float(row['latitude'])
                lon = float(row['longitude'])
                key = f"{country_norm}_{prefix}"
                LOOKUP_DICT[key] = (lat, lon)
            except Exception as e:
                print("Błąd wczytywania rekordu:", row, e)
    print("Wczytany LOOKUP_DICT:", LOOKUP_DICT)


def sync_geo_cache_with_lookup():
    """Synchronizuje geo_cache z danymi z LOOKUP_DICT dla spójności."""
    print("Synchronizowanie geo_cache z LOOKUP_DICT...")
    synced_count = 0

    for key, (lat, lon) in LOOKUP_DICT.items():
        if key not in geo_cache or geo_cache[key][0] is None:
            geo_cache[key] = (lat, lon, 'lookup_sync', 'sync')
            synced_count += 1

    print(f"Zsynchronizowano {synced_count} wpisów z LOOKUP_DICT do geo_cache")
    return synced_count


# Na starcie aplikacji
load_global_data("global_data.csv")
sync_geo_cache_with_lookup()  # Synchronizuj cache


def clean_text(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text.lower().strip()


def get_geocoding_progress():
    if GEOCODING_TOTAL > 0:
        progress = int((GEOCODING_CURRENT / GEOCODING_TOTAL) * 100)
    else:
        progress = 0
    return f"Geokodowanie: {progress}%"


def generate_query_variants(country, postal_code, city=None):
    norm_country = normalize_country(country)
    norm_postal = str(postal_code).strip()
    variants = []
    # Dla dwucyfrowych kodów – pierwszy wariant to prosty: "Poland, 36" z kluczem "Poland_36"
    if len(norm_postal) == 2:
        variants.append((f"{norm_country}, {norm_postal}", f"{norm_country}_{norm_postal}"))
        if city and city.strip():
            norm_city = city.strip().title()
            clean_city = clean_text(norm_city)
            variants.append((f"{norm_country} postal code {norm_postal}, {norm_city}",
                             f"{norm_country}_postal_{norm_postal}_{clean_city}"))
        return variants
    else:
        if city and city.strip():
            norm_city = city.strip().title()
            clean_city = clean_text(norm_city)
            variants.append(
                (f"{norm_country}, {norm_postal}, {norm_city}", f"{norm_country}_{norm_postal}_{clean_city}"))
            variants.append(
                (f"{norm_city}, {norm_postal}, {norm_country}", f"{clean_city}_{norm_postal}_{norm_country}"))
            variants.append(
                (f"{norm_city}, {norm_country}, {norm_postal}", f"{clean_city}_{norm_country}_{norm_postal}"))
            variants.append((f"{norm_city}, {norm_country}", f"{clean_city}_{norm_country}"))
            variants.append((f"{norm_postal}, {norm_country}", f"{norm_country}_{norm_postal}"))
        else:
            variants.append((f"{norm_postal}, {norm_country}", f"{norm_country}_{norm_postal}"))
        return variants


def ptv_geocode_by_text(search_text, api_key, language="pl", country_code=None):
    endpoint = "https://api.myptv.com/geocoding/v1/locations/by-text"
    params = {
        "searchText": search_text,
        "apiKey": api_key,
        "language": language
    }

    # Dodaj parametr countryFilter, jeśli podano kod kraju
    if country_code:
        params["countryFilter"] = country_code.upper()

    print(
        f"PTV API: Wysyłam zapytanie: '{search_text}'" + (f" z filtrem kraju: {country_code}" if country_code else ""))
    try:
        response = requests.get(endpoint, params=params)
        time.sleep(0.1)
        if response.status_code == 200:
            data = response.json()
            if data.get("locations"):
                result = data["locations"][0]
                lat = result["referencePosition"]["latitude"]
                lon = result["referencePosition"]["longitude"]
                quality = result.get("locationType", "PTV_API")
                source = "PTV API"
                print(f"PTV API: Znaleziono wynik: {lat}, {lon}")
                return (lat, lon, quality, source)
            else:
                print(f"PTV API: Brak wyników dla '{search_text}'")
                return (None, None, 'nieznane', 'brak danych')
        else:
            print("PTV API błąd:", response.status_code, response.text)
            return (None, None, 'nieznane', 'błąd PTV API')
    except Exception as e:
        print("PTV API wyjątek:", e)
        return (None, None, 'nieznane', str(e))
def get_coordinates(country, postal_code, city=None):
    norm_postal = str(postal_code).strip()
    # Upewnij się, że city jest ciągiem znaków – jeśli nie, ustaw pusty ciąg
    if city is None or not hasattr(city, "strip") or city.strip() == "":
        city = ""
    else:
        try:
            city = str(city)
        except Exception:
            city = ""
    print(">>> get_coordinates wywołane dla:", country, norm_postal, city)

    norm_country = normalize_country(country)

    # Różne ścieżki dla dwucyfrowych i nie-dwucyfrowych kodów
    if len(norm_postal) == 2:
        # DLA KODÓW DWUCYFROWYCH - ZMIENIONA KOLEJNOŚĆ:
        # PTV API -> Nominatim (po LOOKUP_DICT, który był sprawdzany wcześniej)
        print("Priorytetowe sprawdzanie LOOKUP_DICT dla kodu dwucyfrowego")

        # Standardowy klucz
        key = f"{norm_country}_{norm_postal}"
        print(f"DEBUG: Sprawdzam klucz '{key}' w LOOKUP_DICT")

        # Najpierw sprawdzamy LOOKUP_DICT
        if key in LOOKUP_DICT:
            lat, lon = LOOKUP_DICT[key]
            result = (lat, lon, "lookup", "lookup")
            print(f"LOOKUP: Znaleziono współrzędne dla {key}: {result}")
            # Upewnij się, że wynik jest też w geo_cache
            geo_cache[key] = result
            return result

        # Jeśli nie znaleziono, próbujemy z dodatkowymi formatami klucza
        potential_keys = [
            f"{norm_country}_{norm_postal.zfill(2)}",  # z dodanym zerem
            f"{norm_country}_{norm_postal.lstrip('0')}",  # bez zer wiodących
        ]

        for alt_key in potential_keys:
            print(f"DEBUG: Sprawdzam alternatywny klucz '{alt_key}' w LOOKUP_DICT")
            if alt_key in LOOKUP_DICT:
                lat, lon = LOOKUP_DICT[alt_key]
                result = (lat, lon, "lookup", "lookup")
                print(f"LOOKUP: Znaleziono współrzędne dla {alt_key}: {result}")
                # Zapisz wynik pod standardowym kluczem także
                geo_cache[key] = result
                return result

        # Jeśli nadal nie znaleziono, próbujemy z częściowym dopasowaniem
        for db_key in LOOKUP_DICT:
            if db_key.startswith(f"{norm_country}_") and norm_postal in db_key:
                lat, lon = LOOKUP_DICT[db_key]
                result = (lat, lon, "lookup (częściowe dopasowanie)", "lookup")
                print(f"LOOKUP (częściowe): Znaleziono współrzędne dla {db_key}: {result}")
                # Zapisz wynik pod standardowym kluczem także
                geo_cache[key] = result
                return result

        # Jeśli w LOOKUP_DICT nie znaleziono, przechodzimy do standardowych metod geokodowania
        query_variants = [(f"{norm_country} postal code {norm_postal}", key)]
        if city and city.strip():
            norm_city = city.strip().title()
            clean_city = clean_text(norm_city)
            query_variants.append((f"{norm_country} postal code {norm_postal}, {norm_city}",
                                   f"{norm_country}_postal_{norm_postal}_{clean_city}"))
    else:
        # DLA KODÓW NIE-DWUCYFROWYCH - PRIORYTET MA PTV, POTEM NOMINATIM
        print("Priorytetowe użycie PTV API, potem Nominatim dla kodu nie-dwucyfrowego")

        # Generujemy warianty zapytań
        query_variants = generate_query_variants(country, norm_postal, city)

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
        "Denmark": "dk"
    }
    iso_code = ISO_CODES.get(norm_country, "")

    # Sprawdzenie w cache dla wszystkich wariantów
    for query_string, variant_key in query_variants:
        if variant_key in geo_cache:
            cached = geo_cache[variant_key]
            if cached[0] is not None:
                print(f"Znaleziono wynik w cache dla klucza: {variant_key}: {cached}")
                # Zapisz wynik również pod standardowym kluczem
                key = f"{norm_country}_{norm_postal}"
                if key != variant_key:
                    geo_cache[key] = cached
                return cached

    # Różne ścieżki geokodowania w zależności od długości kodu pocztowego
    if len(norm_postal) != 2:
        # DLA KODÓW NIE-DWUCYFROWYCH - najpierw PTV API, potem Nominatim

        # 1. Próba geokodowania przez PTV API
        print("Wykonuję geokodowanie przez PTV API...")
        for query_string, variant_key in query_variants:
            ptv_result = ptv_geocode_by_text(query_string, PTV_API_KEY, language="pl",country_code=iso_code)
            if ptv_result[0] is not None:
                print(f"PTV API - wariant '{query_string}' zwrócił wynik: {ptv_result}")
                geo_cache[variant_key] = ptv_result
                # Zapisz wynik również pod standardowym kluczem
                key = f"{norm_country}_{norm_postal}"
                if key != variant_key:
                    geo_cache[key] = ptv_result
                print(f"Zapisano do geo_cache: {variant_key} -> {ptv_result}")
                return ptv_result

        # 2. Jeśli PTV nie zwróciło wyników, próbujemy przez Nominatim
        print("PTV API nie zwróciło odpowiedniego wyniku, wywołuję Nominatim...")
        for query_string, variant_key in query_variants:
            print(f"Nominatim - próba zapytania: '{query_string}' (klucz: {variant_key}) z country_codes={iso_code}")
            try:
                extra_params = {}  # Dla kodów nie-dwucyfrowych nie potrzebujemy polygon_geojson
                location = geolocator.geocode(query_string, exactly_one=True, country_codes=iso_code, **extra_params)
                time.sleep(0.1)
                if location:
                    if "geojson" in location.raw and location.raw["geojson"]:
                        geo = location.raw["geojson"]
                        if geo.get("type") == "Polygon":
                            coords = geo.get("coordinates")[0]
                            lat = sum(point[1] for point in coords) / len(coords)
                            lon = sum(point[0] for point in coords) / len(coords)
                            quality = "centroid (polygon)"
                        else:
                            bb = location.raw.get("boundingbox")
                            if bb:
                                lat = (float(bb[0]) + float(bb[1])) / 2
                                lon = (float(bb[2]) + float(bb[3])) / 2
                                quality = "przybliżone (bounding box)"
                            else:
                                lat, lon = location.latitude, location.longitude
                                quality = "dokładne"
                    else:
                        if hasattr(location, 'raw') and 'boundingbox' in location.raw:
                            bb = location.raw['boundingbox']
                            lat = (float(bb[0]) + float(bb[1])) / 2
                            lon = (float(bb[2]) + float(bb[3])) / 2
                            quality = 'przybliżone (bounding box)'
                        else:
                            lat, lon = location.latitude, location.longitude
                            quality = 'dokładne'
                    source = location.raw.get('osm_type', 'API Nominatim')
                    display = location.raw.get('display_name', "").lower()
                    if "poland" in display or "polska" in display:
                        source = 'Polska (Nominatim)'
                    elif "italy" in display or "italia" in display:
                        source = 'Italy (Nominatim)'
                    result = (lat, lon, quality, source)
                    print(f"Nominatim - znaleziono wynik: {result}")
                    geo_cache[variant_key] = result
                    # Zapisz wynik również pod standardowym kluczem
                    key = f"{norm_country}_{norm_postal}"
                    if key != variant_key:
                        geo_cache[key] = result
                    print(f"Zapisano do geo_cache: {variant_key} -> {result}")
                    return result
            except Exception as e:
                print(f"Błąd Nominatim przy zapytaniu '{query_string}': {e}")

        # 3. Dla kodów nie-dwucyfrowych, na końcu sprawdzamy LOOKUP_DICT
        key = f"{norm_country}_{norm_postal}"
        if key in LOOKUP_DICT:
            lat, lon = LOOKUP_DICT[key]
            result = (lat, lon, "lookup (ostatnia opcja)", "lookup")
            print(f"LOOKUP (ostatnia opcja): Znaleziono współrzędne dla {key}: {result}")
            geo_cache[key] = result
            return result
    else:
        # DLA KODÓW DWUCYFROWYCH - NOWA KOLEJNOŚĆ:
        # PTV API -> Nominatim (po LOOKUP_DICT, który był sprawdzany wcześniej)

        # Próba geokodowania przez PTV API
        print("Rozpoczynam geokodowanie przez PTV API dla kodów dwucyfrowych...")
        for query_string, variant_key in query_variants:
            ptv_result = ptv_geocode_by_text(query_string, PTV_API_KEY, language="pl", country_code=iso_code)
            if ptv_result[0] is not None:
                print(f"PTV API - wariant '{query_string}' zwrócił wynik: {ptv_result}")
                geo_cache[variant_key] = ptv_result
                # Zapisz wynik również pod standardowym kluczem
                key = f"{norm_country}_{norm_postal}"
                if key != variant_key:
                    geo_cache[key] = ptv_result
                print(f"Zapisano do geo_cache: {variant_key} -> {ptv_result}")
                return ptv_result

        # Jeśli PTV API nie znalazło lokalizacji, próbujemy Nominatim
        print("PTV API nie zwróciło odpowiedniego wyniku, wywołuję Nominatim...")
        for query_string, variant_key in query_variants:
            print(f"Nominatim - próba zapytania: '{query_string}' (klucz: {variant_key}) z country_codes={iso_code}")
            try:
                extra_params = {"polygon_geojson": 1}  # Dla kodów dwucyfrowych używamy polygon_geojson
                location = geolocator.geocode(query_string, exactly_one=True, country_codes=iso_code, **extra_params)
                time.sleep(0.1)
                if location:
                    if "geojson" in location.raw and location.raw["geojson"]:
                        geo = location.raw["geojson"]
                        if geo.get("type") == "Polygon":
                            coords = geo.get("coordinates")[0]
                            lat = sum(point[1] for point in coords) / len(coords)
                            lon = sum(point[0] for point in coords) / len(coords)
                            quality = "centroid (polygon)"
                        else:
                            bb = location.raw.get("boundingbox")
                            if bb:
                                lat = (float(bb[0]) + float(bb[1])) / 2
                                lon = (float(bb[2]) + float(bb[3])) / 2
                                quality = "przybliżone (bounding box)"
                            else:
                                lat, lon = location.latitude, location.longitude
                                quality = "dokładne"
                    else:
                        if hasattr(location, 'raw') and 'boundingbox' in location.raw:
                            bb = location.raw['boundingbox']
                            lat = (float(bb[0]) + float(bb[1])) / 2
                            lon = (float(bb[2]) + float(bb[3])) / 2
                            quality = 'przybliżone (bounding box)'
                        else:
                            lat, lon = location.latitude, location.longitude
                            quality = 'dokładne'
                    source = location.raw.get('osm_type', 'API Nominatim')
                    display = location.raw.get('display_name', "").lower()
                    if "poland" in display or "polska" in display:
                        source = 'Polska (Nominatim)'
                    elif "italy" in display or "italia" in display:
                        source = 'Italy (Nominatim)'
                    result = (lat, lon, quality, source)
                    print(f"Nominatim - znaleziono wynik: {result}")
                    geo_cache[variant_key] = result
                    # Zapisz wynik również pod standardowym kluczem
                    key = f"{norm_country}_{norm_postal}"
                    if key != variant_key:
                        geo_cache[key] = result
                    print(f"Zapisano do geo_cache: {variant_key} -> {result}")
                    return result
            except Exception as e:
                print(f"Błąd Nominatim przy zapytaniu '{query_string}': {e}")

    # Jeśli żadna metoda nie znalazła lokalizacji
    if query_variants:
        _, variant_key = query_variants[-1]
        result = (None, None, 'nieznane', 'brak danych')
        geo_cache[variant_key] = result
        # Zapisz wynik również pod standardowym kluczem
        key = f"{norm_country}_{norm_postal}"
        if key != variant_key:
            geo_cache[key] = result
        print(f"Brak wyników, zapisano do geo_cache: {variant_key} -> {result}")
        return result

    return (None, None, 'nieznane', 'brak danych')


def get_ungeocoded_locations(df):
    ungeocoded_locations = []
    unique_locations = set()

    print("Zbieranie unikalnych lokalizacji z pliku...")
    for _, row in df.iterrows():
        try:
            kraj_zal = row['kraj_zaladunku']
            kod_zal = str(row['kod_pocztowy_zaladunku']).strip()
            miasto_zal = row.get('miasto_zaladunku', '')
            if not isinstance(miasto_zal, str):
                miasto_zal = ''

            kraj_rozl = row['kraj_rozladunku']
            kod_rozl = str(row['kod_pocztowy_rozladunku']).strip()
            miasto_rozl = row.get('miasto_rozladunku', '')
            if not isinstance(miasto_rozl, str):
                miasto_rozl = ''

            unique_locations.add((kraj_zal, kod_zal, miasto_zal.strip()))
            unique_locations.add((kraj_rozl, kod_rozl, miasto_rozl.strip()))
        except Exception as e:
            print(f"Błąd podczas zbierania lokalizacji z wiersza: {e}")

    print(f"Zebrano {len(unique_locations)} unikalnych lokalizacji do sprawdzenia")

    for loc in unique_locations:
        country, postal_code, city = loc
        # Ujednolicamy city – jeśli None, ustaw pusty ciąg
        if not isinstance(city, str):
            city = ""

        # Normalizacja danych
        norm_country = normalize_country(country)
        norm_postal = str(postal_code).strip()

        print(f"Sprawdzanie geokodowania dla: {norm_country}, {norm_postal}, {city}")

        # Sprawdzamy czy lokalizacja jest już zgeokodowana
        is_geocoded = False

        # Standardowy klucz
        std_key = f"{norm_country}_{norm_postal}"

        # Sprawdź w geo_cache
        if std_key in geo_cache:
            cached = geo_cache[std_key]
            if cached[0] is not None and cached[1] is not None:
                print(f"Znaleziono w geo_cache: {std_key} -> {cached}")
                is_geocoded = True

        # Sprawdź w LOOKUP_DICT dla dwucyfrowych kodów
        if not is_geocoded and len(norm_postal) == 2 and std_key in LOOKUP_DICT:
            print(f"Znaleziono w LOOKUP_DICT: {std_key}")
            is_geocoded = True

        # Sprawdź inne warianty kluczy w geo_cache
        if not is_geocoded:
            variants = generate_query_variants(country, postal_code, city)
            for _, variant_key in variants:
                if variant_key in geo_cache:
                    cached = geo_cache[variant_key]
                    if cached[0] is not None and cached[1] is not None:
                        print(f"Znaleziono w geo_cache dla wariantu: {variant_key} -> {cached}")
                        # Synchronizuj ze standardowym kluczem
                        geo_cache[std_key] = cached
                        is_geocoded = True
                        break

        # Jeśli nadal nie znaleziono, spróbuj zgeokodować
        if not is_geocoded:
            # Użyj get_coordinates do próby geokodowania
            try:
                result = get_coordinates(country, postal_code, city)
                if result[0] is not None and result[1] is not None:
                    print(f"Udało się zgeokodować: {country}, {postal_code}, {city} -> {result}")
                    is_geocoded = True
            except Exception as e:
                print(f"Błąd przy próbie geokodowania: {e}")

        # Jeśli nadal nie udało się zgeokodować, dodaj do nierozpoznanych
        if not is_geocoded:
            variants = generate_query_variants(country, postal_code, city)
            ungeocoded_locations.append({
                'country': country,
                'postal_code': postal_code,
                'city': city,
                'key': std_key,
                'query_variants': variants
            })

    print(f"Znaleziono {len(ungeocoded_locations)} nierozpoznanych lokalizacji")

    return ungeocoded_locations


def haversine(coord1, coord2):
    if None in coord1 or None in coord2:
        return None
    R = 6371
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def safe_float(value):
    if pd.isna(value) or str(value).strip().lower() in ['nan', 'none', '']:
        return None
    try:
        return float(str(value).strip().replace(',', '.'))
    except (ValueError, TypeError):
        return None


def format_currency(value):
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def select_best_rate(row, rate_columns):
    for col in rate_columns:
        rate = safe_float(row.get(col))
        if rate is not None:
            return rate
    return None


def calculate_fracht(distance, rate):
    if distance is None or rate is None:
        return None
    try:
        return distance * rate
    except TypeError:
        return None


def get_toll_cost(coord_from, coord_to, start_time="2023-08-29T10:00:00.000Z", routing_mode=DEFAULT_ROUTING_MODE):
    base_url = "https://api.myptv.com/routing/v1/routes"
    params = {
        "waypoints": [f"{coord_from[0]},{coord_from[1]}", f"{coord_to[0]},{coord_to[1]}"],
        "results": "TOLL_COSTS",
        "options[trafficMode]": "AVERAGE",
        "options[startTime]": start_time,
        "options[routingMode]": routing_mode
    }
    headers = {"apiKey": PTV_API_KEY}
    try:
        response = requests.get(base_url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print("Odpowiedź API (toll_cost):", data)
            toll_cost = (data.get("toll", {})
                         .get("costs", {})
                         .get("convertedPrice", {})
                         .get("price"))
            return toll_cost
        else:
            print(f"Błąd API PTV: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Wyjątek podczas obliczania opłat drogowych: {e}")
    return None


def get_route_distance(coord_from, coord_to, avoid_switzerland=False, routing_mode=DEFAULT_ROUTING_MODE):
    if None in coord_from or None in coord_to:
        return None
    cache_key = f"{coord_from[0]:.6f},{coord_from[1]:.6f}_{coord_to[0]:.6f},{coord_to[1]:.6f}_{avoid_switzerland}_{routing_mode}"
    if cache_key in route_cache:
        return route_cache[cache_key]
    base_url = "https://api.myptv.com/routing/v1/routes"
    params = {
        "waypoints": [f"{coord_from[0]},{coord_from[1]}", f"{coord_to[0]},{coord_to[1]}"],
        "results": "BORDER_EVENTS,POLYLINE",
        "options[routingMode]": routing_mode,
        "options[trafficMode]": "AVERAGE"
    }
    if avoid_switzerland:
        params["options[prohibitedCountries]"] = "CH"
    headers = {"apiKey": PTV_API_KEY}
    print("Wysyłanie zapytania z waypointami:", params["waypoints"])
    try:
        response = requests.get(base_url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "distance" in data:
                distance = data["distance"] / 1000
                route_cache[cache_key] = distance
                return distance
            else:
                print(f"Brak informacji o dystansie w odpowiedzi API: {data}")
        else:
            print(f"Błąd API PTV: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Wyjątek PTV API: {e}")
    route_cache[cache_key] = None
    return None


def verify_city_postal_code_match(country, postal_code, city, threshold_km=100):
    print(f"Wywołano verify_city_postal_code_match z parametrami: kraj={country}, kod={postal_code}, miasto={city}")

    result = {
        'is_match': True,
        'distance_km': None,
        'postal_coords': None,
        'city_coords': None,
        'error': None,
        'lookup_coords': None,  # Nowe pole dla współrzędnych z LOOKUP_DICT
        'suggested_coords': None  # Nowe pole dla sugerowanych współrzędnych
    }

    # Bardziej dokładne sprawdzenie, czy miasto jest puste
    if city is None or not isinstance(city, str) or city.strip() == "" or pd.isna(city):
        print(f"Miasto jest puste, zwracam wynik bez geokodowania")
        result['error'] = "Brak miasta"
        return result

    if postal_code is None or str(postal_code).strip() == "" or pd.isna(postal_code):
        print(f"Kod pocztowy jest pusty, zwracam wynik bez geokodowania")
        result['error'] = "Brak kodu pocztowego"
        return result

    norm_country = normalize_country(country)

    # Dodaj mapowanie kodów ISO dla każdego kraju
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
        "Bulgaria": "bg",
        "Estonia": "ee",
        "Croatia": "hr",
        "Ireland": "ie",
        "Lithuania": "lt",
        "Latvia": "lv",
        "Romania": "ro",
        "United Kingdom": "gb"
    }

    iso_code = ISO_CODES.get(norm_country, "")

    # ETAP 1: Geokodowanie kodu pocztowego
    # A. Najpierw sprawdzamy w geo_cache
    postal_key = f"{norm_country}_{postal_code}"
    if postal_key in geo_cache:
        postal_coords = geo_cache[postal_key][:2]
        postal_quality = geo_cache[postal_key][2] if len(geo_cache[postal_key]) > 2 else 'nieznane'
        postal_source = geo_cache[postal_key][3] if len(geo_cache[postal_key]) > 3 else 'cache'
        print(f"Znaleziono współrzędne dla kodu {postal_code} w cache: {postal_coords}")
    else:
        # B. Sprawdzamy w LOOKUP_DICT
        if postal_key in LOOKUP_DICT:
            postal_coords = LOOKUP_DICT[postal_key]
            postal_quality = 'lookup'
            postal_source = 'LOOKUP_DICT'
            # Zapisz do cache dla przyszłych zapytań
            geo_cache[postal_key] = (*postal_coords, postal_quality, postal_source)
            print(f"Znaleziono współrzędne dla kodu {postal_code} w LOOKUP_DICT: {postal_coords}")
        else:
            # Sprawdź dla dwucyfrowego prefiksu
            postal_prefix = str(postal_code).strip()[:2].zfill(2)
            prefix_key = f"{norm_country}_{postal_prefix}"
            if prefix_key in LOOKUP_DICT:
                postal_coords = LOOKUP_DICT[prefix_key]
                postal_quality = 'lookup (prefiks)'
                postal_source = 'LOOKUP_DICT'
                # Zapisz do cache dla przyszłych zapytań
                geo_cache[postal_key] = (*postal_coords, postal_quality, postal_source)
                print(f"Znaleziono współrzędne dla prefiksu kodu {postal_prefix} w LOOKUP_DICT: {postal_coords}")
            else:
                # C. Próbujemy PTV API
                try:
                    query_string = f"{postal_code}, {norm_country}"
                    print(f"Zapytanie PTV API o kod pocztowy: {query_string}")
                    ptv_result = ptv_geocode_by_text(query_string, PTV_API_KEY, language="pl", country_code=iso_code)
                    if ptv_result[0] is not None:
                        postal_coords = ptv_result[:2]
                        postal_quality = ptv_result[2] if len(ptv_result) > 2 else 'PTV API'
                        postal_source = ptv_result[3] if len(ptv_result) > 3 else 'PTV API'
                        # Zapisz do cache
                        geo_cache[postal_key] = (*postal_coords, postal_quality, postal_source)
                        print(f"Znaleziono współrzędne dla kodu {postal_code} w PTV API: {postal_coords}")
                    else:
                        # D. Ostatnia próba - Nominatim
                        query_string = f"{postal_code}, {norm_country}"
                        print(f"Zapytanie Nominatim o kod pocztowy: {query_string}")
                        location = geolocator.geocode(query_string, exactly_one=True, country_codes=iso_code)
                        time.sleep(0.1)
                        if location:
                            postal_coords = (location.latitude, location.longitude)
                            postal_quality = 'Nominatim'
                            postal_source = 'Nominatim'
                            geo_cache[postal_key] = (*postal_coords, postal_quality, postal_source)
                            print(f"Znaleziono współrzędne dla kodu {postal_code} w Nominatim: {postal_coords}")
                        else:
                            print(f"Nie znaleziono lokalizacji dla kodu pocztowego {postal_code}")
                            result['error'] = f"Nie znaleziono lokalizacji dla kodu pocztowego {postal_code}"
                            return result
                except Exception as e:
                    print(f"Błąd geokodowania kodu pocztowego: {str(e)}")
                    result['error'] = f"Błąd geokodowania kodu pocztowego: {str(e)}"
                    return result

    # ETAP 2: Geokodowanie miasta
    # A. Najpierw sprawdzamy w geo_cache
    city_key = f"{norm_country}_{city}"
    if city_key in geo_cache:
        city_coords = geo_cache[city_key][:2]
        city_quality = geo_cache[city_key][2] if len(geo_cache[city_key]) > 2 else 'nieznane'
        city_source = geo_cache[city_key][3] if len(geo_cache[city_key]) > 3 else 'cache'
        print(f"Znaleziono współrzędne dla miasta {city} w cache: {city_coords}")
    else:
        # B. Sprawdzamy w LOOKUP_DICT (pełna nazwa miasta jako klucz)
        city_lookup_key = f"{norm_country}_{city.strip().lower()}"
        # Sprawdź również z wyczyszczoną nazwą miasta
        clean_city = clean_text(city)
        city_clean_lookup_key = f"{norm_country}_{clean_city}"

        found_in_lookup = False
        # Sprawdź dokładne dopasowanie
        for lookup_key in [city_lookup_key, city_clean_lookup_key]:
            if lookup_key in LOOKUP_DICT:
                city_coords = LOOKUP_DICT[lookup_key]
                city_quality = 'lookup'
                city_source = 'LOOKUP_DICT'
                # Zapisz do cache dla przyszłych zapytań
                geo_cache[city_key] = (*city_coords, city_quality, city_source)
                print(f"Znaleziono współrzędne dla miasta {city} w LOOKUP_DICT: {city_coords}")
                found_in_lookup = True
                break

        # Jeśli nie znaleziono dokładnego dopasowania, sprawdź częściowe
        if not found_in_lookup:
            # Przeszukaj klucze zawierające nazwę miasta
            for db_key in LOOKUP_DICT:
                if db_key.startswith(f"{norm_country}_") and (clean_city in db_key or city.lower() in db_key.lower()):
                    city_coords = LOOKUP_DICT[db_key]
                    city_quality = 'lookup (częściowe dopasowanie)'
                    city_source = 'LOOKUP_DICT'
                    # Zapisz do cache dla przyszłych zapytań
                    geo_cache[city_key] = (*city_coords, city_quality, city_source)
                    print(f"Znaleziono częściowe dopasowanie dla miasta {city} w LOOKUP_DICT: {city_coords}")
                    found_in_lookup = True
                    break

        if not found_in_lookup:
            # C. Próbujemy PTV API
            try:
                query_string = f"{city}, {norm_country}"
                print(f"Zapytanie PTV API o miasto: {query_string} z region={iso_code}")
                ptv_result = ptv_geocode_by_text(query_string, PTV_API_KEY, language="pl", country_code=iso_code)
                if ptv_result[0] is not None:
                    city_coords = ptv_result[:2]
                    city_quality = ptv_result[2] if len(ptv_result) > 2 else 'PTV API'
                    city_source = ptv_result[3] if len(ptv_result) > 3 else 'PTV API'
                    # Zapisz do cache
                    geo_cache[city_key] = (*city_coords, city_quality, city_source)
                    print(f"Znaleziono współrzędne dla miasta {city} w PTV API: {city_coords}")
                else:
                    # D. Ostatnia próba - Nominatim
                    query_string = f"{city}, {norm_country}"
                    print(f"Zapytanie Nominatim o miasto: {query_string} z country_codes={iso_code}")
                    location = geolocator.geocode(query_string, exactly_one=True, country_codes=iso_code)
                    time.sleep(0.1)
                    if location:
                        city_coords = (location.latitude, location.longitude)
                        city_quality = 'Nominatim'
                        city_source = 'Nominatim'
                        geo_cache[city_key] = (*city_coords, city_quality, city_source)
                        print(f"Znaleziono współrzędne dla miasta {city} w Nominatim: {city_coords}")
                    else:
                        print(f"Nie znaleziono lokalizacji dla miasta {city}")
                        result['error'] = f"Nie znaleziono lokalizacji dla miasta {city}"
                        return result
            except Exception as e:
                print(f"Błąd geokodowania miasta: {str(e)}")
                result['error'] = f"Błąd geokodowania miasta: {str(e)}"
                return result

    # Obliczenie odległości między kodem pocztowym a miastem
    distance_km = haversine(postal_coords, city_coords)
    result['postal_coords'] = postal_coords
    result['city_coords'] = city_coords
    result['distance_km'] = distance_km
    print(f"Obliczona odległość między kodem pocztowym a miastem: {distance_km} km")

    # Jeśli odległość przekracza próg (domyślnie 30 km), wykonaj dodatkowe sprawdzenie
    if distance_km is not None and distance_km > threshold_km:
        result['is_match'] = False
        print(f"Odległość przekracza próg {threshold_km} km - wykonuję dodatkowe sprawdzenie")

        # Ocena jakości i wiarygodności geokodowania
        postal_reliability = evaluate_geocoding_reliability(postal_quality, postal_source)
        city_reliability = evaluate_geocoding_reliability(city_quality, city_source)

        print(f"Wiarygodność kodu pocztowego: {postal_reliability}, Wiarygodność miasta: {city_reliability}")

        # Wybór najbardziej wiarygodnych współrzędnych
        if postal_reliability >= city_reliability:
            result['suggested_coords'] = postal_coords
            print(f"Wybieram współrzędne kodu pocztowego jako sugerowane: {postal_coords}")
        else:
            result['suggested_coords'] = city_coords
            print(f"Wybieram współrzędne miasta jako sugerowane: {city_coords}")
    else:
        print(f"Odległość jest w granicach progu {threshold_km} km - oznaczono jako dopasowane")

    return result


# Funkcja pomocnicza do oceny wiarygodności geokodowania
def evaluate_geocoding_reliability(quality, source):
    reliability = 50  # Wyjściowa średnia ocena

    # Ocena na podstawie jakości
    if quality in ['lookup', 'LOOKUP_DICT']:
        reliability += 30  # Najwyższa wiarygodność - dane z ręcznie zweryfikowanej bazy
    elif quality in ['lookup (prefiks)', 'lookup (częściowe dopasowanie)']:
        reliability += 20  # Wysoka wiarygodność, ale częściowe dopasowanie
    elif 'PTV API' in quality:
        reliability += 15  # Dobra wiarygodność - komercyjne API
    elif 'Nominatim' in quality:
        reliability += 5  # Niższa wiarygodność - darmowe API

    # Ocena na podstawie źródła
    if source in ['LOOKUP_DICT', 'lookup']:
        reliability += 20  # Najlepsze źródło
    elif source == 'PTV API':
        reliability += 15  # Dobre źródło
    elif source == 'Nominatim':
        reliability += 5  # Mniej wiarygodne źródło

    # Dodatkowe czynniki można dodać w przyszłości

    return min(100, max(0, reliability))  # Wartość między 0 a 100


def get_all_rates(lc, lp, uc, up, lc_coords, uc_coords):
    try:
        historical_rates_df = pd.read_excel("historical_rates.xlsx",
                                            dtype={'kod pocztowy zaladunku': str, 'kod pocztowy rozladunku': str})
        historical_rates_gielda_df = pd.read_excel("historical_rates_gielda.xlsx",
                                                   dtype={'kod pocztowy zaladunku': str,
                                                          'kod pocztowy rozladunku': str})
    except Exception as e:
        print(f"Błąd wczytywania danych historycznych: {e}")
        historical_rates_df = pd.DataFrame()
        historical_rates_gielda_df = pd.DataFrame()

    norm_lc = normalize_country(lc).strip()
    norm_uc = normalize_country(uc).strip()

    # Określamy, czy kod pocztowy ma conajmniej dwie cyfry
    lp_has_two_digits = len(str(lp).strip()) >= 2
    up_has_two_digits = len(str(up).strip()) >= 2

    # Przygotowujemy kody do dopasowania
    norm_lp = str(lp).strip()[:2].zfill(2) if lp_has_two_digits else str(lp).strip()[0]
    norm_up = str(up).strip()[:2].zfill(2) if up_has_two_digits else str(up).strip()[0]

    # Pierwsza cyfra kodu (na wszelki wypadek zachowujemy)
    norm_lp_1 = str(lp).strip()[0]
    norm_up_1 = str(up).strip()[0]

    # Inicjalizujemy informacje o dopasowaniu
    if lp_has_two_digits and up_has_two_digits:
        dopasowanie_hist = "2 cyfry"
        dopasowanie_gielda = "2 cyfry"
    elif not lp_has_two_digits and up_has_two_digits:
        dopasowanie_hist = "Załadunek: 1 cyfra, Rozładunek: 2 cyfry"
        dopasowanie_gielda = "Załadunek: 1 cyfra, Rozładunek: 2 cyfry"
    elif lp_has_two_digits and not up_has_two_digits:
        dopasowanie_hist = "Załadunek: 2 cyfry, Rozładunek: 1 cyfra"
        dopasowanie_gielda = "Załadunek: 2 cyfry, Rozładunek: 1 cyfra"
    else:
        dopasowanie_hist = "Obie lokalizacje: 1 cyfra"
        dopasowanie_gielda = "Obie lokalizacje: 1 cyfra"

    # Dla dwóch cyfr w obu kodach pocztowych
    if lp_has_two_digits and up_has_two_digits:
        exact_hist = historical_rates_df[
            (historical_rates_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
            (historical_rates_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
            (historical_rates_df['kod pocztowy zaladunku'].astype(str).str.zfill(2) == norm_lp) &
            (historical_rates_df['kod pocztowy rozladunku'].astype(str).str.zfill(2) == norm_up)
            ]

        exact_gielda = historical_rates_gielda_df[
            (historical_rates_gielda_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
            (historical_rates_gielda_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
            (historical_rates_gielda_df['kod pocztowy zaladunku'].astype(str).str.zfill(2) == norm_lp) &
            (historical_rates_gielda_df['kod pocztowy rozladunku'].astype(str).str.zfill(2) == norm_up)
            ]
    # Dla jednej cyfry w kodzie załadunku, dwóch cyfr w kodzie rozładunku
    elif not lp_has_two_digits and up_has_two_digits:
        exact_hist = historical_rates_df[
            (historical_rates_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
            (historical_rates_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
            (historical_rates_df['kod pocztowy zaladunku'].astype(str).str[0] == norm_lp) &
            (historical_rates_df['kod pocztowy rozladunku'].astype(str).str.zfill(2) == norm_up)
            ]

        exact_gielda = historical_rates_gielda_df[
            (historical_rates_gielda_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
            (historical_rates_gielda_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
            (historical_rates_gielda_df['kod pocztowy zaladunku'].astype(str).str[0] == norm_lp) &
            (historical_rates_gielda_df['kod pocztowy rozladunku'].astype(str).str.zfill(2) == norm_up)
            ]
    # Dla dwóch cyfr w kodzie załadunku, jednej cyfry w kodzie rozładunku
    elif lp_has_two_digits and not up_has_two_digits:
        exact_hist = historical_rates_df[
            (historical_rates_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
            (historical_rates_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
            (historical_rates_df['kod pocztowy zaladunku'].astype(str).str.zfill(2) == norm_lp) &
            (historical_rates_df['kod pocztowy rozladunku'].astype(str).str[0] == norm_up)
            ]

        exact_gielda = historical_rates_gielda_df[
            (historical_rates_gielda_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
            (historical_rates_gielda_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
            (historical_rates_gielda_df['kod pocztowy zaladunku'].astype(str).str.zfill(2) == norm_lp) &
            (historical_rates_gielda_df['kod pocztowy rozladunku'].astype(str).str[0] == norm_up)
            ]
    # Dla jednej cyfry w obu kodach
    else:
        exact_hist = historical_rates_df[
            (historical_rates_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
            (historical_rates_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
            (historical_rates_df['kod pocztowy zaladunku'].astype(str).str[0] == norm_lp) &
            (historical_rates_df['kod pocztowy rozladunku'].astype(str).str[0] == norm_up)
            ]

        exact_gielda = historical_rates_gielda_df[
            (historical_rates_gielda_df['kraj zaladunku'].apply(normalize_country) == norm_lc) &
            (historical_rates_gielda_df['kraj rozladunku'].apply(normalize_country) == norm_uc) &
            (historical_rates_gielda_df['kod pocztowy zaladunku'].astype(str).str[0] == norm_lp) &
            (historical_rates_gielda_df['kod pocztowy rozladunku'].astype(str).str[0] == norm_up)
            ]

    # Inicjalizacja wyników
    podlot_hist, z_hist = None, 0
    podlot_gielda, z_gielda = None, 0
    result = {
        'hist_stawka_3m': None,
        'hist_stawka_6m': None,
        'hist_stawka_12m': None,
        'hist_stawka_48m': None,
        'hist_fracht_3m': None,
        'gielda_stawka_3m': None,
        'gielda_stawka_6m': None,
        'gielda_stawka_12m': None,
        'gielda_stawka_48m': None,
        'gielda_fracht_3m': None,
        'podlot_historyczny': None,  # Zmieniona nazwa z 'dystans' na 'podlot_historyczny'
        'relacja': f"{norm_lc} {norm_lp} - {norm_uc} {norm_up}",
        'dopasowanie_hist': dopasowanie_hist,
        'dopasowanie_gielda': dopasowanie_gielda
    }

    # Przetwarzanie wyników historycznych (średnia ważona, jeśli jest wiele rekordów)
    if not exact_hist.empty:
        try:
            if len(exact_hist) > 1:
                # Filtrujemy tylko rekordy z niepustymi stawkami dla każdego okresu
                column_mappings = {
                    'hist_stawka_3m': 'stawka_3m',
                    'hist_stawka_6m': 'stawka_6m',
                    'hist_stawka_12m': 'stawka_12m',
                    'hist_fracht_3m': 'fracht_3m'
                }

                # Przetwarzanie każdej kolumny stawek oddzielnie
                used_records_count = {}

                for result_key, df_key in column_mappings.items():
                    if df_key in exact_hist.columns:
                        # Filtruj tylko rekordy z niepustymi wartościami
                        valid_records = exact_hist[~pd.isna(exact_hist[df_key])]

                        if not valid_records.empty:
                            # Zapisz informację o liczbie użytych rekordów
                            used_records_count[result_key] = len(valid_records)

                            # Oblicz sumę zleceń dla tych rekordów
                            total_zlecen = valid_records[
                                'Liczba zlecen'].sum() if 'Liczba zlecen' in valid_records.columns else len(
                                valid_records)

                            if total_zlecen > 0:
                                # Oblicz wagi na podstawie liczby zleceń
                                if 'Liczba zlecen' in valid_records.columns:
                                    weights = valid_records['Liczba zlecen'] / total_zlecen
                                else:
                                    weights = pd.Series([1 / len(valid_records)] * len(valid_records),
                                                        index=valid_records.index)

                                # Oblicz średnią ważoną
                                result[result_key] = (valid_records[df_key] * weights).sum()

                                # Aktualizuj liczbę zleceń (dla stawki 3m)
                                if result_key == 'hist_stawka_3m':
                                    z_hist = total_zlecen

                # Podlot (dawniej dystans) - osobne przetwarzanie
                if 'dystans' in exact_hist.columns:
                    valid_dist_records = exact_hist[~pd.isna(exact_hist['dystans'])]

                    if not valid_dist_records.empty:
                        used_records_count['podlot_historyczny'] = len(valid_dist_records)

                        total_zlecen = valid_dist_records[
                            'Liczba zlecen'].sum() if 'Liczba zlecen' in valid_dist_records.columns else len(
                            valid_dist_records)

                        if total_zlecen > 0:
                            if 'Liczba zlecen' in valid_dist_records.columns:
                                weights = valid_dist_records['Liczba zlecen'] / total_zlecen
                            else:
                                weights = pd.Series([1 / len(valid_dist_records)] * len(valid_dist_records),
                                                    index=valid_dist_records.index)

                            podlot_hist = (valid_dist_records['dystans'] * weights).sum()
                            result['podlot_historyczny'] = podlot_hist

                # Informacja o dopasowaniu - zaktualizuj, jeśli część rekordów pominięto
                if any(count < len(exact_hist) for count in used_records_count.values()):
                    non_empty_counts = ", ".join([f"{key.split('_')[1]}: {count}/{len(exact_hist)}"
                                                  for key, count in used_records_count.items()])

                    # Zaktualizuj dopasowanie, zachowując informację o rodzaju dopasowania
                    if "średnia ważona" in dopasowanie_hist:
                        dopasowanie_hist = dopasowanie_hist.split(" (")[0] + f" (tylko niepuste: {non_empty_counts})"
                    else:
                        dopasowanie_hist += f" (tylko niepuste: {non_empty_counts})"
                else:
                    # Dodaj informację o średniej ważonej
                    dopasowanie_hist += f" (średnia ważona z {len(exact_hist)} dopasowań)"

                # Aktualizacja po modyfikacji
                result['dopasowanie_hist'] = dopasowanie_hist
            else:
                # Jeśli jest tylko jeden rekord, użyj go bezpośrednio
                row = exact_hist.iloc[0]
                try:
                    # Zmiana: interpretacja dystansu jako podlotu
                    podlot_hist = float(row.get('dystans')) if not pd.isna(row.get('dystans')) else None
                except:
                    podlot_hist = None
                try:
                    z_hist = float(row.get('Liczba zlecen', 0)) if not pd.isna(row.get('Liczba zlecen', 0)) else 0
                except:
                    z_hist = 0

                # Używaj tylko niepustych wartości z pojedynczego rekordu
                result.update({
                    'hist_stawka_3m': row.get('stawka_3m') if not pd.isna(row.get('stawka_3m')) else None,
                    'hist_stawka_6m': row.get('stawka_6m') if not pd.isna(row.get('stawka_6m')) else None,
                    'hist_stawka_12m': row.get('stawka_12m') if not pd.isna(row.get('stawka_12m')) else None,
                    'hist_fracht_3m': row.get('fracht_3m') if not pd.isna(row.get('fracht_3m')) else None,
                    'podlot_historyczny': podlot_hist
                })
        except Exception as e:
            print(f"Błąd przetwarzania danych historycznych: {e}")

    # Przetwarzanie wyników z giełdy (średnia ważona, jeśli jest wiele rekordów)
    if not exact_gielda.empty:
        try:
            if len(exact_gielda) > 1:
                # Filtrujemy tylko rekordy z niepustymi stawkami dla każdego okresu
                column_mappings = {
                    'gielda_stawka_3m': 'stawka_3m',
                    'gielda_stawka_6m': 'stawka_6m',
                    'gielda_stawka_12m': 'stawka_12m',
                    'gielda_fracht_3m': 'fracht_3m'
                }

                # Przetwarzanie każdej kolumny stawek oddzielnie
                used_records_count = {}

                for result_key, df_key in column_mappings.items():
                    if df_key in exact_gielda.columns:
                        # Filtruj tylko rekordy z niepustymi wartościami
                        valid_records = exact_gielda[~pd.isna(exact_gielda[df_key])]

                        if not valid_records.empty:
                            # Zapisz informację o liczbie użytych rekordów
                            used_records_count[result_key] = len(valid_records)

                            # Oblicz sumę zleceń dla tych rekordów
                            total_zlecen = valid_records[
                                'Liczba zlecen'].sum() if 'Liczba zlecen' in valid_records.columns else len(
                                valid_records)

                            if total_zlecen > 0:
                                # Oblicz wagi na podstawie liczby zleceń
                                if 'Liczba zlecen' in valid_records.columns:
                                    weights = valid_records['Liczba zlecen'] / total_zlecen
                                else:
                                    weights = pd.Series([1 / len(valid_records)] * len(valid_records),
                                                        index=valid_records.index)

                                # Oblicz średnią ważoną
                                result[result_key] = (valid_records[df_key] * weights).sum()

                                # Aktualizuj liczbę zleceń (dla stawki 3m)
                                if result_key == 'gielda_stawka_3m':
                                    z_gielda = total_zlecen

                # Podlot - osobne przetwarzanie tylko jeśli nie mamy jeszcze podlotu
                if 'dystans' in exact_gielda.columns and result['podlot_historyczny'] is None:
                    valid_dist_records = exact_gielda[~pd.isna(exact_gielda['dystans'])]

                    if not valid_dist_records.empty:
                        used_records_count['podlot_historyczny'] = len(valid_dist_records)

                        total_zlecen = valid_dist_records[
                            'Liczba zlecen'].sum() if 'Liczba zlecen' in valid_dist_records.columns else len(
                            valid_dist_records)

                        if total_zlecen > 0:
                            if 'Liczba zlecen' in valid_dist_records.columns:
                                weights = valid_dist_records['Liczba zlecen'] / total_zlecen
                            else:
                                weights = pd.Series([1 / len(valid_dist_records)] * len(valid_dist_records),
                                                    index=valid_dist_records.index)

                            podlot_gielda = (valid_dist_records['dystans'] * weights).sum()
                            result['podlot_historyczny'] = podlot_gielda

                # Informacja o dopasowaniu - zaktualizuj, jeśli część rekordów pominięto
                if any(count < len(exact_gielda) for count in used_records_count.values()):
                    non_empty_counts = ", ".join([f"{key.split('_')[1]}: {count}/{len(exact_gielda)}"
                                                  for key, count in used_records_count.items()])

                    # Zaktualizuj dopasowanie, zachowując informację o rodzaju dopasowania
                    if "średnia ważona" in dopasowanie_gielda:
                        dopasowanie_gielda = dopasowanie_gielda.split(" (")[
                                                 0] + f" (tylko niepuste: {non_empty_counts})"
                    else:
                        dopasowanie_gielda += f" (tylko niepuste: {non_empty_counts})"
                else:
                    # Dodaj informację o średniej ważonej
                    dopasowanie_gielda += f" (średnia ważona z {len(exact_gielda)} dopasowań)"

                # Aktualizacja po modyfikacji
                result['dopasowanie_gielda'] = dopasowanie_gielda
            else:
                # Jeśli jest tylko jeden rekord, użyj go bezpośrednio
                row = exact_gielda.iloc[0]
                try:
                    # Zmiana: interpretacja dystansu jako podlotu
                    podlot_gielda = float(row.get('dystans')) if not pd.isna(row.get('dystans')) else None
                except:
                    podlot_gielda = None
                try:
                    z_gielda = float(row.get('Liczba zlecen', 0)) if not pd.isna(row.get('Liczba zlecen', 0)) else 0
                except:
                    z_gielda = 0

                # Używaj tylko niepustych wartości z pojedynczego rekordu
                gielda_values = {
                    'gielda_stawka_3m': row.get('stawka_3m') if not pd.isna(row.get('stawka_3m')) else None,
                    'gielda_stawka_6m': row.get('stawka_6m') if not pd.isna(row.get('stawka_6m')) else None,
                    'gielda_stawka_12m': row.get('stawka_12m') if not pd.isna(row.get('stawka_12m')) else None,
                    'gielda_fracht_3m': row.get('fracht_3m') if not pd.isna(row.get('fracht_3m')) else None,
                }

                # Aktualizuj wyniki, ale nie nadpisuj podlotu jeśli już jest ustawiony
                result.update(gielda_values)
                if result['podlot_historyczny'] is None:
                    result['podlot_historyczny'] = podlot_gielda
        except Exception as e:
            print(f"Błąd przetwarzania danych z giełdy: {e}")

    # Obliczenie średniego podlotu ważonego liczbą zleceń
    if (z_hist + z_gielda) > 0:
        hist_podlot = podlot_hist if podlot_hist is not None else 0
        gielda_podlot = podlot_gielda if podlot_gielda is not None else 0

        # Tylko jeśli mamy jakieś faktyczne wartości podlotu
        if hist_podlot > 0 or gielda_podlot > 0:
            weighted_podlot = (hist_podlot * z_hist + gielda_podlot * z_gielda) / (z_hist + z_gielda)
            result['podlot_sredni_wazony'] = weighted_podlot

    return result


def modify_process_przetargi(process_func):
    @wraps(process_func)
    def wrapper(*args, **kwargs):
        global GEOCODING_TOTAL, GEOCODING_CURRENT
        df = args[0] if args else kwargs.get('df')
        unique_locations = set()
        for _, row in df.iterrows():
            # Ujednolicamy pola miasta – jeśli nie string, ustaw pusty ciąg
            city_load = row.get('miasto_zaladunku', '')
            if not isinstance(city_load, str):
                city_load = ''
            city_unload = row.get('miasto_rozladunku', '')
            if not isinstance(city_unload, str):
                city_unload = ''
            unique_locations.add((
                row['kraj_zaladunku'],
                str(row['kod_pocztowy_zaladunku']).strip(),
                city_load.strip()
            ))
            unique_locations.add((
                row['kraj_rozladunku'],
                str(row['kod_pocztowy_rozladunku']).strip(),
                city_unload.strip()
            ))
        print(">>> Wywołanie geokodowania dla unikalnych lokalizacji:")
        GEOCODING_TOTAL = len(unique_locations)
        GEOCODING_CURRENT = 0
        for loc in unique_locations:
            print("Geokodowanie:", loc)
            get_coordinates(*loc)
            GEOCODING_CURRENT += 1
            print(get_geocoding_progress())
        ungeocoded = get_ungeocoded_locations(df)
        if ungeocoded:
            print(">>> Nierozpoznane lokalizacje po geokodowaniu:", ungeocoded)
            raise GeocodeException(ungeocoded)
        else:
            print(">>> Wszystkie lokalizacje zostały poprawnie zgeokodowane.")
        return process_func(*args, **kwargs)

    return wrapper


@modify_process_przetargi
def process_przetargi(df, fuel_cost=0.40, driver_cost=130):
    global PROGRESS, RESULT_EXCEL, CURRENT_ROW, TOTAL_ROWS
    TOTAL_ROWS = len(df)
    CURRENT_ROW = 0
    print(f"Rozpoczynam przetwarzanie {TOTAL_ROWS} wierszy...")
    results = []
    all_locations = set()
    for _, row in df.iterrows():
        lc = row['kraj_zaladunku']
        lp = str(row['kod_pocztowy_zaladunku']).strip()
        uc = row['kraj_rozladunku']
        up = str(row['kod_pocztowy_rozladunku']).strip()

        # Poprawna obsługa miast
        lc_city = row.get("miasto_zaladunku", "")
        if lc_city is None or not isinstance(lc_city, str) or pd.isna(lc_city):
            lc_city = ""
        else:
            lc_city = lc_city.strip()

        uc_city = row.get("miasto_rozladunku", "")
        if uc_city is None or not isinstance(uc_city, str) or pd.isna(uc_city):
            uc_city = ""
        else:
            uc_city = uc_city.strip()

        all_locations.add((lc, lp, lc_city if lc_city else None))
        all_locations.add((uc, up, uc_city if uc_city else None))

    print(f"Geokodowanie {len(all_locations)} unikalnych lokalizacji...")
    location_coords = {}
    for loc in all_locations:
        print("Przed wywołaniem get_coordinates dla lokalizacji:", loc)
        location_coords[loc] = get_coordinates(*loc)

    print("Kolumny:", list(df.columns))
    for i, (_, row) in enumerate(df.iterrows()):
        try:
            CURRENT_ROW = i + 1
            lc = row['kraj_zaladunku']
            lp = str(row['kod_pocztowy_zaladunku']).strip()
            uc = row['kraj_rozladunku']
            up = str(row['kod_pocztowy_rozladunku']).strip()

            # Poprawna obsługa miast
            lc_city = row.get("miasto_zaladunku", "")
            if lc_city is None or not isinstance(lc_city, str) or pd.isna(lc_city):
                lc_city = ""
            else:
                lc_city = lc_city.strip()

            uc_city = row.get("miasto_rozladunku", "")
            if uc_city is None or not isinstance(uc_city, str) or pd.isna(uc_city):
                uc_city = ""
            else:
                uc_city = uc_city.strip()

            coords_zl = location_coords.get((lc, lp, lc_city if lc_city else None))
            coords_roz = location_coords.get((uc, up, uc_city if uc_city else None))
            # Obsługa weryfikacji zgodności miasta i kodu pocztowego
            if lc_city:
                verify_load = verify_city_postal_code_match(lc, lp, lc_city)
                # Sprawdź, czy mamy sugerowane współrzędne dla załadunku
                if not verify_load['is_match'] and verify_load.get('suggested_coords'):
                    # Zastąp współrzędne załadunku sugerowanymi
                    lc_lat, lc_lon = verify_load['suggested_coords']
                    lc_jakosc = 'sugerowane przez weryfikację'
                    lc_zrodlo = 'LOOKUP_sugestia'
                    coords_zl = (lc_lat, lc_lon, lc_jakosc, lc_zrodlo)
                    print(f"Użyto sugerowanych współrzędnych dla załadunku: {coords_zl[:2]}")
            else:
                verify_load = {'is_match': True, 'distance_km': None, 'error': "Brak miasta"}

            if uc_city:
                verify_unload = verify_city_postal_code_match(uc, up, uc_city)
                # Sprawdź, czy mamy sugerowane współrzędne dla rozładunku
                if not verify_unload['is_match'] and verify_unload.get('suggested_coords'):
                    # Zastąp współrzędne rozładunku sugerowanymi
                    uc_lat, uc_lon = verify_unload['suggested_coords']
                    uc_jakosc = 'sugerowane przez weryfikację'
                    uc_zrodlo = 'LOOKUP_sugestia'
                    coords_roz = (uc_lat, uc_lon, uc_jakosc, uc_zrodlo)
                    print(f"Użyto sugerowanych współrzędnych dla rozładunku: {coords_roz[:2]}")
            else:
                verify_unload = {'is_match': True, 'distance_km': None, 'error': "Brak miasta"}

            toll_cost = (get_toll_cost(coords_zl[:2], coords_roz[:2], routing_mode=DEFAULT_ROUTING_MODE)
                         if (coords_zl and coords_roz and None not in coords_zl[:2] and None not in coords_roz[:2])
                         else None)

            if coords_zl and coords_roz and None not in coords_zl[:2] and None not in coords_roz[:2]:
                dist_ptv = get_route_distance(coords_zl[:2], coords_roz[:2], avoid_switzerland=False,
                                              routing_mode=DEFAULT_ROUTING_MODE)
            else:
                dist_ptv = None

            fuel_cost_value = dist_ptv * fuel_cost if dist_ptv is not None else None

            if dist_ptv is not None:
                if dist_ptv <= 350:
                    driver_days = 1
                elif 351 <= dist_ptv <= 500:
                    driver_days = 1.25
                elif 501 <= dist_ptv <= 700:
                    driver_days = 1.5
                elif 701 <= dist_ptv <= 1100:
                    driver_days = 2
                elif 1101 <= dist_ptv <= 1700:
                    driver_days = 3
                elif 1701 <= dist_ptv <= 2300:
                    driver_days = 4
                elif 2301 <= dist_ptv <= 2900:
                    driver_days = 5
                else:
                    driver_days = None
            else:
                driver_days = None

            driver_cost_value = driver_days * driver_cost if driver_days is not None else None

            # Pobierz standardowe stawki
            rates = get_all_rates(lc, lp, uc, up, coords_zl, coords_roz)

            # Pobierz stawki bazujące na regionach
            region_rates = get_region_based_rates(lc, lp, uc, up)

            # Zmiana: podlot jest już bezpośrednio dostępny z historycznych danych
            podlot = rates.get('podlot_historyczny')

            # Jeśli brak podlotu w danych historycznych, użyj domyślnej wartości 100 km
            if podlot is None:
                podlot = 100

            # Oblicz całkowity dystans (PTV + podlot)
            if dist_ptv is not None:
                total_distance = dist_ptv + podlot
            else:
                total_distance = None

            # Obliczenie opłat drogowych za podlot
            oplaty_drogowe_podlot = podlot * 0.30 if podlot is not None else None

            suma_kosztow = 0
            for cost in [toll_cost, fuel_cost_value, driver_cost_value, oplaty_drogowe_podlot]:
                if cost is not None:
                    suma_kosztow += cost

            lc_lat, lc_lon, lc_jakosc, lc_zrodlo = coords_zl if coords_zl else (None, None, 'nieznane', 'brak danych')
            uc_lat, uc_lon, uc_jakosc, uc_zrodlo = coords_roz if coords_roz else (None, None, 'nieznane', 'brak danych')
            lc_coords_str = f"{lc_lat}, {lc_lon}" if None not in (lc_lat, lc_lon) else "Brak danych"
            uc_coords_str = f"{uc_lat}, {uc_lon}" if None not in (uc_lat, uc_lon) else "Brak danych"

            dist_haversine = haversine(coords_zl[:2] if coords_zl else (None, None),
                                       coords_roz[:2] if coords_roz else (None, None))

            gielda_rate = select_best_rate(rates, ['gielda_stawka_3m', 'gielda_stawka_6m', 'gielda_stawka_12m'])
            hist_rate = select_best_rate(rates, ['hist_stawka_3m', 'hist_stawka_6m', 'hist_stawka_12m'])

            # Obliczenie frachtów na podstawie dystansu PTV i dystansu całkowitego
            gielda_fracht_km_ptv = calculate_fracht(dist_ptv, gielda_rate)
            gielda_fracht_km_total = calculate_fracht(total_distance, gielda_rate)
            klient_fracht_km_ptv = calculate_fracht(dist_ptv, hist_rate)
            klient_fracht_km_total = calculate_fracht(total_distance, hist_rate)

            gielda_fracht_3m = rates.get('gielda_fracht_3m')
            hist_fracht_3m = rates.get('hist_fracht_3m')
            # Pobierz współrzędne z verify_load i verify_unload
            city_load_coords = None
            postal_load_coords = None
            if verify_load.get('city_coords'):
                city_load_coords = f"{verify_load['city_coords'][0]}, {verify_load['city_coords'][1]}"
            if verify_load.get('postal_coords'):
                postal_load_coords = f"{verify_load['postal_coords'][0]}, {verify_load['postal_coords'][1]}"

            city_unload_coords = None
            postal_unload_coords = None
            if verify_unload.get('city_coords'):
                city_unload_coords = f"{verify_unload['city_coords'][0]}, {verify_unload['city_coords'][1]}"
            if verify_unload.get('postal_coords'):
                postal_unload_coords = f"{verify_unload['postal_coords'][0]}, {verify_unload['postal_coords'][1]}"

            # Dodaj informację o użyciu sugerowanych współrzędnych
            suggested_coords_info = ""
            if lc_city and not verify_load.get('is_match') and verify_load.get('suggested_coords'):
                suggested_coords_info += "Użyto sugerowanych współrzędnych dla załadunku. "
            if uc_city and not verify_unload.get('is_match') and verify_unload.get('suggested_coords'):
                suggested_coords_info += "Użyto sugerowanych współrzędnych dla rozładunku."

            # Przygotuj wyniki z dodanymi kolumnami regionalnymi
            result_dict = {
                "Kraj zaladunku": lc,
                "Kod zaladunku": lp,
                "Miasto zaladunku": lc_city,
                "Współrzędne zaladunku": lc_coords_str,
                "Jakość geokodowania (zał.)": lc_jakosc,
                "Źródło geokodowania (zał.)": lc_zrodlo,
                "Kraj rozladunku": uc,
                "Kod rozładunku": up,
                "Miasto rozładunku": uc_city,
                "Współrzędne rozładunku": uc_coords_str,
                "Jakość geokodowania (rozł.)": uc_jakosc,
                "Źródło geokodowania (rozł.)": uc_zrodlo,
                "km PTV (tylko ładowne)": format_currency(dist_ptv),
                "km całkowite z podlotem": format_currency(total_distance),  # Nowa kolumna
                "podlot": format_currency(podlot),  # Zmieniona nazwa kolumny
                "km w linii prostej": format_currency(dist_haversine),
                "Dopasowanie (giełda)": rates.get('dopasowanie_gielda'),
                "Giełda_stawka_3m": format_currency(safe_float(rates.get('gielda_stawka_3m'))),
                "Giełda_stawka_6m": format_currency(safe_float(rates.get('gielda_stawka_6m'))),
                "Giełda_stawka_12m": format_currency(safe_float(rates.get('gielda_stawka_12m'))),
                "Giełda - fracht historyczny": format_currency(gielda_fracht_3m),
                "Giełda - fracht proponowany km ładowne": format_currency(gielda_fracht_km_ptv),
                "Giełda - fracht proponowany km całkowite": format_currency(gielda_fracht_km_total),  # Zmieniona nazwa
                "Dopasowanie (Klient)": rates.get('dopasowanie_hist'),
                "Klient_stawka_3m": format_currency(safe_float(rates.get('hist_stawka_3m'))),
                "Klient_stawka_6m": format_currency(safe_float(rates.get('hist_stawka_6m'))),
                "Klient_stawka_12m": format_currency(safe_float(rates.get('hist_stawka_12m'))),
                "Klient - fracht historyczny": format_currency(hist_fracht_3m),
                "Klient - fracht proponowany km ładowne": format_currency(klient_fracht_km_ptv),
                "Klient - fracht proponowany km całkowite": format_currency(klient_fracht_km_total),  # Zmieniona nazwa
                "Relacja": rates.get('relacja'),
                "Tryb wyznaczania trasy": DEFAULT_ROUTING_MODE,
                "opłaty drogowe (EUR)": format_currency(toll_cost),
                "Koszt paliwa (EUR)": format_currency(fuel_cost_value),
                "Koszt kierowcy (EUR)": format_currency(driver_cost_value),
                "Opłaty drogowe podlot (EUR)": format_currency(oplaty_drogowe_podlot),
                "Suma kosztów (EUR)": format_currency(suma_kosztow),
                "Odległość miasto-kod pocztowy załadunku (km)": format_currency(verify_load.get('distance_km')),
                "Zgodność lokalizacji załadunku": "Tak" if verify_load.get('is_match') else "Nie",
                "Koordynaty miasta załadunku": city_load_coords,
                "Koordynaty kodu pocztowego załadunku": postal_load_coords,
                "Odległość miasto-kod pocztowy rozładunku (km)": format_currency(verify_unload.get('distance_km')),
                "Zgodność lokalizacji rozładunku": "Tak" if verify_unload.get('is_match') else "Nie",
                "Koordynaty miasta rozładunku": city_unload_coords,
                "Koordynaty kodu pocztowego rozładunku": postal_unload_coords,
                "Uwagi dotyczące współrzędnych": suggested_coords_info if suggested_coords_info else None,

                # Nowe kolumny z danymi regionalnymi
                "Region załadunku": region_rates.get('region_relacja', "").split(' - ')[0] if ' - ' in region_rates.get(
                    'region_relacja', "") else "",
                "Region rozładunku": region_rates.get('region_relacja', "").split(' - ')[
                    1] if ' - ' in region_rates.get('region_relacja', "") else "",
                "Region - dopasowanie": region_rates.get('region_dopasowanie'),
                "Region - Giełda stawka 3m": format_currency(safe_float(region_rates.get('region_gielda_stawka_3m'))),
                "Region - Giełda stawka 6m": format_currency(safe_float(region_rates.get('region_gielda_stawka_6m'))),
                "Region - Giełda stawka 12m": format_currency(safe_float(region_rates.get('region_gielda_stawka_12m'))),
                "Region - Klient stawka 3m": format_currency(safe_float(region_rates.get('region_klient_stawka_3m'))),
                "Region - Klient stawka 6m": format_currency(safe_float(region_rates.get('region_klient_stawka_6m'))),
                "Region - Klient stawka 12m": format_currency(safe_float(region_rates.get('region_klient_stawka_12m'))),
            }

            results.append(result_dict)

            if i % 10 == 0 or i == len(df) - 1:
                PROGRESS = int((i + 1) / TOTAL_ROWS * 100)
        except Exception as e:
            print(f"Błąd przetwarzania wiersza {i}: {e}")

    print("Tworzenie pliku wynikowego...")
    # Zaktualizuj columns_order, aby zawierał nowe kolumny
    columns_order = [
        "Kraj zaladunku", "Kod zaladunku", "Miasto zaladunku", "Współrzędne zaladunku",
        ##"Jakość geokodowania (zał.)", "Źródło geokodowania (zał.)",
        "Kraj rozladunku", "Kod rozładunku", "Miasto rozładunku", "Współrzędne rozładunku",
        ##"Jakość geokodowania (rozł.)", "Źródło geokodowania (rozł.)",
        "km PTV (tylko ładowne)",
        "km całkowite z podlotem",  # Nowa kolumna
        "podlot",  # Zmieniona nazwa
        # "km w linii prostej",
        # "Dopasowanie (giełda)",
        "Giełda_stawka_3m", "Giełda_stawka_6m", "Giełda_stawka_12m",
        ##"Giełda_stawka_48m",
        "Giełda - fracht historyczny", "Giełda - fracht proponowany km ładowne",
        "Giełda - fracht proponowany km całkowite",  # Zmieniona nazwa
        ##"Dopasowanie (Klient)",
        "Klient_stawka_3m", "Klient_stawka_6m", "Klient_stawka_12m",
        ##"Klient_stawka_48m",
        "Klient - fracht historyczny", "Klient - fracht proponowany km ładowne",
        "Klient - fracht proponowany km całkowite",  # Zmieniona nazwa
        "Relacja",
        ##"Tryb wyznaczania trasy",
        "opłaty drogowe (EUR)", "Koszt paliwa (EUR)", "Koszt kierowcy (EUR)",
        "Opłaty drogowe podlot (EUR)", "Suma kosztów (EUR)",
        "Odległość miasto-kod pocztowy załadunku (km)",
        "Zgodność lokalizacji załadunku",
        "Koordynaty miasta załadunku", "Koordynaty kodu pocztowego załadunku",
        "Odległość miasto-kod pocztowy rozładunku (km)",
        "Zgodność lokalizacji rozładunku",
        "Koordynaty miasta rozładunku", "Koordynaty kodu pocztowego rozładunku",
        "Uwagi dotyczące współrzędnych",

        # Nowe kolumny regionalne
        "Region załadunku",
        "Region rozładunku",
        "Region - dopasowanie",
        "Region - Giełda stawka 3m",
        "Region - Giełda stawka 6m",
        "Region - Giełda stawka 12m",
        "Region - Klient stawka 3m",
        "Region - Klient stawka 6m",
        "Region - Klient stawka 12m",
    ]

    df_out = pd.DataFrame(results)
    for col in columns_order:
        if col not in df_out.columns:
            df_out[col] = None
    df_out = df_out[columns_order]

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
        df_out.to_excel(writer, index=False, sheet_name='Wyniki')
        workbook = writer.book
        worksheet = writer.sheets['Wyniki']

        # Definicje formatów
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#000000',
            'bg_color': '#D9D9D9'
        })

        format_gielda = workbook.add_format({
            'num_format': '#,##0.00',
            'bg_color': '#FCF8C8',
            'align': 'right',
            'border': 1,
            'border_color': '#000000'
        })

        format_hist = workbook.add_format({
            'num_format': '#,##0.00',
            'bg_color': '#D2EED5',
            'align': 'right',
            'border': 1,
            'border_color': '#000000'
        })

        format_default = workbook.add_format({
            'num_format': '#,##0',
            'align': 'right',
            'border': 1,
            'border_color': '#000000'
        })

        format_fracht_gielda = workbook.add_format({
            'num_format': '#,##0',
            'bg_color': '#F5E737',
            'align': 'right',
            'border': 1,
            'border_color': '#000000'
        })

        format_koszty = workbook.add_format({
            'num_format': '#,##0',
            'bg_color': '#FFC1C1',
            'align': 'right',
            'border': 1,
            'border_color': '#000000'
        })

        format_koszty_suma = workbook.add_format({
            'num_format': '#,##0',
            'bg_color': '#FF3B3B',
            'align': 'right',
            'border': 1,
            'border_color': '#000000'
        })

        format_fracht_klient = workbook.add_format({
            'num_format': '#,##0',
            'bg_color': '#48BC56',
            'align': 'right',
            'border': 1,
            'border_color': '#000000'
        })

        text_format = workbook.add_format({
            'num_format': '@',
            'align': 'left',
            'border': 1,
            'border_color': '#000000'
        })

        # Nagłówki
        for col_num, value in enumerate(df_out.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Kolumny tekstowe
        text_columns = [
            "Kraj zaladunku", "Kod zaladunku", "Miasto zaladunku", "Współrzędne zaladunku",
            "Jakość geokodowania (zał.)", "Źródło geokodowania (zał.)",
            "Kraj rozladunku", "Kod rozładunku", "Miasto rozładunku", "Współrzędne rozładunku",
            "Jakość geokodowania (rozł.)", "Źródło geokodowania (rozł.)",
            "Dopasowanie (giełda)", "Dopasowanie (Klient)", "Relacja", "Tryb wyznaczania trasy",
            "Zgodność lokalizacji załadunku", "Zgodność lokalizacji rozładunku", "Uwagi dotyczące współrzędnych",
            "Koordynaty miasta załadunku", "Koordynaty kodu pocztowego załadunku",
            "Koordynaty miasta rozładunku", "Koordynaty kodu pocztowego rozładunku",
            "Region załadunku", "Region rozładunku", "Region - dopasowanie"
        ]

        # Kolumny stawek giełdy
        gielda_stawki_columns = [
            "Giełda_stawka_3m", "Giełda_stawka_6m", "Giełda_stawka_12m",
            "Region - Giełda stawka 3m", "Region - Giełda stawka 6m", "Region - Giełda stawka 12m"
        ]

        # Kolumny stawek klienta
        klient_stawki_columns = [
            "Klient_stawka_3m", "Klient_stawka_6m", "Klient_stawka_12m",
            "Region - Klient stawka 3m", "Region - Klient stawka 6m", "Region - Klient stawka 12m"
        ]

        # Kolumny frachtów giełdy
        gielda_fracht_columns = [
            "Giełda - fracht historyczny", "Giełda - fracht proponowany km ładowne",
            "Giełda - fracht proponowany km całkowite"  # Zmieniona nazwa
        ]

        # Kolumny frachtów klienta
        klient_fracht_columns = [
            "Klient - fracht historyczny", "Klient - fracht proponowany km ładowne",
            "Klient - fracht proponowany km całkowite"  # Zmieniona nazwa
        ]

        # Kolumny kosztów
        koszty_columns = [
            "opłaty drogowe (EUR)", "Koszt paliwa (EUR)", "Koszt kierowcy (EUR)", "Opłaty drogowe podlot (EUR)"
        ]

        # Kolumny dystansów
        dystans_columns = [
            "km PTV (tylko ładowne)", "km całkowite z podlotem", "podlot", "km w linii prostej",
            "Odległość miasto-kod pocztowy załadunku (km)", "Odległość miasto-kod pocztowy rozładunku (km)"
        ]

        # Mapowanie kolumn na formaty
        for row in range(1, len(df_out) + 1):
            for col_num, column in enumerate(df_out.columns):
                cell_value = df_out.iloc[row - 1, col_num]

                # Obsługa wartości pustych, None lub NaN
                if cell_value is None or pd.isna(cell_value) or (
                        isinstance(cell_value, str) and cell_value.strip() == ''):
                    if column in text_columns:
                        worksheet.write_blank(row, col_num, None, text_format)
                    elif column in gielda_stawki_columns:
                        worksheet.write_blank(row, col_num, None, format_gielda)
                    elif column in klient_stawki_columns:
                        worksheet.write_blank(row, col_num, None, format_hist)
                    elif column in gielda_fracht_columns:
                        worksheet.write_blank(row, col_num, None, format_fracht_gielda)
                    elif column in klient_fracht_columns:
                        worksheet.write_blank(row, col_num, None, format_fracht_klient)
                    elif column in koszty_columns:
                        worksheet.write_blank(row, col_num, None, format_koszty)
                    elif column == "Suma kosztów (EUR)":
                        worksheet.write_blank(row, col_num, None, format_koszty_suma)
                    elif column in dystans_columns:
                        worksheet.write_blank(row, col_num, None, format_default)
                    else:
                        worksheet.write_blank(row, col_num, None, format_default)
                    continue

                # Wybór odpowiedniego formatu na podstawie nazwy kolumny
                if column in text_columns:
                    worksheet.write(row, col_num, cell_value, text_format)
                elif column in gielda_stawki_columns:
                    try:
                        val = float(cell_value) if cell_value is not None else None
                        worksheet.write(row, col_num, val, format_gielda)
                    except (ValueError, TypeError):
                        worksheet.write_blank(row, col_num, None, format_gielda)
                elif column in klient_stawki_columns:
                    try:
                        val = float(cell_value) if cell_value is not None else None
                        worksheet.write(row, col_num, val, format_hist)
                    except (ValueError, TypeError):
                        worksheet.write_blank(row, col_num, None, format_hist)
                elif column in gielda_fracht_columns:
                    try:
                        val = float(cell_value) if cell_value is not None else None
                        worksheet.write(row, col_num, val, format_fracht_gielda)
                    except (ValueError, TypeError):
                        worksheet.write_blank(row, col_num, None, format_fracht_gielda)
                elif column in klient_fracht_columns:
                    try:
                        val = float(cell_value) if cell_value is not None else None
                        worksheet.write(row, col_num, val, format_fracht_klient)
                    except (ValueError, TypeError):
                        worksheet.write_blank(row, col_num, None, format_fracht_klient)
                elif column in koszty_columns:
                    try:
                        val = float(cell_value) if cell_value is not None else None
                        worksheet.write(row, col_num, val, format_koszty)
                    except (ValueError, TypeError):
                        worksheet.write_blank(row, col_num, None, format_koszty)
                elif column == "Suma kosztów (EUR)":
                    try:
                        val = float(cell_value) if cell_value is not None else None
                        worksheet.write(row, col_num, val, format_koszty_suma)
                    except (ValueError, TypeError):
                        worksheet.write_blank(row, col_num, None, format_koszty_suma)
                elif column in dystans_columns:
                    try:
                        val = float(cell_value) if cell_value is not None else None
                        worksheet.write(row, col_num, val, format_default)
                    except (ValueError, TypeError):
                        worksheet.write_blank(row, col_num, None, format_default)
                else:
                    # Domyślny format dla pozostałych kolumn
                    try:
                        if isinstance(cell_value, (int, float)):
                            worksheet.write(row, col_num, cell_value, format_default)
                        else:
                            val = float(cell_value) if cell_value is not None else None
                            worksheet.write(row, col_num, val, format_default)
                    except (ValueError, TypeError):
                        worksheet.write_blank(row, col_num, None, format_default)

                    # Dostosowanie szerokości kolumn
                worksheet.set_column(0, len(df_out.columns) - 1, 15)

                # Dostosowanie szerokości kolumn z długimi nazwami
                for col_num, column in enumerate(df_out.columns):
                    if len(column) > 15:
                        worksheet.set_column(col_num, col_num, len(column) * 0.9)

    buffer.seek(0)
    global RESULT_EXCEL
    RESULT_EXCEL = buffer.read()
    PROGRESS = 100


def save_caches():
    try:
        geo_dict = {key: geo_cache[key] for key in geo_cache}
        route_dict = {key: route_cache[key] for key in route_cache}
        joblib.dump(geo_dict, 'geo_cache_backup.joblib')
        joblib.dump(route_dict, 'route_cache_backup.joblib')
        print("Zapisano pamięć podręczną.")
    except Exception as e:
        print(f"Błąd zapisywania pamięci podręcznej: {e}")


def load_caches():
    try:
        if os.path.exists('geo_cache_backup.joblib'):
            geo_cache_data = joblib.load('geo_cache_backup.joblib')
            for k, v in geo_cache_data.items():
                geo_cache[k] = v
            print(f"Wczytano {len(geo_cache_data)} elementów geo_cache.")
        if os.path.exists('route_cache_backup.joblib'):
            route_cache_data = joblib.load('route_cache_backup.joblib')
            for k, v in route_cache_data.items():
                route_cache[k] = v
            print(f"Wczytano {len(route_cache_data)} elementów route_cache.")
    except Exception as e:
        print(f"Błąd wczytywania pamięci podręcznej: {e}")


app = Flask(__name__)


@app.route("/show_cache")
def show_cache():
    cache_info = {k: geo_cache[k] for k in geo_cache}
    return jsonify(cache_info)


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files.get("file")
        if file:
            global PROGRESS, RESULT_EXCEL
            PROGRESS = 0
            RESULT_EXCEL = None
            fuel_cost_str = request.form.get("fuel_cost", "0.40")
            try:
                fuel_cost = float(fuel_cost_str)
            except ValueError:
                fuel_cost = 0.40
            driver_cost_str = request.form.get("driver_cost", "130")
            try:
                driver_cost = float(driver_cost_str)
            except ValueError:
                driver_cost = 130
            file_bytes = io.BytesIO(file.read())
            file_bytes.seek(0)
            threading.Thread(target=background_processing, args=(file_bytes, fuel_cost, driver_cost)).start()
            return '''<html><body>
                      <h2>Plik przesłany i przetwarzany.</h2>
                      <p id="postep">Trwa przetwarzanie...</p>
                      <div id="download-link" style="display:none;">
                        <a href="/download">📥 Pobierz wynikowy plik Excel</a>
                      </div>
                      <div id="geocode-link" style="display:none;">
                        <a href="/ungeocoded_locations">🌍 Uzupełnij brakujące lokalizacje</a>
                      </div>
                      <div>
                        <p><a href="/test_route_form">🧪 Testuj trasę</a></p>
                      </div>
                      <script>
                      function checkProgress() {
  fetch('/progress')
    .then(response => response.json())
    .then(data => {
      let message = `⏳ Przeliczanie: ${data.current} z ${data.total} (${data.progress}%)`;
      if (data.geocoding_progress !== undefined) {
        message += ` | Geokodowanie: ${data.geocoding_progress}%`;
      }
      document.getElementById("postep").innerText = message;
      if (data.progress >= 100) {
        document.getElementById("postep").innerText = "✅ Gotowe! Możesz pobrać wynik.";
        document.getElementById("download-link").style.display = "block";
        clearInterval(timer);
      }
      if (data.progress === -2) {
        document.getElementById("postep").innerText = "⚠️ Wymagane ręczne uzupełnienie lokalizacji!";
        document.getElementById("geocode-link").style.display = "block";
        clearInterval(timer);
      }
    });
}
                      let timer = setInterval(checkProgress, 1000);
                      </script>
                      </body></html>'''
        return '''<html><body>
                  <h1>Nie wybrano pliku</h1>
                  <p>Wróć i wybierz plik Excel do przetworzenia.</p>
                  <a href="/">Powrót</a>
                  </body></html>'''
    return '''<html><body>
              <h1>Wgraj plik Excel z przetargami</h1>
              <form method="post" enctype="multipart/form-data">
                  <input type="file" name="file"><br>
                  <label for="fuel_cost">Koszt paliwa (€/km):</label>
                  <input type="number" step="0.01" name="fuel_cost" value="0.40"><br>
                  <label for="driver_cost">Koszt kierowcy (€/dzień):</label>
                  <input type="number" step="0.01" name="driver_cost" value="130"><br>
                  <input type="submit" value="Prześlij">
              </form>
              <p><a href="/test_route_form">🧪 Testuj trasę</a></p>
              <p><a href="/save_cache">💾 Zapisz pamięć podręczną</a></p>
              </body></html>'''


@app.route("/download")
def download():
    if RESULT_EXCEL and len(RESULT_EXCEL) > 100:
        return send_file(io.BytesIO(RESULT_EXCEL), download_name="wycena.xlsx", as_attachment=True)
    return "Jeszcze nie gotowe."


@app.route("/progress")
def progress():
    geocoding_progress = 0
    if GEOCODING_TOTAL > 0:
        geocoding_progress = int((GEOCODING_CURRENT / GEOCODING_TOTAL) * 100)
    return jsonify(
        progress=PROGRESS,
        current=CURRENT_ROW,
        total=TOTAL_ROWS,
        geocoding_progress=geocoding_progress,
        error=PROGRESS == -1 or PROGRESS == -2
    )


@app.route("/save_cache")
def save_cache_endpoint():
    save_caches()
    return "Zapisano pamięć podręczną."


@app.route("/ungeocoded_locations", methods=["GET", "POST"])
def ungeocoded_locations():
    if request.method == "POST":
        file = request.files.get('file')
        if file:
            file_bytes = io.BytesIO(file.read())
            file_bytes.seek(0)
            try:
                df = pd.read_excel(file_bytes, dtype=str)
                # Upewnij się, że nazwy kolumn są spójne
                column_mapping = {}
                for col in df.columns:
                    normalized_col = col.lower().strip()
                    if " " in normalized_col:
                        normalized_col = normalized_col.replace(" ", "_")
                    column_mapping[col] = normalized_col

                df = df.rename(columns=column_mapping)
                print("Kolumny po normalizacji:", list(df.columns))

                # Sprawdź czy wymagane kolumny istnieją
                required_columns = [
                    'kraj_zaladunku', 'kod_pocztowy_zaladunku',
                    'kraj_rozladunku', 'kod_pocztowy_rozladunku'
                ]

                # Przekształć nazwy kolumn za pomocą mapowania, jeśli potrzeba
                for i, col in enumerate(required_columns):
                    if col not in df.columns:
                        alt_col = col.replace("_", " ")
                        if alt_col in df.columns:
                            required_columns[i] = alt_col

                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    return f"Brak wymaganych kolumn: {', '.join(missing_columns)}", 400

                # Synchronizuj cache przed sprawdzaniem
                sync_geo_cache_with_lookup()

                # Pobierz nierozpoznane lokalizacje
                ungeocoded = get_ungeocoded_locations(df)

                # Jeśli wszystko zostało zgeokodowane
                if not ungeocoded:
                    return '''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Geokodowanie zakończone</title>
                        <style>
                            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                        </style>
                    </head>
                    <body>
                        <h1>✅ Wszystkie lokalizacje zostały poprawnie zgeokodowane!</h1>
                        <p>Możesz teraz kontynuować przetwarzanie pliku.</p>
                        <p><a href="/">« Powrót do strony głównej</a></p>
                    </body>
                    </html>
                    '''

                return render_template_string('''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Nierozpoznane lokalizacje</title>
                        <style>
                            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                            table { width: 100%; border-collapse: collapse; }
                            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                            th { background-color: #f2f2f2; }
                            .success { color: green; font-weight: bold; }
                            .error { color: red; font-weight: bold; }
                        </style>
                    </head>
                    <body>
                        <h1>Nierozpoznane lokalizacje</h1>
                        <p>Znaleziono <span class="error">{{ ungeocoded|length }}</span> lokalizacji, które wymagają ręcznego geokodowania.</p>
                        <table>
                            <thead>
                                <tr>
                                    <th>Kraj</th>
                                    <th>Kod pocztowy</th>
                                    <th>Miasto</th>
                                    <th>Klucz</th>
                                    <th>Warianty zapytań</th>
                                    <th>Akcje</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for loc in ungeocoded %}
                                <tr>
                                    <td>{{ loc.country }}</td>
                                    <td>{{ loc.postal_code }}</td>
                                    <td>{{ loc.city }}</td>
                                    <td>{{ loc.key }}</td>
                                    <td>
                                        {% for variant in loc.query_variants %}
                                            <div>{{ variant[0] }}<br/><small>(klucz: {{ variant[1] }})</small></div>
                                        {% endfor %}
                                    </td>
                                    <td>
                                        <a href="#" onclick="showManualInput('{{ loc.key }}', '{{ loc.country }}', '{{ loc.postal_code }}', '{{ loc.city }}')">
                                            Dodaj współrzędne
                                        </a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                        <div id="manualInputModal" style="display:none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
                            <div style="background: white; margin: 100px auto; padding: 20px; width: 400px; border-radius: 5px;">
                                <h2>Dodaj współrzędne ręcznie</h2>
                                <form id="manualCoordForm" onsubmit="submitCoordinates(event)">
                                    <input type="hidden" id="locationKey" name="key">
                                    <label>Kraj: <input type="text" id="countryInput" readonly></label><br>
                                    <label>Kod pocztowy: <input type="text" id="postalCodeInput" readonly></label><br>
                                    <label>Miasto: <input type="text" id="cityInput" readonly></label><br>
                                    <label>Szerokość geograficzna: <input type="text" id="latInput" required></label><br>
                                    <label>Długość geograficzna: <input type="text" id="lonInput" required></label><br>
                                    <button type="submit">Zapisz współrzędne</button>
                                    <button type="button" onclick="closeModal()">Anuluj</button>
                                </form>
                            </div>
                        </div>
                        <div style="margin-top: 20px;">
                            <p><a href="/">« Powrót do strony głównej</a></p>
                        </div>
                        <script>
                        function showManualInput(key, country, postalCode, city) {
                            document.getElementById('locationKey').value = key;
                            document.getElementById('countryInput').value = country;
                            document.getElementById('postalCodeInput').value = postalCode;
                            document.getElementById('cityInput').value = city;
                            document.getElementById('manualInputModal').style.display = 'block';
                        }
                        function closeModal() {
                            document.getElementById('manualInputModal').style.display = 'none';
                        }
                        function submitCoordinates(event) {
                            event.preventDefault();
                            const key = document.getElementById('locationKey').value;
                            const lat = parseFloat(document.getElementById('latInput').value);
                            const lon = parseFloat(document.getElementById('lonInput').value);
                            fetch('/save_manual_coordinates', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ key: key, latitude: lat, longitude: lon })
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    alert('Współrzędne zostały zapisane!');
                                    location.reload();
                                } else {
                                    alert('Błąd: ' + data.message);
                                }
                            });
                        }
                        </script>
                    </body>
                    </html>
                ''', ungeocoded=ungeocoded)
            except Exception as e:
                return f"Błąd przetwarzania pliku: {str(e)}", 500
        return "Brak pliku", 400
    else:
        return '''<html><body>
                  <h1>Wgraj plik Excel, aby sprawdzić nierozpoznane lokalizacje</h1>
                  <form method="post" enctype="multipart/form-data">
                  <input type="file" name="file">
                  <input type="submit" value="Prześlij">
                  </form>
                  </body></html>'''


@app.route("/save_manual_coordinates", methods=['POST'])
def save_manual_coordinates():
    data = request.json
    try:
        key = data.get('key')
        lat = data.get('latitude')
        lon = data.get('longitude')
        if not key or lat is None or lon is None:
            return jsonify({'success': False, 'message': 'Nieprawidłowe dane'})
        geo_cache[key] = (lat, lon, 'ręczne', 'użytkownik')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route("/test_route_form")
def test_route_form():
    return '''<html>
            <head>
                <title>Test trasy</title>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                    .form-group { margin-bottom: 15px; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input[type="text"] { width: 300px; padding: 8px; }
                    button { padding: 10px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
                    #result { margin-top: 20px; border: 1px solid #ddd; padding: 15px; display: none; }
                    .back-link { margin-top: 20px; }
                    select { width: 315px; padding: 8px; }
                </style>
            </head>
            <body>
                <h1>Test trasy</h1>
                <div class="form-group">
                    <label for="from">Punkt początkowy (szerokość,długość):</label>
                    <input type="text" id="from" name="from" value="50.433792,7.466426" placeholder="np. 50.433792,7.466426">
                </div>
                <div class="form-group">
                    <label for="to">Punkt końcowy (szerokość,długość):</label>
                    <input type="text" id="to" name="to" value="48.237324,13.824039" placeholder="np. 48.237324,13.824039">
                </div>
                <div class="form-group">
                    <label for="routingMode">Tryb wyznaczania trasy:</label>
                    <select id="routingMode" name="routingMode">
                        <option value="MONETARY" selected>Ekonomiczna (MONETARY)</option>
                        <option value="SHORTEST">Najkrótsza (SHORTEST)</option>
                        <option value="FAST">Najszybsza (FAST)</option>
                        <option value="SHORT">Krótka (SHORT)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="avoid_switzerland"> Omijaj Szwajcarię
                    </label>
                </div>
                <button onclick="testRoute()">Testuj trasę</button>
                <div id="result"></div>
                <div class="back-link">
                    <a href="/">« Powrót do strony głównej</a>
                </div>
                <script>
                function testRoute() {
                    const from = document.getElementById('from').value;
                    const to = document.getElementById('to').value;
                    const mode = document.getElementById('routingMode').value;
                    const avoid = document.getElementById('avoid_switzerland').checked;
                    document.getElementById('result').style.display = 'block';
                    document.getElementById('result').innerHTML = '<p>Obliczanie trasy...</p>';
                    fetch(`/test_truck_route?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&mode=${encodeURIComponent(mode)}&avoid=${avoid}`)
                        .then(response => response.json())
                        .then(data => {
                            let resultHtml = '';
                            if (data.status === 'success') {
                                resultHtml = `
                                    <h3>Wyniki:</h3>
                                    <p><strong>Dystans:</strong> ${data.dystans_km.toFixed(2)} km</p>
                                    <p><strong>Czas przejazdu:</strong> ${data.czas_min.toFixed(2)} min (${(data.czas_min/60).toFixed(2)} godz.)</p>
                                `;
                                if (data.kraje && data.kraje.length > 0) {
                                    resultHtml += `<p><strong>Kraje na trasie:</strong> ${data.kraje.join(', ')}</p>`;
                                }
                            } else {
                                resultHtml = `<p><strong>Błąd:</strong> ${data.message}</p>`;
                            }
                            document.getElementById('result').innerHTML = resultHtml;
                        })
                        .catch(error => {
                            document.getElementById('result').innerHTML = `<p><strong>Błąd:</strong> ${error}</p>`;
                        });
                }
                </script>
            </body>
            </html>'''


@app.route("/test_truck_route")
def test_truck_route():
    coord_from = request.args.get('from', '50.433792,7.466426')
    coord_to = request.args.get('to', '48.237324,13.824039')
    routing_mode = request.args.get('mode', DEFAULT_ROUTING_MODE)
    avoid_switzerland = request.args.get('avoid', 'false').lower() in ('true', 'yes', '1')
    try:
        lat1, lon1 = map(float, coord_from.split(','))
        lat2, lon2 = map(float, coord_to.split(','))
        cache_key = f"{lat1:.6f},{lon1:.6f}_{lat2:.6f},{lon2:.6f}_{avoid_switzerland}_{routing_mode}"
        if cache_key in route_cache:
            dist = route_cache[cache_key]
            travel_time = (dist / 80) * 60 if dist else 0
            return jsonify({
                'status': 'success',
                'dystans_km': dist,
                'czas_min': travel_time,
                'kraje': ["Z cache - brak informacji o krajach"]
            })
        base_url = "https://api.myptv.com/routing/v1/routes"
        params = {
            "waypoints": [f"{lat1},{lon1}", f"{lat2},{lon2}"],
            "results": "BORDER_EVENTS,POLYLINE",
            "options[routingMode]": routing_mode,
            "options[trafficMode]": "AVERAGE"
        }
        if avoid_switzerland:
            params["options[prohibitedCountries]"] = "CH"
        headers = {"apiKey": PTV_API_KEY}
        print(f"Wysyłanie zapytania do API PTV z parametrami: {params}")
        response = requests.get(base_url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()
            dist = data.get("distance", 0) / 1000
            route_cache[cache_key] = dist
            return jsonify({
                'status': 'success',
                'dystans_km': dist,
                'czas_min': data.get("travelTime", 0) / 60,
                'kraje': [event.get("country") for event in data.get("borderEvents", [])]
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f"Błąd API: {response.status_code} - {response.text}"
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"Błąd: {str(e)}"
        })


def background_processing(file_stream, fuel_cost, driver_cost):
    global RESULT_EXCEL, PROGRESS
    try:
        print("Rozpoczynam przetwarzanie pliku...")
        df = pd.read_excel(file_stream, dtype=str)
        df.columns = df.columns.str.lower().str.replace(" ", "_").str.strip()
        print("Przekształcone kolumny:", list(df.columns))
        try:
            process_przetargi(df, fuel_cost, driver_cost)
            save_caches()
            print("Przetwarzanie zakończone.")
        except GeocodeException as ge:
            PROGRESS = -2
            print(f"Znaleziono {len(ge.ungeocoded_locations)} nierozpoznanych lokalizacji")
    except Exception as e:
        print(f"Błąd przetwarzania: {e}")
        PROGRESS = -1


if __name__ == '__main__':
    load_caches()
    load_region_mapping()  # Dodaj tę linię, aby wczytać mapowania regionów
    log = logging.getLogger('werkzeug')


    class FilterProgress(logging.Filter):
        def filter(self, record):
            return "/progress" not in record.getMessage()


    log.addFilter(FilterProgress())
    app.run(debug=True)
