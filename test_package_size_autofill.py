"""Test package size autofill functionality."""

import sys
sys.path.insert(0, '.')

from modules.portions import get_unit_info_from_name

# Test the get_unit_info_from_name function
print("Testing get_unit_info_from_name() function...\n")

# Test various units and their expected multipliers
test_cases = [
    ("liters", 1000, "Volume: liters should have multiplier 1000"),
    ("liter", 1000, "Volume: liter should have multiplier 1000"),
    ("l", 1000, "Volume: l should have multiplier 1000"),
    ("kg", 1000, "Weight: kg should have multiplier 1000"),
    ("kilograms", 1000, "Weight: kilograms should have multiplier 1000"),
    ("g", 1, "Weight: grams should have multiplier 1"),
    ("gram", 1, "Weight: gram should have multiplier 1"),
    ("meters", 100, "Length: meters should have multiplier 100"),
    ("meter", 100, "Length: meter should have multiplier 100"),
    ("m", 100, "Length: m should have multiplier 100"),
    ("cm", 1, "Length: cm should have multiplier 1"),
    ("lb", 16, "Weight: lb should have multiplier 16"),
    ("lbs", 16, "Weight: lbs should have multiplier 16"),
    ("pound", 16, "Weight: pound should have multiplier 16"),
    ("oz", 1, "Weight: oz should have multiplier 1"),
    ("ounce", 1, "Weight: ounce should have multiplier 1"),
    ("gallon", 128, "Volume: gallon should have multiplier 128"),
    ("gal", 128, "Volume: gal should have multiplier 128"),
    ("ml", 1, "Volume: ml should have multiplier 1"),
    ("milliliter", 1, "Volume: milliliter should have multiplier 1"),
    ("quart", 32, "Volume: quart should have multiplier 32"),
    ("pint", 16, "Volume: pint should have multiplier 16"),
    ("yard", 36, "Length: yard should have multiplier 36"),
    ("foot", 12, "Length: foot should have multiplier 12"),
    ("inch", 1, "Length: inch should have multiplier 1"),
]

all_passed = True
for unit_name, expected_multiplier, description in test_cases:
    try:
        unit_info = get_unit_info_from_name(unit_name)
        actual_multiplier = unit_info.get("multiplier", 1)
        
        if actual_multiplier == expected_multiplier:
            print(f"✓ PASS: {description}")
            print(f"  Unit: '{unit_name}' → multiplier: {actual_multiplier}")
        else:
            print(f"✗ FAIL: {description}")
            print(f"  Unit: '{unit_name}' → expected: {expected_multiplier}, got: {actual_multiplier}")
            all_passed = False
    except Exception as e:
        print(f"✗ ERROR: {description}")
        print(f"  Unit: '{unit_name}' → {str(e)}")
        all_passed = False
    print()

if all_passed:
    print("\n✓ All tests passed!")
    sys.exit(0)
else:
    print("\n✗ Some tests failed!")
    sys.exit(1)

