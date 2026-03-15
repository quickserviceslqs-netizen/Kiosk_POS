"""Internationalization utilities for Kiosk POS."""
from __future__ import annotations

import json
import os
from typing import Dict, Any, Optional
from database.init_db import get_connection


# Default translations (English)
DEFAULT_TRANSLATIONS = {
    "en": {
        "app_name": "Kiosk POS",
        "item_name": "Item Name",
        "category": "Category",
        "price": "Price",
        "quantity": "Quantity",
        "total": "Total",
        "save": "Save",
        "cancel": "Cancel",
        "delete": "Delete",
        "edit": "Edit",
        "add": "Add",
        "search": "Search",
        "settings": "Settings",
        "inventory": "Inventory",
        "reports": "Reports",
        "dashboard": "Dashboard",
        "logout": "Logout",
        "login": "Login",
        "username": "Username",
        "password": "Password",
        "error": "Error",
        "success": "Success",
        "warning": "Warning",
        "confirmation": "Confirmation",
        "required_field": "This field is required",
        "invalid_input": "Invalid input",
        "item_created": "Item created successfully",
        "item_updated": "Item updated successfully",
        "item_deleted": "Item deleted successfully",
        "currency_symbol": "$",
        "currency_code": "USD",
        "date_format": "%Y-%m-%d",
        "time_format": "%H:%M:%S",
        "datetime_format": "%Y-%m-%d %H:%M:%S",
    },
    "es": {
        "app_name": "Kiosk POS",
        "item_name": "Nombre del Artículo",
        "category": "Categoría",
        "price": "Precio",
        "quantity": "Cantidad",
        "total": "Total",
        "save": "Guardar",
        "cancel": "Cancelar",
        "delete": "Eliminar",
        "edit": "Editar",
        "add": "Agregar",
        "search": "Buscar",
        "settings": "Configuración",
        "inventory": "Inventario",
        "reports": "Reportes",
        "dashboard": "Panel de Control",
        "logout": "Cerrar Sesión",
        "login": "Iniciar Sesión",
        "username": "Usuario",
        "password": "Contraseña",
        "error": "Error",
        "success": "Éxito",
        "warning": "Advertencia",
        "confirmation": "Confirmación",
        "required_field": "Este campo es obligatorio",
        "invalid_input": "Entrada inválida",
        "item_created": "Artículo creado exitosamente",
        "item_updated": "Artículo actualizado exitosamente",
        "item_deleted": "Artículo eliminado exitosamente",
        "currency_symbol": "€",
        "currency_code": "EUR",
        "date_format": "%d/%m/%Y",
        "time_format": "%H:%M:%S",
        "datetime_format": "%d/%m/%Y %H:%M:%S",
    },
    "sw": {  # Swahili
        "app_name": "Kiosk POS",
        "item_name": "Jina la Bidhaa",
        "category": "Kategoria",
        "price": "Bei",
        "quantity": "Kiasi",
        "total": "Jumla",
        "save": "Hifadhi",
        "cancel": "Ghairi",
        "delete": "Futa",
        "edit": "Hariri",
        "add": "Ongeza",
        "search": "Tafuta",
        "settings": "Mipangilio",
        "inventory": "Hekalu",
        "reports": "Ripoti",
        "dashboard": "Dashibodi",
        "logout": "Ondoka",
        "login": "Ingia",
        "username": "Jina la Mtumiaji",
        "password": "Nenosiri",
        "error": "Kosa",
        "success": "Mafanikio",
        "warning": "Onyo",
        "confirmation": "Uthibitisho",
        "required_field": "Sehemu hii inahitajika",
        "invalid_input": "Ingizo batili",
        "item_created": "Bidhaa imeundwa vizuri",
        "item_updated": "Bidhaa imesasishwa vizuri",
        "item_deleted": "Bidhaa imefutwa vizuri",
        "currency_symbol": "KSh",
        "currency_code": "KES",
        "date_format": "%d/%m/%Y",
        "time_format": "%H:%M:%S",
        "datetime_format": "%d/%m/%Y %H:%M:%S",
    }
}


class I18N:
    """Internationalization manager for Kiosk POS."""

    def __init__(self, language: str = "en"):
        self.current_language = language
        self.translations = DEFAULT_TRANSLATIONS.copy()
        self._load_custom_translations()

    def _load_custom_translations(self) -> None:
        """Load custom translations from files if available."""
        translations_dir = os.path.join(os.path.dirname(__file__), "..", "translations")
        if os.path.exists(translations_dir):
            for filename in os.listdir(translations_dir):
                if filename.endswith(".json"):
                    lang_code = filename[:-5]  # Remove .json
                    try:
                        with open(os.path.join(translations_dir, filename), 'r', encoding='utf-8') as f:
                            custom_translations = json.load(f)
                            if lang_code in self.translations:
                                self.translations[lang_code].update(custom_translations)
                            else:
                                self.translations[lang_code] = custom_translations
                    except Exception:
                        # Ignore invalid translation files
                        pass

    def set_language(self, language: str) -> None:
        """Set the current language."""
        if language in self.translations:
            self.current_language = language
        else:
            self.current_language = "en"  # Fallback to English

    def get(self, key: str, default: str = "") -> str:
        """Get translated text for a key."""
        return self.translations.get(self.current_language, {}).get(key, default)

    def get_available_languages(self) -> list[str]:
        """Get list of available languages."""
        return list(self.translations.keys())

    def get_currency_symbol(self) -> str:
        """Get the currency symbol for current language."""
        return self.get("currency_symbol", "$")

    def get_currency_code(self) -> str:
        """Get the currency code for current language."""
        return self.get("currency_code", "USD")

    def format_currency(self, amount: float) -> str:
        """Format amount with current currency symbol."""
        symbol = self.get_currency_symbol()
        return f"{symbol}{amount:.2f}"

    def get_date_format(self) -> str:
        """Get the date format for current language."""
        return self.get("date_format", "%Y-%m-%d")

    def get_time_format(self) -> str:
        """Get the time format for current language."""
        return self.get("time_format", "%H:%M:%S")

    def get_datetime_format(self) -> str:
        """Get the datetime format for current language."""
        return self.get("datetime_format", "%Y-%m-%d %H:%M:%S")


# Global i18n instance
_i18n = I18N()


def get_text(key: str, default: str = "") -> str:
    """Get translated text for a key."""
    return _i18n.get(key, default)


def set_language(language: str) -> None:
    """Set the current language globally."""
    _i18n.set_language(language)


def get_current_language() -> str:
    """Get the current language."""
    return _i18n.current_language


def get_available_languages() -> list[str]:
    """Get list of available languages."""
    return _i18n.get_available_languages()


def get_currency_symbol() -> str:
    """Get the current currency symbol."""
    # First try database setting, then fall back to language default
    try:
        from database.init_db import get_connection
        with get_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency_symbol'")
            row = cursor.fetchone()
            if row:
                return row['value'] if isinstance(row, dict) else row[0]
    except Exception:
        pass
    return _i18n.get_currency_symbol()


def get_currency_code() -> str:
    """Get the current currency code."""
    # First try database setting, then fall back to language default
    try:
        from database.init_db import get_connection
        with get_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency_code'")
            row = cursor.fetchone()
            if row:
                return row['value'] if isinstance(row, dict) else row[0]
    except Exception:
        pass
    return _i18n.get_currency_code()


def get_default_currency_symbol_for_code(code: str) -> str:
    """Get the default currency symbol for a given currency code."""
    # Comprehensive currency symbol mapping covering major world currencies
    _SYMBOL_MAP: dict = {
        # Major World Currencies
        'USD': '$',     'EUR': '€',     'GBP': '£',     'JPY': '¥',
        'CNY': '¥',     'INR': '₹',     'KRW': '₩',     'RUB': '₽',
        
        # Dollar Family
        'CAD': 'C$',    'AUD': 'A$',    'NZD': 'NZ$',   'HKD': 'HK$',
        'SGD': 'S$',    'TWD': 'NT$',   'BRL': 'R$',    'MXN': 'MX$',
        
        # European Currencies  
        'CHF': 'CHF',   'SEK': 'kr',    'NOK': 'kr',    'DKK': 'kr',
        'PLN': 'zł',    'CZK': 'Kč',    'HUF': 'Ft',    'RON': 'lei',
        'BGN': 'лв',    'HRK': 'kn',    'ISK': 'kr',    'TRY': '₺',
        
        # Asian Currencies
        'THB': '฿',     'PHP': '₱',     'MYR': 'RM',    'IDR': 'Rp',
        'VND': '₫',     'KHR': '៛',     'LAK': '₭',     'MMK': 'K',
        'BDT': '৳',     'PKR': '₨',     'LKR': '₨',     'NPR': '₨',
        'AFN': '؋',     'IRR': '﷼',     'ILS': '₪',     'JOD': 'JD',
        'KWD': 'KD',    'BHD': 'BD',    'QAR': 'QR',    'AED': 'AED',
        'SAR': 'SR',    'OMR': 'RO',    'YER': 'YER',   'LBP': 'LBP',
        'SYP': 'SYP',   'IQD': 'IQD',   
        
        # African Currencies
        'ZAR': 'R',     'NGN': '₦',     'GHS': 'GH₵',   'KES': 'KSh',
        'TZS': 'TSh',   'UGX': 'USh',   'RWF': 'FRw',   'ETB': 'Br',
        'EGP': '£',     'MAD': 'DH',    'TND': 'DT',    'DZD': 'DA',
        'LYD': 'LD',    'SDG': 'SDG',   'SOS': 'S',     'DJF': 'Fdj',
        'ERN': 'Nfk',   'MWK': 'MK',    'ZMW': 'ZK',    'BWP': 'P',
        'SZL': 'L',     'LSL': 'L',     'NAD': 'N$',    'AOA': 'Kz',
        'MZN': 'MT',    'MGA': 'Ar',    'KMF': 'CF',    'SCR': '₨',
        'MUR': '₨',     'MVR': 'Rf',    
        
        # Central & South American Currencies
        'ARS': 'AR$',   'CLP': 'CL$',   'COP': 'CO$',   'PEN': 'S/',
        'UYU': '$U',    'PYG': '₲',     'BOB': 'Bs',    'VES': 'Bs',
        'GYD': 'G$',    'SRD': 'SR$',   'TTD': 'TT$',   
        
        # Central American & Caribbean
        'MXP': '$',     'GTQ': 'Q',     'BZD': 'BZ$',   'HNL': 'L',
        'NIO': 'C$',    'CRC': '₡',     'PAB': 'B/.',   'JMD': 'J$',
        'HTG': 'G',     'DOP': 'RD$',   'CUP': '₱',     'BSD': 'B$',
        'BBD': 'Bds$',  'XCD': 'EC$',   
        
        # Pacific & Other Regions  
        'FJD': 'FJ$',   'TOP': 'T$',    'WST': 'WS$',   'VUV': 'VT',
        'PGK': 'K',     'SBD': 'SI$',   'NCL': 'F',     'XPF': 'F',
        
        # Uncommon but Valid Currencies
        'ALL': 'L',     'AMD': '֏',     'AZN': '₼',     'BAM': 'KM',
        'BYN': 'Br',    'GEL': '₾',     'KGS': 'с',     'KZT': '₸',
        'MDL': 'L',     'MKD': 'ден',   'RSD': 'дин',   'TJS': 'SM',
        'TMT': 'T',     'UAH': '₴',     'UZS': 'soʻm',  
        
        # Additional Coverage
        'AWG': 'ƒ',     'ANG': 'ƒ',     'BMD': 'BD$',   'KYD': 'CI$',
        'XOF': 'CFA',   'XAF': 'FCFA',  'XPF': 'CFP',   'BTN': 'Nu',
        'BND': 'B$',    'MOP': 'MOP$',  'LRD': 'L$',    'SLE': 'Le',
        
        # Previously Missing Currencies - Wave 2
        'ARS': 'AR$',   'BIF': 'FBu',   'BOV': 'BOV',   'CDF': 'FC',
        'CHE': 'CHE',   'CHW': 'CHW',   'CLF': 'CLF',   'COP': 'CO$',
        'COU': 'COU',   'CUC': 'CUC$',  'CVE': 'CVE',   'FKP': '£',
        'GIP': '£',     'GMD': 'D',     'GNF': 'FG',    'KPW': '₩',
        'MNT': '₮',     'MRU': 'UM',    'MXV': 'MXV',   'SHP': '£',
        'SLL': 'Le',    'SSP': '£',     'STN': 'Db',    'SVC': '₡',
        'USN': 'US$',   'UYI': 'UYI',   'UYW': 'UYW',   'VED': 'Bs',
        'ZWL': 'Z$',
        
        # Special Drawing Rights & Commodities  
        'XDR': 'XDR',   'XAG': 'XAG',   'XAU': 'XAU',   'XPD': 'XPD',
        'XPT': 'XPT',   'XSU': 'XSU',   'XUA': 'XUA',
        
        # Bond & Testing Units
        'XBA': 'XBA',   'XBB': 'XBB',   'XBC': 'XBC',   'XBD': 'XBD',
        'XTS': 'XTS',   'XXX': 'XXX',
    }
    upper = code.strip().upper()
    if upper in _SYMBOL_MAP:
        return _SYMBOL_MAP[upper]
    # Fall back to scanning DEFAULT_TRANSLATIONS locale table
    for lang, translations in DEFAULT_TRANSLATIONS.items():
        if translations.get("currency_code") == upper:
            return translations.get("currency_symbol", "$")
    return "$"  # final fallback


def format_currency(amount: float) -> str:
    """Format amount with current currency."""
    symbol = get_currency_symbol()
    return f"{symbol}{amount:.2f}"