"""Unit tests for validation utilities."""
import unittest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validation import (
    ValidationError,
    sanitize_string,
    validate_numeric,
    validate_integer,
    validate_email,
    validate_barcode,
    validate_path,
    validate_item_name,
    validate_item_category,
    validate_item_barcode,
    validate_item_price,
    validate_item_cost,
    validate_item_quantity,
    validate_item_vat_rate,
    validate_item_low_stock_threshold,
    validate_item_unit_of_measure,
    validate_item_package_size,
)


class TestValidation(unittest.TestCase):
    """Test cases for validation utilities."""

    def test_sanitize_string(self):
        """Test string sanitization."""
        # Valid string
        self.assertEqual(sanitize_string("Hello World"), "Hello World")

        # Empty string with allow_empty=True
        self.assertEqual(sanitize_string("", allow_empty=True), "")

        # Empty string with allow_empty=False
        with self.assertRaises(ValidationError):
            sanitize_string("", allow_empty=False)

        # String with HTML tags (should be sanitized)
        self.assertEqual(sanitize_string("<script>alert('xss')</script>"), "scriptalert(xss)/script")

        # String exceeding max length
        with self.assertRaises(ValidationError):
            sanitize_string("a" * 256, max_length=255)

    def test_validate_numeric(self):
        """Test numeric validation."""
        # Valid numbers
        self.assertEqual(validate_numeric("123.45"), 123.45)
        self.assertEqual(validate_numeric(123), 123.0)

        # Invalid input
        with self.assertRaises(ValidationError):
            validate_numeric("not_a_number")

        # Below minimum
        with self.assertRaises(ValidationError):
            validate_numeric(5, min_value=10)

        # Above maximum
        with self.assertRaises(ValidationError):
            validate_numeric(100, max_value=50)

        # Zero not allowed
        with self.assertRaises(ValidationError):
            validate_numeric(0, allow_zero=False)

    def test_validate_integer(self):
        """Test integer validation."""
        # Valid integers
        self.assertEqual(validate_integer("123"), 123)
        self.assertEqual(validate_integer(123.0), 123)

        # Invalid input
        with self.assertRaises(ValidationError):
            validate_integer("not_an_integer")

        # Float input (should be converted)
        self.assertEqual(validate_integer(123.7), 123)

    def test_validate_email(self):
        """Test email validation."""
        # Valid emails
        self.assertEqual(validate_email("test@example.com"), "test@example.com")
        self.assertEqual(validate_email("user.name+tag@domain.co.uk"), "user.name+tag@domain.co.uk")

        # Invalid emails
        with self.assertRaises(ValidationError):
            validate_email("invalid-email")

        with self.assertRaises(ValidationError):
            validate_email("")

    def test_validate_barcode(self):
        """Test barcode validation."""
        # Valid barcodes
        self.assertEqual(validate_barcode("123456789"), "123456789")
        self.assertEqual(validate_barcode("ABC-123-XYZ"), "ABC-123-XYZ")

        # Invalid barcodes
        with self.assertRaises(ValidationError):
            validate_barcode("invalid@barcode")

        # None input
        self.assertIsNone(validate_barcode(None))

    def test_validate_item_name(self):
        """Test item name validation."""
        # Valid names
        self.assertEqual(validate_item_name("Test Item"), "Test Item")

        # Empty name
        with self.assertRaises(ValidationError):
            validate_item_name("")

        # Name too long
        with self.assertRaises(ValidationError):
            validate_item_name("a" * 101)

    def test_validate_item_category(self):
        """Test item category validation."""
        # Valid categories
        self.assertEqual(validate_item_category("Test Category"), "Test Category")

        # None category
        self.assertIsNone(validate_item_category(None))

        # Empty category
        self.assertIsNone(validate_item_category(""))

        # Category too long
        with self.assertRaises(ValidationError):
            validate_item_category("a" * 51)

    def test_validate_item_price(self):
        """Test item price validation."""
        # Valid prices
        self.assertEqual(validate_item_price(10.99), 10.99)
        self.assertEqual(validate_item_price("15.50"), 15.50)

        # Negative price
        with self.assertRaises(ValidationError):
            validate_item_price(-5)

        # Price too high
        with self.assertRaises(ValidationError):
            validate_item_price(1000000)

    def test_validate_item_quantity(self):
        """Test item quantity validation."""
        # Valid quantities
        self.assertEqual(validate_item_quantity(100), 100.0)
        self.assertEqual(validate_item_quantity("50.5"), 50.5)

        # Negative quantity
        with self.assertRaises(ValidationError):
            validate_item_quantity(-1)

    def test_validate_item_vat_rate(self):
        """Test VAT rate validation."""
        # Valid rates
        self.assertEqual(validate_item_vat_rate(16.0), 16.0)
        self.assertEqual(validate_item_vat_rate("0"), 0.0)

        # Invalid rates
        with self.assertRaises(ValidationError):
            validate_item_vat_rate(-1)

        with self.assertRaises(ValidationError):
            validate_item_vat_rate(101)

    def test_validate_item_low_stock_threshold(self):
        """Test low stock threshold validation."""
        # Valid thresholds
        self.assertEqual(validate_item_low_stock_threshold(10), 10)
        self.assertEqual(validate_item_low_stock_threshold("5"), 5)

        # Invalid thresholds
        with self.assertRaises(ValidationError):
            validate_item_low_stock_threshold(-1)

        with self.assertRaises(ValidationError):
            validate_item_low_stock_threshold(10001)

    def test_validate_item_unit_of_measure(self):
        """Test unit of measure validation."""
        # Valid units
        self.assertEqual(validate_item_unit_of_measure("pieces"), "pieces")
        self.assertEqual(validate_item_unit_of_measure("liters"), "liters")

        # Invalid unit
        with self.assertRaises(ValidationError):
            validate_item_unit_of_measure("invalid_unit")

    def test_validate_item_package_size(self):
        """Test package size validation."""
        # Valid sizes
        self.assertEqual(validate_item_package_size(1000), 1000)
        self.assertEqual(validate_item_package_size("500"), 500)

        # Invalid sizes
        with self.assertRaises(ValidationError):
            validate_item_package_size(0)

        with self.assertRaises(ValidationError):
            validate_item_package_size(1000001)


if __name__ == '__main__':
    unittest.main()