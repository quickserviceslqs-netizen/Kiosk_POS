#!/usr/bin/env python3
"""
Test script to verify package size autofill functionality in the item dialog.
This script tests the _on_unit_change method logic directly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from modules.portions import get_unit_info_from_name

class MockDialog:
    """Mock dialog class to test the autofill logic."""

    def __init__(self):
        self.package_size_value = ""
        self.unit_value = ""

    def package_size(self):
        return self

    def get(self):
        return self.package_size_value

    def set(self, value):
        self.package_size_value = value

    def unit_of_measure(self):
        return self

    def _on_unit_change(self):
        """Simulate the _on_unit_change method from SimplifiedItemDialog."""
        unit = self.unit_value
        if unit:
            unit_info = get_unit_info_from_name(unit)
            if unit_info and 'multiplier' in unit_info:
                multiplier = unit_info['multiplier']
                current_value = self.package_size_value
                # Only autofill if field is empty or "1"
                if not current_value or current_value == "1":
                    self.package_size_value = str(multiplier)

def test_package_size_autofill():
    """Test the package size autofill functionality."""

    print("Testing package size autofill functionality...")

    # Test cases: unit -> expected package_size
    test_cases = [
        ("kg", "1000"),
        ("liters", "1000"),
        ("lb", "16"),
        ("g", "1"),
        ("oz", "1"),
        ("meter", "100"),
        ("cm", "1"),
        ("gallon", "128"),
        ("ml", "1"),
        ("quart", "32"),
        ("pint", "16"),
        ("yard", "36"),
        ("foot", "12"),
        ("inch", "1"),
    ]

    passed = 0
    failed = 0

    for unit, expected_multiplier in test_cases:
        dialog = MockDialog()
        dialog.unit_value = unit
        dialog.package_size_value = ""  # Empty field

        # Simulate unit change
        dialog._on_unit_change()

        # Check if package_size was set correctly
        actual_value = dialog.package_size_value

        if actual_value == expected_multiplier:
            print(f"✓ PASS: Unit '{unit}' → package_size: {actual_value}")
            passed += 1
        else:
            print(f"✗ FAIL: Unit '{unit}' → expected: {expected_multiplier}, got: {actual_value}")
            failed += 1

    # Test that autofill doesn't overwrite existing values
    print("\nTesting preservation of existing values...")
    dialog = MockDialog()
    dialog.unit_value = "kg"
    dialog.package_size_value = "500"  # Set a custom value

    dialog._on_unit_change()

    if dialog.package_size_value == "500":
        print("✓ PASS: Custom package_size value preserved")
        passed += 1
    else:
        print(f"✗ FAIL: Custom value overwritten: {dialog.package_size_value}")
        failed += 1

    # Test that autofill works when value is "1"
    dialog = MockDialog()
    dialog.unit_value = "liters"
    dialog.package_size_value = "1"

    dialog._on_unit_change()

    if dialog.package_size_value == "1000":
        print("✓ PASS: Autofill works when value is '1'")
        passed += 1
    else:
        print(f"✗ FAIL: Autofill didn't work for '1': {dialog.package_size_value}")
        failed += 1

    print(f"\nTest Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✓ All package size autofill tests passed!")
        return True
    else:
        print("✗ Some tests failed!")
        return False

if __name__ == "__main__":
    test_package_size_autofill()