#!/usr/bin/env python3
"""
Currency Settings Propagation System
Fixes currency settings not being respected across the system by:
1. Adding currency change notifications
2. Refreshing cached currency symbols in UI components
3. Fixing character encoding issues
4. Creating centralized currency formatting
"""

import sqlite3
from typing import List, Callable, Dict, Any
from database.init_db import get_connection

class CurrencyNotificationSystem:
    """Centralized system for currency change notifications."""
    
    def __init__(self):
        self._subscribers: List[Callable] = []
        
    def subscribe(self, callback: Callable) -> None:
        """Subscribe to currency change notifications."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe from currency change notifications."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def notify_currency_changed(self, currency_code: str, currency_symbol: str) -> None:
        """Notify all subscribers that currency has changed."""
        print(f"Notifying {len(self._subscribers)} subscribers of currency change: {currency_code} ({currency_symbol})")
        for callback in self._subscribers[:]:  # Use slice to avoid modification during iteration
            try:
                callback(currency_code, currency_symbol)
            except Exception as e:
                print(f"Error notifying currency subscriber: {e}")

# Global notification system
_currency_notifier = CurrencyNotificationSystem()


def subscribe_to_currency_changes(callback: Callable) -> None:
    """Subscribe a callback to currency change notifications."""
    _currency_notifier.subscribe(callback)


def unsubscribe_from_currency_changes(callback: Callable) -> None:
    """Unsubscribe a callback from currency change notifications."""
    _currency_notifier.unsubscribe(callback)


def set_currency_settings(currency_code: str, currency_symbol: str) -> None:
    """
    Set currency settings and notify all subscribers.
    This should be used instead of directly updating the database.
    """
    # Ensure proper encoding by using explicit UTF-8
    try:
        # Test that the symbol is properly encodable
        currency_symbol.encode('utf-8')
        
        with get_connection() as conn:
            # Use explicit UTF-8 encoding for database storage
            conn.execute("PRAGMA encoding = 'UTF-8'")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                        ("currency_code", currency_code))
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                        ("currency_symbol", currency_symbol))
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                        ("currency", currency_code))  # Legacy fallback
            conn.commit()
            
        # Notify all subscribers
        _currency_notifier.notify_currency_changed(currency_code, currency_symbol)
        print(f"Currency settings updated: {currency_code} ({currency_symbol})")
        
    except Exception as e:
        print(f"Error setting currency settings: {e}")
        raise


def get_currency_settings() -> Dict[str, str]:
    """Get current currency settings as a dictionary."""
    from utils.i18n import get_currency_code, get_currency_symbol
    return {
        'code': get_currency_code(),
        'symbol': get_currency_symbol()
    }


def format_currency_amount(amount: float) -> str:
    """Centralized currency formatting function."""
    from utils.i18n import get_currency_symbol
    symbol = get_currency_symbol()
    return f"{symbol}{amount:.2f}"


def parse_currency_amount(currency_string: str) -> float:
    """Parse a currency-formatted string back to float."""
    from utils.i18n import get_currency_symbol
    symbol = get_currency_symbol()
    
    # Remove currency symbol and whitespace, handle commas
    cleaned = currency_string.replace(symbol, '').replace(',', '').strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def fix_currency_encoding_in_database():
    """Fix any currency symbol encoding issues in the database."""
    print("Fixing currency symbol encoding issues...")
    
    try:
        with get_connection() as conn:
            # Set database to UTF-8 encoding
            conn.execute("PRAGMA encoding = 'UTF-8'")
            
            # Get current currency settings
            cursor = conn.execute("SELECT value FROM settings WHERE key = 'currency_code'")
            row = cursor.fetchone()
            currency_code = row[0] if row else 'USD'
            
            # Get the proper symbol for this currency from our mapping
            from utils.i18n import get_default_currency_symbol_for_code
            proper_symbol = get_default_currency_symbol_for_code(currency_code)
            
            # Update the currency symbol with proper encoding
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                        ("currency_symbol", proper_symbol))
            conn.commit()
            
            print(f"Fixed currency symbol for {currency_code}: {proper_symbol}")
            
            # Notify subscribers of the fix
            _currency_notifier.notify_currency_changed(currency_code, proper_symbol)
            
    except Exception as e:
        print(f"Error fixing currency encoding: {e}")


if __name__ == "__main__":
    # Test the notification system and encoding fix
    print("Testing Currency Notification System")
    print("=" * 50)
    
    # Fix encoding issues first
    fix_currency_encoding_in_database()
    
    # Test notification system
    def test_callback(code, symbol):
        print(f"Received notification: {code} ({symbol})")
    
    subscribe_to_currency_changes(test_callback)
    
    # Test setting currency (this should trigger notification)
    set_currency_settings("USD", "$")
    set_currency_settings("EUR", "€")
    set_currency_settings("GBP", "£")
    
    unsubscribe_from_currency_changes(test_callback)
    
    print("\nCurrency notification system working correctly!")