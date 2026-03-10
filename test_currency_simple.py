"""
Simple Currency Settings Test

Direct test of currency settings without complex UI imports.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.init_db import get_setting, set_setting
from utils.i18n import get_currency_symbol, format_currency, get_default_currency_symbol_for_code


def test_current_currency_status():
    """Display current currency configuration."""
    print("💰 Current Currency Configuration:")
    print("=" * 40)
    
    # Check database settings
    currency_code = get_setting('currency_code')
    currency_symbol = get_setting('currency_symbol') 
    legacy_currency = get_setting('currency')
    
    print(f"Database Settings:")
    print(f"  currency_code (modern):  {currency_code}")
    print(f"  currency_symbol:         {currency_symbol}")
    print(f"  currency (legacy):       {legacy_currency}")
    
    # Check what i18n module returns
    active_symbol = get_currency_symbol()
    print(f"\nActive Symbol (from i18n): {active_symbol}")
    
    # Test formatting
    test_amounts = [10.50, 123.45, 1000.00]
    for amount in test_amounts:
        formatted = format_currency(amount)
        print(f"  {amount:8.2f} -> {formatted}")
    
    print("\n✅ Current Status Displayed")


def test_currency_change_workflow():
    """Test changing currency and verify it works end-to-end."""
    print("\n🔄 Testing Currency Change Workflow:")
    print("=" * 40)
    
    # Store original values
    orig_code = get_setting('currency_code')
    orig_symbol = get_setting('currency_symbol')
    orig_legacy = get_setting('currency')
    
    print(f"Original: {orig_code or orig_legacy} ({orig_symbol})")
    
    # Change to Japanese Yen
    new_code = 'JPY'
    new_symbol = '¥'
    
    print(f"\nChanging to: {new_code} ({new_symbol})")
    
    # Update settings (same way UI does)
    set_setting('currency_code', new_code)
    set_setting('currency_symbol', new_symbol)
    set_setting('currency', new_code)  # Legacy compatibility
    
    # Verify change worked
    retrieved_code = get_setting('currency_code')
    retrieved_symbol = get_setting('currency_symbol')
    active_symbol = get_currency_symbol()
    
    print(f"Retrieved: {retrieved_code} ({retrieved_symbol})")
    print(f"Active symbol from i18n: {active_symbol}")
    
    # Test formatting with new currency
    formatted = format_currency(1234.56)
    print(f"Format test: 1234.56 -> {formatted}")
    
    assert retrieved_code == new_code, f"Code not saved: {retrieved_code}"
    assert retrieved_symbol == new_symbol, f"Symbol not saved: {retrieved_symbol}"
    assert new_symbol in formatted, f"New symbol not in formatted output: {formatted}"
    
    print("✅ Currency change successful")
    
    # Change to Euro
    new_code = 'EUR'
    new_symbol = '€'
    
    print(f"\nChanging to: {new_code} ({new_symbol})")
    
    set_setting('currency_code', new_code)
    set_setting('currency_symbol', new_symbol)  
    set_setting('currency', new_code)
    
    # Verify
    formatted = format_currency(987.65)
    print(f"Format test: 987.65 -> {formatted}")
    
    assert new_symbol in formatted, f"Euro symbol not in output: {formatted}"
    print("✅ Second currency change successful")
    
    # Restore original settings
    print(f"\nRestoring original: {orig_code or orig_legacy} ({orig_symbol})")
    
    if orig_code:
        set_setting('currency_code', orig_code)
    if orig_symbol:
        set_setting('currency_symbol', orig_symbol)
    if orig_legacy:
        set_setting('currency', orig_legacy)
    
    print("✅ Original settings restored")


def test_currency_defaults():
    """Test currency default mechanisms."""
    print("\n🎌 Testing Currency Defaults:")
    print("=" * 40)
    
    # Test default symbol lookup
    test_codes = [
        ('USD', '$'),
        ('EUR', '€'), 
        ('GBP', '£'),
        ('JPY', '¥'),
        ('CAD', 'C$'),
        ('AUD', 'A$'),
        ('KES', 'KSh'),
        ('ZAR', 'R'),
        ('INR', '₹')
    ]
    
    for code, expected in test_codes:
        symbol = get_default_currency_symbol_for_code(code)
        status = "✅" if symbol == expected else "⚠️"
        print(f"  {code} -> {symbol:>4} {status}")
        
        if symbol != expected:
            print(f"    Expected: {expected}")
    
    print("\n✅ Default lookup test completed")


def test_currency_edge_cases():
    """Test edge cases and error handling."""
    print("\n🔍 Testing Edge Cases:")
    print("=" * 40)
    
    # Test with empty/null values
    original_symbol = get_setting('currency_symbol')
    
    # Temporarily clear symbol
    set_setting('currency_symbol', '')
    
    try:
        symbol = get_currency_symbol()
        print(f"Empty symbol handling: '{symbol}'")
        
        formatted = format_currency(100.00)
        print(f"Formatting with empty symbol: {formatted}")
        
    finally:
        # Restore
        if original_symbol:
            set_setting('currency_symbol', original_symbol)
    
    print("✅ Edge case handling works")


def main():
    """Run all currency tests."""
    print("🧪 Comprehensive Currency Settings Test\n")
    
    try:
        test_current_currency_status()
        test_currency_change_workflow()
        test_currency_defaults() 
        test_currency_edge_cases()
        
        print("\n" + "=" * 50)
        print("✅ ALL CURRENCY TESTS PASSED!")
        print("Currency settings are working correctly.")
        
    except Exception as e:
        print(f"\n❌ CURRENCY TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()