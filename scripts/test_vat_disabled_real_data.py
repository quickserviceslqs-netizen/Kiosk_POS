import sys
sys.path.insert(0, 'C:/Users/ADMIN/Kiosk_POS')
from modules import items
from utils.cart import compute_totals_from_line_totals
from utils.security import get_cart_vat_enabled, set_cart_vat_enabled

def test_vat_disabled_with_real_items():
    # Ensure VAT is disabled
    set_cart_vat_enabled(False)
    assert not get_cart_vat_enabled(), "VAT should be disabled for this test"

    # Get items from DB that have vat_rate set
    all_items = items.list_items()
    items_with_vat = [item for item in all_items if item.get('vat_rate') is not None and item.get('vat_rate') > 0]

    if not items_with_vat:
        print("No items with VAT rates found - creating test item")
        # Create a test item with VAT rate
        test_item = items.create_item(
            name='VAT Test Item',
            selling_price=100.0,
            unit_of_measure='pieces',
            unit_size_ml=1,
            quantity=10,
            vat_rate=15.0  # 15% VAT
        )
        items_with_vat = [test_item]

    # Simulate cart entries
    cart_entries = []
    for item in items_with_vat[:3]:  # Test with up to 3 items
        entry = {
            'item_id': item['item_id'],
            'price': item['selling_price'],
            'quantity': 2,
            '_line_total': item['selling_price'] * 2,
            'vat_rate': item.get('vat_rate')
        }
        cart_entries.append(entry)

    # Compute totals with VAT disabled
    totals = compute_totals_from_line_totals(
        cart_entries,
        discount_pct=0.0,
        vat_enabled=False,  # Explicitly disabled
        default_vat_percent=16.0
    )

    print(f"Items tested: {len(cart_entries)}")
    print(f"Subtotal: {totals['subtotal']}")
    print(f"VAT Amount: {totals['vat_amt']}")
    print(f"Total: {totals['total']}")

    # Assert VAT is 0 even though items have rates
    assert totals['vat_amt'] == 0.0, f"VAT should be 0 when disabled, got {totals['vat_amt']}"
    assert totals['total'] == totals['subtotal'], "Total should equal subtotal when VAT disabled"

    print("✅ Test passed: VAT correctly ignored when system VAT is disabled")

    # Cleanup test item if created
    if 'test_item' in locals():
        items.delete_item(test_item['item_id'])

if __name__ == '__main__':
    test_vat_disabled_with_real_items()