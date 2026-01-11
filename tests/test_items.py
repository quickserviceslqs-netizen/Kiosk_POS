"""Unit tests for items module."""
import unittest
import sys
import os
import tempfile
import shutil

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import initialize_database
from modules import items


class TestItems(unittest.TestCase):
    """Test cases for items module."""

    def setUp(self):
        """Set up test database."""
        # For now, just ensure we have a clean state
        # In a real implementation, you'd create a separate test database
        pass

    def tearDown(self):
        """Clean up."""
        pass

    def test_create_item_valid(self):
        """Test creating a valid item."""
        item = items.create_item(
            name="Test Item",
            category="Test Category",
            selling_price=10.99,
            cost_price=8.50,
            quantity=100,
            unit_of_measure="pieces"
        )

        self.assertIsInstance(item, dict)
        self.assertEqual(item['name'], "Test Item")
        self.assertEqual(item['category'], "Test Category")
        self.assertEqual(item['selling_price'], 10.99)
        self.assertEqual(item['cost_price'], 8.50)
        self.assertEqual(item['quantity'], 100)

    def test_create_item_invalid_name(self):
        """Test creating item with invalid name."""
        with self.assertRaises(ValueError):
            items.create_item(name="", selling_price=10.0)

    def test_create_item_negative_price(self):
        """Test creating item with negative price."""
        with self.assertRaises(ValueError):
            items.create_item(name="Test", selling_price=-5.0)

    def test_create_item_duplicate_barcode(self):
        """Test creating items with duplicate barcodes."""
        items.create_item(name="Item 1", barcode="12345", selling_price=10.0)
        with self.assertRaises(ValueError):
            items.create_item(name="Item 2", barcode="12345", selling_price=15.0)

    def test_update_item(self):
        """Test updating an item."""
        item = items.create_item(name="Original Name", selling_price=10.0)
        updated = items.update_item(item['item_id'], name="Updated Name", selling_price=12.0)

        self.assertEqual(updated['name'], "Updated Name")
        self.assertEqual(updated['selling_price'], 12.0)

    def test_get_item(self):
        """Test retrieving an item."""
        created = items.create_item(name="Test Item", selling_price=10.0)
        retrieved = items.get_item(created['item_id'])

        self.assertEqual(retrieved['name'], "Test Item")
        self.assertEqual(retrieved['selling_price'], 10.0)

    def test_delete_item(self):
        """Test deleting an item."""
        item = items.create_item(name="To Delete", selling_price=10.0)
        result = items.delete_item(item['item_id'])

        self.assertTrue(result)
        # Verify item is gone
        self.assertIsNone(items.get_item(item['item_id']))


if __name__ == '__main__':
    unittest.main()