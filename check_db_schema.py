import sqlite3
import os

# Check which database to use
config_path = 'config.json'
db_path = 'database/pos.db'  # default
if os.path.exists(config_path):
    import json
    with open(config_path, 'r') as f:
        config = json.load(f)
        db_path = config.get('db_path', db_path)

print(f'Using database: {db_path}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('Tables in database:')
    for table in tables:
        print(f'  {table[0]}')

    if 'item_portions' in [t[0] for t in tables]:
        cursor.execute('PRAGMA table_info(item_portions)')
        columns = cursor.fetchall()
        print('\nColumns in item_portions:')
        for col in columns:
            print(f'  {col[1]}: {col[2]}')

        # Check total portions
        cursor.execute('SELECT COUNT(*) FROM item_portions')
        count = cursor.fetchone()[0]
        print(f'\nTotal portions: {count}')

        # Check portions with lot_id
        cursor.execute('SELECT COUNT(*) FROM item_portions WHERE lot_id IS NOT NULL')
        lot_count = cursor.fetchone()[0]
        print(f'Portions with lot_id assigned: {lot_count}')

        if count > 0:
            cursor.execute('SELECT item_id, portion_name, lot_id FROM item_portions LIMIT 5')
            portions = cursor.fetchall()
            print('\nSample portions:')
            for p in portions:
                print(f'  Item {p[0]}: {p[1]} (lot_id: {p[2]})')

    # Check special volume items
    cursor.execute('SELECT COUNT(*) FROM items WHERE is_special_volume = 1')
    special_count = cursor.fetchone()[0]
    print(f'\nSpecial volume items: {special_count}')

    if special_count > 0:
        cursor.execute('SELECT item_id, name FROM items WHERE is_special_volume = 1 LIMIT 5')
        special_items = cursor.fetchall()
        print('Sample special volume items:')
        for item in special_items:
            print(f'  Item {item[0]}: {item[1]}')

    conn.close()
else:
    print('Database file does not exist')