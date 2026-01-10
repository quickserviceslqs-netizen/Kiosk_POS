import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules import items, variants, portions, pos
import traceback

# Test variant and portion tracking in sales
try:
    # Create a test item
    item = items.create_item(
        name='Test Item for Variants/Portions',
        category='Test',
        cost_price=5.0,
        selling_price=10.0,
        quantity=100,
        unit_of_measure='pieces'
    )
    print(f'Created item: {item["item_id"]}')

    # Create a variant
    variant = variants.create_variant(
        item_id=item['item_id'],
        variant_name='Large',
        selling_price=12.0,
        cost_price=6.0,
        quantity=50
    )
    print(f'Created variant: {variant}')

    # Create a portion for a different item (special volume)
    portion_item = items.create_item(
        name='Test Drink',
        category='Beverages',
        cost_price=2.0,
        selling_price=5.0,
        quantity=10,
        unit_of_measure='liters',
        is_special_volume=1,
        unit_size_ml=1000
    )
    print(f'Created portion item: {portion_item["item_id"]}')

    portion = portions.create_portion(
        item_id=portion_item['item_id'],
        portion_name='Medium (500ml)',
        portion_ml=500,
        selling_price=3.0,
        cost_price=1.5
    )
    print(f'Created portion: {portion}')

    # Test sale with variant
    variant_sale_lines = [{
        'item_id': item['item_id'],
        'variant_id': variant,
        'quantity': 2,
        'price': 12.0
    }]

    variant_sale = pos.create_sale(
        variant_sale_lines,
        payment=24.0,
        vat_amount=0.0,
        discount_amount=0.0
    )
    print(f'Created variant sale: {variant_sale}')

    # Test sale with portion
    portion_sale_lines = [{
        'item_id': portion_item['item_id'],
        'portion_id': portion['portion_id'],
        'quantity': 500,  # ml
        'price': 0.006  # per ml (3.0 / 500)
    }]

    portion_sale = pos.create_sale(
        portion_sale_lines,
        payment=3.0,
        vat_amount=0.0,
        discount_amount=0.0
    )
    print(f'Created portion sale: {portion_sale}')

    print('All tests passed!')

except Exception as e:
    traceback.print_exc()