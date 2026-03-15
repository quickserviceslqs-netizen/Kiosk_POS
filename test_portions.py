from modules.portions import create_default_portions

# Test with milliliters unit
portions = create_default_portions(55, unit_of_measure='milliliters')
print('Portions created for milliliters:')
for p in portions:
    print(f'  {p["portion_name"]}')

# Test with liters unit
portions_liters = create_default_portions(55, unit_of_measure='liters')
print('\nPortions created for liters:')
for p in portions_liters:
    print(f'  {p["portion_name"]}')