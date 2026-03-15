-- Migration: Add selling_price column to stock_lots table
-- Date: 2026-03-14
-- Description: Adds lot-specific selling prices to allow different pricing for different stock lots

ALTER TABLE stock_lots ADD COLUMN selling_price REAL;