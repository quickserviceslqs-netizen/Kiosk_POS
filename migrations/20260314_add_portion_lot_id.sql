-- Add lot_id column to item_portions table for lot-based pricing
ALTER TABLE item_portions ADD COLUMN lot_id INTEGER REFERENCES stock_lots(lot_id);