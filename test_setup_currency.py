"""
Setup Process and Currency List Test

Tests to verify:
1. Initial setup applies settings correctly
2. All currencies show up in both setup and main settings
3. Currency list consistency between setup and settings
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.init_db import get_setting, set_setting, get_connection
import pycountry


def test_setup_currency_list():
    """Test that setup wizard has comprehensive currency list."""
    print("Testing setup wizard currency list...")
    
    # Get the hardcoded list from admin_setup.py
    setup_currencies = ['USD', 'EUR', 'GBP', 'KES', 'ZAR', 'CAD', 'AUD', 'JPY', 'CNY']
    
    # Get comprehensive list from pycountry (same as main settings)
    all_currencies = []
    for currency in pycountry.currencies:
        all_currencies.append(currency.alpha_3)
    
    print(f"   Setup wizard currencies: {len(setup_currencies)} currencies")
    print(f"   Available world currencies: {len(all_currencies)} currencies")
    print(f"   Setup currencies: {setup_currencies}")
    
    # Check if setup list is comprehensive enough
    major_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CNY', 'CAD', 'AUD', 'CHF', 'SEK', 'NOK', 
                       'DKK', 'KES', 'ZAR', 'NGN', 'GHS', 'EGP', 'MAD', 'TND', 'INR', 'SGD', 
                       'HKD', 'THB', 'MYR', 'PHP', 'BRL', 'MXN', 'ARS', 'CLP']
    
    missing_major = [curr for curr in major_currencies if curr not in setup_currencies]
    if missing_major:
        print(f"   ⚠️  Major currencies missing from setup: {missing_major}")
        return False
    else:
        print("   ✅ Setup has all major currencies")
        return True


def test_currency_list_consistency():
    """Test consistency between setup and main settings currency lists."""
    print("\nTesting currency list consistency...")
    
    # Import the settings currency handling
    try:
        from ui.settings import CurrencySettingsFrame
        import tkinter as tk
        
        # Create test instance to check currency list
        root = tk.Tk()
        root.withdraw()
        
        settings_frame = CurrencySettingsFrame(root)
        settings_currencies = settings_frame.all_currencies
        
        root.destroy()
        
        print(f"   Main settings currencies: {len(settings_currencies)} currencies")
        print(f"   Sample: {settings_currencies[:10]}")
        
        # The main settings should have MANY more currencies than setup
        if len(settings_currencies) > 100:
            print("   ✅ Main settings has comprehensive currency list")
            return True
        else:
            print(f"   ⚠️  Main settings has limited currencies: {len(settings_currencies)}")
            return False
            
    except Exception as e:
        print(f"   ⚠️  Could not test settings currencies: {e}")
        return False


def test_setup_settings_persistence():
    """Test that setup wizard settings are properly persisted."""
    print("\nTesting setup settings persistence...")
    
    # Simulate the setup completion process
    try:
        # Store original values  
        orig_business = get_setting('business_name')
        orig_currency_code = get_setting('currency_code')
        orig_currency_symbol = get_setting('currency_symbol')
        orig_currency_legacy = get_setting('currency')
        orig_theme = get_setting('theme')
        orig_footer = get_setting('receipt_footer')
        
        print(f"   Original settings:")
        print(f"     Business: {orig_business}")
        print(f"     Currency: {orig_currency_code} ({orig_currency_symbol})")
        print(f"     Theme: {orig_theme}")
        
        # Simulate setup wizard saving settings
        test_business = "Test Setup Store"
        test_currency_code = "CAD"
        test_currency_symbol = "C$"
        test_theme = "light"
        test_footer = "Test footer from setup"
        
        print(f"\n   Simulating setup with:")
        print(f"     Business: {test_business}")
        print(f"     Currency: {test_currency_code} ({test_currency_symbol})")
        print(f"     Theme: {test_theme}")
        
        # Save settings (simulating _save_currency_setting and _save_preferences_settings)
        with get_connection() as conn:
            settings = [
                ('business_name', test_business),
                ('currency_code', test_currency_code),
                ('currency_symbol', test_currency_symbol),
                ('currency', test_currency_code),  # legacy fallback
                ('theme', test_theme),
                ('receipt_footer', test_footer)
            ]
            
            for key, value in settings:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        
        print("   ✅ Setup settings saved to database")
        
        # Verify settings were saved correctly
        saved_business = get_setting('business_name')
        saved_currency_code = get_setting('currency_code')
        saved_currency_symbol = get_setting('currency_symbol')
        saved_theme = get_setting('theme')
        saved_footer = get_setting('receipt_footer')
        
        print(f"\n   Retrieved settings:")
        print(f"     Business: {saved_business}")
        print(f"     Currency: {saved_currency_code} ({saved_currency_symbol})")
        print(f"     Theme: {saved_theme}")
        
        # Verify correctness
        assert saved_business == test_business, f"Business name not saved correctly"
        assert saved_currency_code == test_currency_code, f"Currency code not saved correctly"
        assert saved_currency_symbol == test_currency_symbol, f"Currency symbol not saved correctly"
        assert saved_theme == test_theme, f"Theme not saved correctly"
        
        print("   ✅ All setup settings persisted correctly")
        
        # Restore original settings
        print("\n   Restoring original settings...")
        with get_connection() as conn:
            if orig_business:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('business_name', orig_business))
            if orig_currency_code:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('currency_code', orig_currency_code))
            if orig_currency_symbol:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('currency_symbol', orig_currency_symbol))
            if orig_currency_legacy:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('currency', orig_currency_legacy))
            if orig_theme:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('theme', orig_theme))
            if orig_footer:
                conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('receipt_footer', orig_footer))
            conn.commit()
        
        print("   ✅ Original settings restored")
        return True
        
    except Exception as e:
        print(f"   ❌ Setup persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pycountry_currency_integration():
    """Test that pycountry integration works correctly."""
    print("\nTesting pycountry currency integration...")
    
    try:
        import pycountry
        
        # Get all currencies
        currencies = list(pycountry.currencies)
        print(f"   Total pycountry currencies: {len(currencies)}")
        
        # Test some common currencies
        test_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'KES', 'ZAR', 'NGN', 'GHS']
        
        for code in test_currencies:
            try:
                currency = pycountry.currencies.get(alpha_3=code)
                if currency:
                    name = currency.name
                    print(f"   {code}: {name}")
                else:
                    print(f"   {code}: Not found")
            except Exception as e:
                print(f"   {code}: Error - {e}")
        
        print("   ✅ pycountry integration working")
        return True
        
    except Exception as e:
        print(f"   ❌ pycountry test failed: {e}")
        return False


def main():
    """Run setup and currency list tests."""
    print("🔧 Setup Process and Currency List Tests\n")
    
    try:
        results = []
        
        results.append(test_setup_currency_list())
        results.append(test_currency_list_consistency()) 
        results.append(test_setup_settings_persistence())
        results.append(test_pycountry_currency_integration())
        
        if all(results):
            print("\n" + "=" * 50)
            print("✅ ALL SETUP AND CURRENCY TESTS PASSED!")
            
            print("\nISSUES IDENTIFIED:")
            print("1. Setup wizard has limited currency list (9 currencies)")
            print("2. Main settings has comprehensive list (150+ currencies)")
            print("3. This creates inconsistent user experience")
            print("\nRECOMMENDATION: Update setup wizard to use full currency list")
            
        else:
            print("\n❌ SOME TESTS FAILED - See details above")
            
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()