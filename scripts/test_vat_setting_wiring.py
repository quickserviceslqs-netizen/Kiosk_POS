import sys
sys.path.insert(0, 'C:/Users/ADMIN/Kiosk_POS')
from modules import items
from utils.security import set_vat_rate, get_vat_rate


def test_vat_setting_wiring():
    # Set VAT to a non-default value and ensure calculations use it
    set_vat_rate(12.5)
    assert abs(get_vat_rate() - 12.5) < 1e-9

    it = items.create_item(name='VAT Wiring UnitTest', selling_price=200.0, unit_of_measure='pieces', unit_size_ml=1, quantity=5)
    try:
        entry = {'item_id': it['item_id'], 'price': it['selling_price'], 'quantity': 1}
        default_vat = float(get_vat_rate())
        item_vat_rate = float(entry.get('vat_rate', default_vat)) / 100.0
        line_total = entry['price'] * entry['quantity']
        vat_amt = line_total * item_vat_rate
        assert abs(vat_amt - (200.0 * 0.125)) < 1e-6
    finally:
        items.delete_item(it['item_id'])
