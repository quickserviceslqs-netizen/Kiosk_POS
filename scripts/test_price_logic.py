import sys
sys.path.insert(0, r'c:\Users\ADMIN\Kiosk_Pos')

# New semantics: unit_size is expressed in "large" units (e.g., 1 = 1 L, 0.5 = 500 mL)
def compute_price_per_base(price, unit, unit_size):
    return price / unit_size if unit_size > 0 else price

# Test cases
cases = [
    (10.0, 'litre', 1.0, 10.0),   # 10 per 1L -> 10 per L
    (10.0, 'litre', 0.5, 20.0),   # 10 per 0.5L -> 20 per L
    (5.0, 'kg', 1.0, 5.0),        # 5 per 1kg -> 5 per kg
    (5.0, 'kg', 0.5, 10.0),       # 5 per 0.5kg -> 10 per kg
    (2.0, 'pieces', 1.0, 2.0),    # non-fractional
]

for price, unit, unit_size, expected in cases:
    actual = compute_price_per_base(price, unit, unit_size)
    print(price, unit, unit_size, '=>', actual, 'expected', expected)
    assert abs(actual - expected) < 1e-6

print('All tests passed')