import sqlite3
import pathlib

for p in pathlib.Path('database').glob('*.db'):
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    # Only run if items table exists
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    if 'items' in tables:
        # Normalize 'pieces' that incorrectly had 1000 default
        updated_pieces = cur.execute("UPDATE items SET unit_size_ml = 1 WHERE lower(unit_of_measure) = 'pieces' AND unit_size_ml = 1000").rowcount
        # Normalize litre/kg entries that used 1000 where it really means '1' (e.g., 1000 -> 1 litre)
        updated_liters = cur.execute("UPDATE items SET unit_size_ml = CAST(unit_size_ml / 1000 AS INTEGER) WHERE lower(unit_of_measure) IN ('liters','litre','liter','litres','l','kilograms','kilogram','kg','kgs') AND unit_size_ml >= 1000").rowcount
        # Normalize meters where 100 means 1 (cm->m conversion)
        updated_meters = cur.execute("UPDATE items SET unit_size_ml = CAST(unit_size_ml / 100 AS INTEGER) WHERE lower(unit_of_measure) IN ('meters','meter','metre','metres','m') AND unit_size_ml >= 100").rowcount
        conn.commit()
        print(f"{p}: pieces={updated_pieces} liters/kg={updated_liters} meters={updated_meters}")
    else:
        print(f"{p}: no items table; skipping")
    conn.close()
