#!/usr/bin/env python3
"""Test currency settings propagation across the entire system."""

import os
import sys

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def test_currency_encoding_fix():
    """Test that currency encoding issues are fixed."""
    print("=" * 60)
    print("TESTING CURRENCY ENCODING FIX")
    print("=" * 60)
    
    from utils.currency_notifications import fix_currency_encoding_in_database
    from utils.i18n import get_currency_symbol, get_currency_code
    
    # Fix encoding issues
    fix_currency_encoding_in_database()
    
    # Test current settings
    code = get_currency_code()
    symbol = get_currency_symbol()
    
    print(f"Currency Code: {code}")
    print(f"Currency Symbol: '{symbol}' (length: {len(symbol)})")
    
    # Verify the symbol is not corrupted
    if symbol == '�':
        print("❌ Currency symbol is corrupted (shows as �)")
        return False
    else:
        print(f"✅ Currency symbol displays correctly: {symbol}")
        return True


def test_currency_notification_system():
    """Test the currency notification system works."""
    print("\n" + "=" * 60)
    print("TESTING CURRENCY NOTIFICATION SYSTEM")  
    print("=" * 60)
    
    from utils.currency_notifications import (
        subscribe_to_currency_changes, 
        unsubscribe_from_currency_changes,
        set_currency_settings,
        get_currency_settings
    )
    
    notifications_received = []
    
    def test_callback(code, symbol):
        notifications_received.append((code, symbol))
        print(f"📢 Received notification: {code} ({symbol})")
    
    # Subscribe to notifications
    subscribe_to_currency_changes(test_callback)
    
    # Test setting different currencies
    test_currencies = [
        ('USD', '$'),
        ('EUR', '€'),
        ('GBP', '£'),
        ('JPY', '¥')
    ]
    
    for code, symbol in test_currencies:
        print(f"\nSetting currency to {code} ({symbol})")
        set_currency_settings(code, symbol)
        
        # Verify the setting was stored
        current_settings = get_currency_settings()
        if current_settings['code'] == code and current_settings['symbol'] == symbol:
            print(f"✅ Currency correctly set and retrieved: {code} ({symbol})")
        else:
            print(f"❌ Currency mismatch! Expected {code}/{symbol}, got {current_settings['code']}/{current_settings['symbol']}")
            return False
    
    # Check notifications were received
    unsubscribe_from_currency_changes(test_callback)
    
    if len(notifications_received) == len(test_currencies):
        print(f"\n✅ All {len(test_currencies)} currency change notifications received")
        return True
    else:
        print(f"\n❌ Expected {len(test_currencies)} notifications, received {len(notifications_received)}")
        return False


def test_centralized_currency_formatting():
    """Test centralized currency formatting functions."""
    print("\n" + "=" * 60)
    print("TESTING CENTRALIZED CURRENCY FORMATTING")
    print("=" * 60)
    
    from utils.currency_notifications import format_currency_amount, parse_currency_amount
    
    # Test formatting
    test_amounts = [10.50, 1234.56, 0.99]
    
    for amount in test_amounts:
        formatted = format_currency_amount(amount)
        parsed = parse_currency_amount(formatted)
        
        print(f"Amount: {amount} -> Formatted: '{formatted}' -> Parsed back: {parsed}")
        
        if abs(parsed - amount) < 0.01:  # Allow for floating point precision
            print(f"✅ Formatting and parsing consistent for {amount}")
        else:
            print(f"❌ Formatting/parsing mismatch for {amount}")
            return False
    
    return True


def test_ui_imports():
    """Test that UI components can import the new currency system."""
    print("\n" + "=" * 60)
    print("TESTING UI COMPONENT IMPORTS")
    print("=" * 60)
    
    try:
        # Test that key UI modules can import the currency notification system
        from ui.settings import CurrencySettingsFrame
        print("✅ ui.settings imports correctly")
        
        from utils.currency_notifications import set_currency_settings
        print("✅ Currency notification system imports correctly")
        
        # Test that we can create instances (basic functionality test)
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Hide window
        
        # This should not crash
        frame = tk.Frame(root)
        currency_frame = CurrencySettingsFrame(frame)
        print("✅ CurrencySettingsFrame can be instantiated")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ UI import test failed: {e}")
        return False


def test_database_consistency():
    """Test that database operations are consistent."""
    print("\n" + "=" * 60)
    print("TESTING DATABASE CONSISTENCY")
    print("=" * 60)
    
    from utils.currency_notifications import set_currency_settings, get_currency_settings
    from database.init_db import get_connection
    
    # Set a specific currency
    test_code = "CAD"
    test_symbol = "C$"
    
    print(f"Setting currency to {test_code} ({test_symbol})")
    set_currency_settings(test_code, test_symbol)
    
    # Verify through different access methods
    settings = get_currency_settings()
    print(f"get_currency_settings(): {settings}")
    
    # Direct database check
    with get_connection() as conn:
        cursor = conn.execute("SELECT key, value FROM settings WHERE key LIKE '%currency%'")
        db_settings = cursor.fetchall()
        
    print("Direct database values:")
    for setting in db_settings:
        key = setting['key'] if isinstance(setting, dict) else setting[0]
        value = setting['value'] if isinstance(setting, dict) else setting[1]
        print(f"  {key}: '{value}'")
    
    # Check consistency
    if (settings['code'] == test_code and 
        settings['symbol'] == test_symbol and
        test_symbol not in ['�', None, '']):
        print("✅ Database consistency verified")
        return True
    else:
        print("❌ Database consistency failed")
        return False


def main():
    """Run all currency propagation tests."""
    print("🧪 CURRENCY SETTINGS PROPAGATION TESTING")
    print("Testing currency settings propagation across the system...\n")
    
    tests = [
        ("Encoding Fix", test_currency_encoding_fix),
        ("Notification System", test_currency_notification_system),
        ("Centralized Formatting", test_centralized_currency_formatting),
        ("UI Component Imports", test_ui_imports),
        ("Database Consistency", test_database_consistency),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running test: {test_name}")
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: CRASHED - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"✅ Tests Passed: {passed}")
    print(f"❌ Tests Failed: {failed}")
    print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL CURRENCY PROPAGATION TESTS PASSED!")
        print("✅ Currency encoding issues fixed")
        print("✅ Currency change notifications working")
        print("✅ Centralized currency formatting operational")
        print("✅ UI components properly integrated")
        print("✅ Database consistency maintained")
        print("\n🚀 Currency settings should now be respected across the entire system!")
    else:
        print(f"\n⚠️  {failed} issues still need to be addressed")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)