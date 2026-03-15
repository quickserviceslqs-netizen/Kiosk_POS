-- Migration: Add preferred_lot_id column to items table
-- Date: 2026-03-14
-- Description: Adds a reference to a preferred stock lot for determining item pricing

ALTER TABLE items ADD COLUMN preferred_lot_id INTEGER REFERENCES stock_lots(lot_id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_items_preferred_lot ON items(preferred_lot_id);
