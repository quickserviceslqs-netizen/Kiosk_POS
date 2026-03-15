#!/usr/bin/env python3
"""
Test script to verify package size autofill functionality in the item dialog.
This script simulates the unit change event to test if package_size autofills correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ui.simplified_item_dialog import SimplifiedItemDialog
from modules.portions import get_unit_info_from_name
import tkinter as tk

def test_package_size_autofill():
    """Test the package size autofill functionality by simulating unit changes."""

    print("Testing package size autofill functionality...")

    # Create a root window (will be hidden)
    root = tk.Tk()
    root.withdraw()

    # Create the dialog
    dialog = SimplifiedItemDialog(root)
    dialog.show()  # Initialize the UI elements

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
        # Set item type to measurable to enable unit selection
        dialog.item_type.set("measurable")

        # Clear package_size field
        dialog.package_size.set("")

        # Simulate unit change
        dialog.unit_of_measure.set(unit)
        dialog._on_unit_change()

        # Check if package_size was set correctly
        actual_value = dialog.package_size.get()

        if actual_value == expected_multiplier:
            print(f"✓ PASS: Unit '{unit}' → package_size: {actual_value}")
            passed += 1
        else:
            print(f"✗ FAIL: Unit '{unit}' → expected: {expected_multiplier}, got: {actual_value}")
            failed += 1

    # Test that autofill doesn't overwrite existing values
    print("\nTesting preservation of existing values...")
    dialog.item_type.set("measurable")
    dialog.package_size.set("500")  # Set a custom value
    dialog.unit_of_measure.set("kg")
    dialog._on_unit_change()

    if dialog.package_size.get() == "500":
        print("✓ PASS: Custom package_size value preserved")
        passed += 1
    else:
        print(f"✗ FAIL: Custom value overwritten: {dialog.package_size.get()}")
        failed += 1

    # Test that autofill works when value is "1"
    dialog.package_size.set("1")
    dialog.unit_of_measure.set("liters")
    dialog._on_unit_change()

    if dialog.package_size.get() == "1000":
        print("✓ PASS: Autofill works when value is '1'")
        passed += 1
    else:
        print(f"✗ FAIL: Autofill didn't work for '1': {dialog.package_size.get()}")
        failed += 1

    # Clean up
    root.destroy()

    print(f"\nTest Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✓ All package size autofill tests passed!")
        return True
    else:
        print("✗ Some tests failed!")
        return False

if __name__ == "__main__":
    test_package_size_autofill()