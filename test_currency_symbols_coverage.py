#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test currency symbols coverage and identify currencies lacking appropriate symbols.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import pycountry
    from utils.i18n import get_default_currency_symbol_for_code
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the virtual environment and all dependencies are installed.")
    sys.exit(1)


def test_currency_symbols_coverage():
    """Test which currencies have proper symbols vs default fallback."""
    print("🔍 CURRENCY SYMBOLS COVERAGE ANALYSIS")
    print("=" * 60)
    
    # Get all available pycountry currencies
    all_currencies = sorted([currency.alpha_3 for currency in pycountry.currencies])
    
    print(f"📊 Total pycountry currencies: {len(all_currencies)}")
    print("")
    
    # Categories
    has_specific_symbol = []
    uses_default_fallback = []
    
    # Test each currency
    for code in all_currencies:
        symbol = get_default_currency_symbol_for_code(code)
        if symbol == '$':  # Default fallback
            uses_default_fallback.append(code)
        else:
            has_specific_symbol.append(code)
    
    print("✅ CURRENCIES WITH SPECIFIC SYMBOLS:")
    print(f"   Count: {len(has_specific_symbol)}")
    symbol_list = []
    for code in has_specific_symbol:
        symbol = get_default_currency_symbol_for_code(code)
        symbol_list.append(f"{code}({symbol})")
    
    # Print in rows of 6
    for i in range(0, len(symbol_list), 6):
        row = symbol_list[i:i+6]
        print(f"   {' '.join(f'{item:<10}' for item in row)}")
    
    print("")
    print("❌ CURRENCIES USING DEFAULT '$' FALLBACK:")
    print(f"   Count: {len(uses_default_fallback)}")
    
    # Print missing currencies in rows of 10
    for i in range(0, len(uses_default_fallback), 10):
        row = uses_default_fallback[i:i+10]
        print(f"   {' '.join(f'{code:<5}' for code in row)}")
    
    print("")
    print("📈 COVERAGE STATISTICS:")
    print(f"   Total currencies: {len(all_currencies)}")
    print(f"   With specific symbols: {len(has_specific_symbol)}")
    print(f"   Using fallback: {len(uses_default_fallback)}")
    print(f"   Coverage: {len(has_specific_symbol)/len(all_currencies)*100:.1f}%")
    
    return uses_default_fallback


def show_common_missing_currencies():
    """Show some common/important currencies that are missing symbols."""
    print("\n🚨 NOTABLE CURRENCIES WITH MISSING SYMBOLS:")
    print("=" * 50)
    
    important_currencies = [
        'THB',   # Thai Baht
        'TWD',   # Taiwan Dollar  
        'KRW',   # South Korean Won
        'PHP',   # Philippine Peso
        'MYR',   # Malaysian Ringgit
        'IDR',   # Indonesian Rupiah
        'VND',   # Vietnamese Dong
        'TRY',   # Turkish Lira
        'PLN',   # Polish Zloty
        'CZK',   # Czech Koruna
        'HUF',   # Hungarian Forint
        'RUB',   # Russian Ruble
        'UAH',   # Ukrainian Hryvnia
        'ILS',   # Israeli Shekel
        'EGP',   # Egyptian Pound
        'PKR',   # Pakistani Rupee
        'BDT',   # Bangladeshi Taka
        'LKR',   # Sri Lankan Rupee
        'NPR',   # Nepalese Rupee
        'MMK',   # Myanmar Kyat
    ]
    
    for code in important_currencies:
        try:
            currency = pycountry.currencies.get(alpha_3=code)
            symbol = get_default_currency_symbol_for_code(code)
            
            if currency:
                status = "❌ Missing Symbol" if symbol == '$' else f"✅ Has Symbol: {symbol}"
                print(f"   {code} - {currency.name:<30} {status}")
        except:
            print(f"   {code} - Currency not found in pycountry")


if __name__ == "__main__":
    try:
        missing_currencies = test_currency_symbols_coverage()
        show_common_missing_currencies()
        
        print(f"\n💡 RECOMMENDATION:")
        print(f"   Expand the _SYMBOL_MAP in utils/i18n.py to include more currencies")
        print(f"   Priority: Add symbols for the {len(missing_currencies)} currencies currently using '$' fallback")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()