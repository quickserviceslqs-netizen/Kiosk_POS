from modules.portions import create_default_portions, get_unit_info_from_name

# Test different units
test_units = ['liters', 'ml', 'kg', 'g', 'meter', 'cm', 'lb', 'oz', 'gallon', 'quart', 'pint', 'yard', 'foot', 'inch']

for unit in test_units:
    try:
        unit_info = get_unit_info_from_name(unit)
        print(f'\n{unit}: {unit_info}')
        
        # Test portion creation (without actually creating them)
        portions = create_default_portions(55, unit_of_measure=unit)
        print(f'  Would create {len(portions)} portions:')
        for p in portions[:2]:  # Show first 2
            print(f'    {p["portion_name"]}')
    except Exception as e:
        print(f'  ERROR: {e}')
