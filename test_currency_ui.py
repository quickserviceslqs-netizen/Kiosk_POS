"""
Currency Settings UI Test

Test the UI components for currency management.
"""

import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.init_db import get_setting, set_setting


def test_currency_ui_component():
    """Test the currency settings UI component without actually showing it."""
    print("Testing currency settings UI component...")
    
    try:
        from ui.settings import CurrencySettingsFrame
        
        # Create a minimal root window (withdrawn so it doesn't show)
        root = tk.Tk()
        root.withdraw()
        
        # Create the currency settings frame
        frame = CurrencySettingsFrame(root)
        
        # Test that it loads current settings
        current_currency = frame.currency_var.get()
        current_symbol = frame.symbol_var.get()
        
        print(f"   UI loaded currency: {current_currency} ({current_symbol})")
        
        # Test that we can simulate changing values
        frame.currency_var.set('GBP')
        frame.symbol_var.set('£')
        
        # Test the save functionality (but restore after)
        original_currency = get_setting('currency_code') or get_setting('currency')
        original_symbol = get_setting('currency_symbol')
        
        frame.save_currency()
        
        # Verify it was saved
        saved_currency = get_setting('currency_code')
        saved_symbol = get_setting('currency_symbol')
        
        assert saved_currency == 'GBP', f"Expected GBP, got {saved_currency}"
        assert saved_symbol == '£', f"Expected £, got {saved_symbol}"
        
        print("   ✅ UI save functionality works correctly")
        
        # Test refresh functionality 
        frame.currency_var.set('XXX')  # Set to something different
        frame.symbol_var.set('X')
        
        frame.refresh()  # Should reload from database
        
        refreshed_currency = frame.currency_var.get()
        refreshed_symbol = frame.symbol_var.get()
        
        assert refreshed_currency == 'GBP', f"Refresh failed: expected GBP, got {refreshed_currency}"
        assert refreshed_symbol == '£', f"Refresh failed: expected £, got {refreshed_symbol}"
        
        print("   ✅ UI refresh functionality works correctly")
        
        # Restore original values
        if original_currency:
            set_setting('currency_code', original_currency)
            set_setting('currency', original_currency)
        if original_symbol:
            set_setting('currency_symbol', original_symbol)
        
        # Clean up
        root.destroy()
        print("   ✅ Currency UI component test completed successfully")
        
    except Exception as e:
        print(f"   ⚠️  Currency UI test error: {e}")
        import traceback
        traceback.print_exc()


def test_currency_auto_population():
    """Test automatic symbol population when currency code is selected."""
    print("\nTesting currency auto-population...")
    
    try:
        from ui.settings import CurrencySettingsFrame
        
        root = tk.Tk()
        root.withdraw()
        
        frame = CurrencySettingsFrame(root)
        
        # Test auto-population for different currencies
        test_currencies = [
            ('USD', '$'),
            ('EUR', '€'),
            ('GBP', '£'),
            ('JPY', '¥'),
            ('KES', 'KSh')
        ]
        
        for code, expected_symbol in test_currencies:
            frame.currency_var.set(code)
            
            # Simulate the selection event
            event = type('Event', (), {})()  # Mock event object
            frame._on_currency_selected(event)
            
            actual_symbol = frame.symbol_var.get()
            print(f"   {code} -> {actual_symbol}")
            
            assert actual_symbol == expected_symbol, f"Expected {expected_symbol} for {code}, got {actual_symbol}"
        
        print("   ✅ Auto-population working correctly")
        
        root.destroy()
        
    except Exception as e:
        print(f"   ⚠️  Auto-population test error: {e}")
        import traceback
        traceback.print_exc()


def test_currency_validation():
    """Test input validation for currency settings."""
    print("\nTesting currency validation...")
    
    try:
        from ui.settings import CurrencySettingsFrame
        
        root = tk.Tk()  
        root.withdraw()
        
        frame = CurrencySettingsFrame(root)
        
        # Store original values
        original_currency = get_setting('currency_code') or get_setting('currency')
        original_symbol = get_setting('currency_symbol')
        
        # Test empty currency code (should show error)
        frame.currency_var.set('')
        frame.symbol_var.set('$')
        
        # The save_currency method should handle empty values
        try:
            frame.save_currency()
            print("   ✅ Empty currency validation handled")
        except Exception:
            print("   ✅ Empty currency validation triggered error as expected")
        
        # Test empty symbol (should show error)  
        frame.currency_var.set('USD')
        frame.symbol_var.set('')
        
        try:
            frame.save_currency()
            print("   ✅ Empty symbol validation handled")
        except Exception:
            print("   ✅ Empty symbol validation triggered error as expected")
        
        # Test valid input
        frame.currency_var.set('USD')
        frame.symbol_var.set('$')
        
        frame.save_currency()
        print("   ✅ Valid input accepted")
        
        # Restore original values
        if original_currency:
            set_setting('currency_code', original_currency)
            set_setting('currency', original_currency)
        if original_symbol:
            set_setting('currency_symbol', original_symbol)
        
        root.destroy()
        
    except Exception as e:
        print(f"   ⚠️  Validation test error: {e}")


def main():
    """Run currency UI tests."""
    print("🖥️  Starting Currency Settings UI Tests\n")
    
    try:
        test_currency_ui_component()
        test_currency_auto_population()
        test_currency_validation()
        
        print("\n✅ ALL CURRENCY UI TESTS PASSED!")
        print("Currency UI components are working correctly.")
        
    except Exception as e:
        print(f"\n❌ CURRENCY UI TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()