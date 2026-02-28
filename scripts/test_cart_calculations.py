import sys
sys.path.insert(0, 'C:/Users/ADMIN/Kiosk_POS')
from utils.cart import compute_totals_from_line_totals


def test_no_vat_no_discount():
    entries = [{'_line_total': 10.0}, {'_line_total': 5.0}]
    totals = compute_totals_from_line_totals(entries, discount_pct=0.0, vat_enabled=False, default_vat_percent=16.0)
    assert totals['subtotal'] == 15.0
    assert totals['discount_amt'] == 0.0
    assert totals['vat_amt'] == 0.0
    assert totals['total'] == 15.0


def test_vat_only():
    entries = [{'_line_total': 100.0}]
    totals = compute_totals_from_line_totals(entries, discount_pct=0.0, vat_enabled=True, default_vat_percent=10.0)
    assert abs(totals['vat_amt'] - 10.0) < 1e-6
    assert abs(totals['total'] - 110.0) < 1e-6


def test_discount_only():
    entries = [{'_line_total': 200.0}]
    totals = compute_totals_from_line_totals(entries, discount_pct=0.25, vat_enabled=False)
    assert abs(totals['discount_amt'] - 50.0) < 1e-6
    assert abs(totals['total'] - 150.0) < 1e-6


def test_per_item_vat_override():
    entries = [{'_line_total': 50.0, 'vat_rate': 5.0}, {'_line_total': 50.0}]  # second uses default 20%
    totals = compute_totals_from_line_totals(entries, discount_pct=0.0, vat_enabled=True, default_vat_percent=20.0)
    # VAT = 50*0.05 + 50*0.20 = 2.5 + 10 = 12.5
    assert abs(totals['vat_amt'] - 12.5) < 1e-6
    assert abs(totals['total'] - (100.0 + 12.5)) < 1e-6


def test_vat_disabled_ignores_per_item_rates():
    entries = [{'_line_total': 100.0, 'vat_rate': 10.0}]  # item has 10% rate
    totals = compute_totals_from_line_totals(entries, discount_pct=0.0, vat_enabled=False, default_vat_percent=20.0)
    # Even with per-item rate, VAT should be 0 when disabled
    assert totals['vat_amt'] == 0.0
    assert totals['total'] == 100.0
