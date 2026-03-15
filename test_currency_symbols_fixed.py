#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the expanded currency symbols coverage.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.i18n import get_default_currency_symbol_for_code


def test_specific_currencies():
    """Test specific important currencies that were previously missing."""
    print("🔍 TESTING EXPANDED CURRENCY SYMBOL COVERAGE")
    print("=" * 60)
    
    # Test currencies that were previously missing
    test_currencies = [
        # Major Asian currencies
        ('KRW', 'South Korean Won'),
        ('THB', 'Thai Baht'), 
        ('TWD', 'Taiwan Dollar'),
        ('PHP', 'Philippine Peso'),
        ('MYR', 'Malaysian Ringgit'),
        ('IDR', 'Indonesian Rupiah'),
        ('VND', 'Vietnamese Dong'),
        
        # Major European currencies
        ('TRY', 'Turkish Lira'),
        ('PLN', 'Polish Zloty'),
        ('CZK', 'Czech Koruna'), 
        ('HUF', 'Hungarian Forint'),
        ('RUB', 'Russian Ruble'),
        ('UAH', 'Ukrainian Hryvnia'),
        
        # Middle Eastern currencies
        ('ILS', 'Israeli Shekel'),
        ('AED', 'UAE Dirham'),
        ('SAR', 'Saudi Riyal'),
        
        # Other important currencies
        ('EGP', 'Egyptian Pound'),
        ('PKR', 'Pakistani Rupee'),
        ('BDT', 'Bangladeshi Taka'),
        ('LKR', 'Sri Lankan Rupee'),
    ]
    
    print("Testing previously missing currencies:")
    fixed_count = 0
    
    for code, name in test_currencies:
        symbol = get_default_currency_symbol_for_code(code)
        
        if symbol == '$':
            print(f"  ❌ {code} ({name}): Still using fallback '$'")
        else:
            print(f"  ✅ {code} ({name}): {repr(symbol)}")
            fixed_count += 1
    
    print(f"\nResults:")
    print(f"  Fixed currencies: {fixed_count}/{len(test_currencies)}")
    print(f"  Coverage: {fixed_count/len(test_currencies)*100:.1f}%")
    
    return fixed_count == len(test_currencies)


def test_original_currencies():
    """Test that original currencies still work."""
    print("\n🔄 TESTING ORIGINAL CURRENCY SUPPORT")
    print("=" * 50)
    
    original_currencies = [
        ('USD', '$'),
        ('EUR', '€'),  
        ('GBP', '£'),
        ('JPY', '¥'),
        ('CAD', 'C$'),
        ('AUD', 'A$'),
        ('CHF', 'CHF'),
        ('SEK', 'kr'),
        ('NOK', 'kr'),
        ('DKK', 'kr'),
        ('INR', '₹'),
        ('BRL', 'R$'),
        ('MXN', 'MX$'),
        ('SGD', 'S$'),
        ('HKD', 'HK$'),
        ('KES', 'KSh'),
        ('ZAR', 'R'),
        ('NGN', '₦'),
        ('GHS', 'GH₵'),
        ('AED', 'AED'),
    ]
    
    print("Testing original currencies (should not break):")
    all_working = True
    
    for code, expected_type in original_currencies:
        symbol = get_default_currency_symbol_for_code(code)
        
        # Check if we got some symbol (not fallback '$' unless it's USD)
        if code == 'USD' and symbol == '$':
            print(f"  ✅ {code}: {repr(symbol)} (correct)")
        elif symbol == '$' and code != 'USD':
            print(f"  ❌ {code}: Using fallback '$' (should have specific symbol)")
            all_working = False
        else:
            print(f"  ✅ {code}: {repr(symbol)}")
    
    print(f"\nOriginal currencies all working: {'✅ Yes' if all_working else '❌ No'}")
    return all_working


if __name__ == "__main__":
    try:
        print("Running expanded currency symbol tests...\n")
        
        # Test the fixes
        expansions_working = test_specific_currencies()
        originals_working = test_original_currencies()
        
        print(f"\n{'='*60}")
        print("FINAL RESULTS:")
        print(f"  Expanded coverage working: {'✅ Yes' if expansions_working else '❌ No'}")
        print(f"  Original support maintained: {'✅ Yes' if originals_working else '❌ No'}")
        
        if expansions_working and originals_working:
            print(f"\n🎉 SUCCESS: Currency symbols significantly improved!")
            print(f"   The currency dropdown should now show proper symbols")
            print(f"   for most world currencies instead of generic '$'")
        else:
            print(f"\n⚠️  Some issues remain - check the output above")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()