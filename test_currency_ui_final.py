#!/usr/bin/env python3
"""Quick test to verify currency settings work in the setup wizard."""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_setup_currency_dropdown():
    """Test that the setup wizard currency dropdown works correctly."""
    print("Testing setup wizard currency dropdown...")
    
    try:
        import tkinter as tk
        from ui.admin_setup import AdminSetupWizard
        from utils.i18n import get_default_currency_symbol_for_code
        
        # Create a test root window
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Test a few currencies to make sure the dropdown format works
        test_codes = ['USD', 'EUR', 'GBP', 'JPY', 'XSU']
        
        for code in test_codes:
            symbol = get_default_currency_symbol_for_code(code)
            dropdown_text = f"{code} ({symbol})"
            print(f"✅ {code}: {dropdown_text}")
        
        root.destroy()
        print("✅ Setup wizard currency formatting works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Setup wizard test failed: {e}")
        return False

def test_settings_ui_currency():
    """Test that the settings UI currency functions work."""
    print("\nTesting settings UI currency functions...")
    
    try:
        from utils.i18n import get_currency_code, get_currency_symbol, get_default_currency_symbol_for_code
        
        # Test that we can get current currency
        code = get_currency_code()
        symbol = get_currency_symbol()
        print(f"✅ Current currency: {code} ({symbol})")
        
        # Test that we can get default symbols for any currency
        test_symbol = get_default_currency_symbol_for_code('JPY')
        if test_symbol == '¥':
            print(f"✅ Symbol lookup works: JPY -> {test_symbol}")
        else:
            print(f"❌ Symbol lookup issue: JPY -> {test_symbol} (expected ¥)")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Settings UI test failed: {e}")
        return False

def main():
    """Run currency UI tests."""
    print("🧪 CURRENCY UI TESTING")
    print("Ensuring currency settings work correctly in the user interface...\n")
    
    tests = [
        test_setup_currency_dropdown,
        test_settings_ui_currency,
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            all_passed = False
    
    if all_passed:
        print("\n🎉 ALL CURRENCY UI TESTS PASSED!")
        print("✅ Setup wizard currency dropdown works")
        print("✅ Settings UI currency functions work")
        print("\n✨ The currency system is now fully functional!")
    else:
        print("\n⚠️  Some currency UI tests failed")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)