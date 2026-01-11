-- Migration: Add strong constraints to items table for data integrity
-- Date: 2026-01-11

PRAGMA foreign_keys=off;

BEGIN TRANSACTION;

-- 1. Create new table with constraints
CREATE TABLE IF NOT EXISTS items_new (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL CHECK(length(name) > 0),
    category TEXT,
    cost_price REAL NOT NULL CHECK(cost_price >= 0),
    selling_price REAL NOT NULL CHECK(selling_price >= 0),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
    image_path TEXT,
    barcode TEXT UNIQUE,
    vat_rate REAL NOT NULL DEFAULT 16.0 CHECK(vat_rate >= 0 AND vat_rate <= 100),
    low_stock_threshold INTEGER NOT NULL DEFAULT 10 CHECK(low_stock_threshold >= 0 AND low_stock_threshold <= 10000),
    unit_of_measure TEXT NOT NULL CHECK(length(unit_of_measure) > 0),
    is_special_volume INTEGER NOT NULL DEFAULT 0 CHECK(is_special_volume IN (0,1)),
    unit_size_ml INTEGER NOT NULL DEFAULT 1 CHECK(unit_size_ml > 0 AND unit_size_ml <= 1000000),
    price_per_ml REAL,
    cost_price_per_unit REAL,
    unit_multiplier REAL,
    selling_price_per_unit REAL
);

-- 2. Copy data from old table (ignore rows that violate new constraints)
INSERT OR IGNORE INTO items_new (
    item_id, name, category, cost_price, selling_price, quantity, image_path, barcode, vat_rate, low_stock_threshold, unit_of_measure, is_special_volume, unit_size_ml, price_per_ml, cost_price_per_unit, unit_multiplier, selling_price_per_unit
)
SELECT 
    item_id, name, category, cost_price, selling_price, quantity, image_path, barcode, vat_rate, low_stock_threshold, unit_of_measure, is_special_volume, unit_size_ml, price_per_ml, cost_price_per_unit, unit_multiplier, selling_price_per_unit
FROM items;

-- 3. Drop old table and rename new one
DROP TABLE items;
ALTER TABLE items_new RENAME TO items;

COMMIT;

PRAGMA foreign_keys=on;
