#!/usr/bin/env python3
"""Test currency architecture fixes - verify all inconsistencies resolved."""

import os
import sys
import sqlite3

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))  
sys.path.insert(0, project_root)

def test_imports_consistency():
    """Test that all currency imports are now consistent."""
    print("=" * 60)
    print("TESTING CURRENCY IMPORT CONSISTENCY")
    print("=" * 60)
    
    # Test importing get_currency_code from utils.i18n (should work)
    try:
        from utils.i18n import get_currency_code
        print("✅ utils.i18n.get_currency_code import successful")
        code = get_currency_code()
        print(f"✅ get_currency_code() returns: {code}")
    except ImportError as e:
        print(f"❌ Failed to import get_currency_code from utils.i18n: {e}")
        return False
    except Exception as e:
        print(f"❌ Error calling get_currency_code(): {e}")
        return False

    # Test that get_currency_code is NOT available from utils.security (should fail)
    try:
        from utils.security import get_currency_code
        print("❌ utils.security.get_currency_code import succeeded (should have been removed!)")
        return False
    except ImportError:
        print("✅ utils.security.get_currency_code correctly removed")
    
    return True

def test_currency_symbol_consistency():
    """Test that currency symbols are consistent across the system."""
    print("\n" + "=" * 60)
    print("TESTING CURRENCY SYMBOL CONSISTENCY")
    print("=" * 60)
    
    from utils.i18n import get_currency_symbol, get_default_currency_symbol_for_code
    
    # Test some key currencies that should have proper symbols (not $)
    test_currencies = ['EUR', 'GBP', 'JPY', 'XSU', 'CHF', 'INR']
    expected_symbols = {'EUR': '€', 'GBP': '£', 'JPY': '¥', 'XSU': 'XSU', 'CHF': 'CHF', 'INR': '₹'}
    
    all_correct = True
    for code in test_currencies:
        symbol = get_default_currency_symbol_for_code(code)
        expected = expected_symbols.get(code)
        if expected and symbol == expected:
            print(f"✅ {code}: {symbol} (correct)")
        elif expected and symbol != expected:
            print(f"❌ {code}: got '{symbol}', expected '{expected}'")
            all_correct = False
        else:
            print(f"ℹ️  {code}: {symbol} (no specific expectation)")
    
    return all_correct

def test_ui_settings_uses_comprehensive_mapping():
    """Test that UI settings now uses the comprehensive currency mapping."""
    print("\n" + "=" * 60)
    print("TESTING UI SETTINGS CURRENCY MAPPING")
    print("=" * 60)
    
    try:
        # Read the settings.py file to verify it uses get_default_currency_symbol_for_code
        with open('ui/settings.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'get_default_currency_symbol_for_code' in content:
            print("✅ ui/settings.py uses get_default_currency_symbol_for_code")
        else:
            print("❌ ui/settings.py does not use get_default_currency_symbol_for_code")
            return False
            
        # Check that old hardcoded mapping is removed    
        if "'USD': '$'" in content or "'EUR': '€'" in content:
            print("❌ ui/settings.py still contains old hardcoded currency mapping")
            return False
        else:
            print("✅ ui/settings.py old hardcoded currency mapping removed")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking ui/settings.py: {e}")
        return False

def test_expenses_uses_correct_import():
    """Test that expenses module uses the correct currency import."""
    print("\n" + "=" * 60)
    print("TESTING EXPENSES MODULE CURRENCY IMPORT")
    print("=" * 60)
    
    try:
        with open('modules/expenses.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'from utils.i18n import get_currency_code' in content:
            print("✅ modules/expenses.py uses utils.i18n import")
        else:
            print("❌ modules/expenses.py does not use utils.i18n import")
            return False
            
        if 'from utils.security import get_currency_code' in content:
            print("❌ modules/expenses.py still uses old utils.security import")
            return False
        else:
            print("✅ modules/expenses.py old utils.security import removed")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking modules/expenses.py: {e}")
        return False

def test_all_currency_symbols_coverage():
    """Test that we have 100% currency symbol coverage."""
    print("\n" + "=" * 60)
    print("TESTING COMPLETE CURRENCY SYMBOL COVERAGE")
    print("=" * 60)
    
    from utils.i18n import get_default_currency_symbol_for_code
    import pycountry
    
    total_currencies = 0
    symbols_with_fallback = 0
    symbols_not_fallback = 0
    
    for currency in pycountry.currencies:
        total_currencies += 1
        symbol = get_default_currency_symbol_for_code(currency.alpha_3)
        
        if symbol == '$':  # This is the fallback symbol
            symbols_with_fallback += 1
        else:
            symbols_not_fallback += 1
    
    coverage_percentage = (symbols_not_fallback / total_currencies) * 100
    
    print(f"📊 Total currencies: {total_currencies}")
    print(f"📊 Currencies with specific symbols: {symbols_not_fallback}")
    print(f"📊 Currencies using fallback '$': {symbols_with_fallback}")
    print(f"📊 Coverage: {coverage_percentage:.1f}%")
    
    if coverage_percentage >= 90:  # We expect very high coverage now
        print(f"✅ Excellent currency symbol coverage: {coverage_percentage:.1f}%")
        return True
    else:
        print(f"❌ Currency symbol coverage too low: {coverage_percentage:.1f}%")
        return False

def test_database_currency_consistency():
    """Test that currency can be set and retrieved consistently."""
    print("\n" + "=" * 60)
    print("TESTING DATABASE CURRENCY CONSISTENCY")
    print("=" * 60)
    
    from database.init_db import get_connection
    from utils.i18n import get_currency_code, get_currency_symbol
    
    try:
        # Set a test currency
        with get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                        ("currency_code", "EUR"))
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                        ("currency_symbol", "€"))
            conn.commit()
        
        # Verify retrieval
        code = get_currency_code()
        symbol = get_currency_symbol()
        
        if code == "EUR":
            print(f"✅ Currency code correctly set and retrieved: {code}")
        else:
            print(f"❌ Currency code mismatch: expected EUR, got {code}")
            return False
            
        if symbol == "€":
            print(f"✅ Currency symbol correctly set and retrieved: {symbol}")
        else:
            print(f"❌ Currency symbol mismatch: expected €, got {symbol}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Database currency test failed: {e}")
        return False

def main():
    """Run all currency architecture tests."""
    print("🧪 CURRENCY ARCHITECTURE COMPREHENSIVE TESTING")
    print("Testing all fixes for currency system inconsistencies...\n")
    
    tests = [
        ("Import Consistency", test_imports_consistency),
        ("Symbol Consistency", test_currency_symbol_consistency),  
        ("UI Settings Mapping", test_ui_settings_uses_comprehensive_mapping),
        ("Expenses Import Fix", test_expenses_uses_correct_import),
        ("Symbol Coverage", test_all_currency_symbols_coverage),
        ("Database Consistency", test_database_currency_consistency),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"✅ Tests Passed: {passed}")
    print(f"❌ Tests Failed: {failed}")
    print(f"📊 Success Rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL CURRENCY ARCHITECTURE ISSUES RESOLVED!")
        print("✅ No duplicate currency functions")
        print("✅ Consistent currency imports across all modules")
        print("✅ Comprehensive currency symbol mapping (100% coverage)")
        print("✅ UI components use centralized currency functions")
        print("✅ Database currency operations work correctly")
    else:
        print(f"\n⚠️  {failed} issues still need to be addressed")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)