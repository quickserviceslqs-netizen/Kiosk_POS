-- Add loyalty points system to Kiosk POS
-- This migration adds tables and columns for customer loyalty tracking

-- Create loyalty_customers table
CREATE TABLE IF NOT EXISTS loyalty_customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    phone TEXT UNIQUE,
    email TEXT,
    total_points INTEGER DEFAULT 0,
    used_points INTEGER DEFAULT 0,
    available_points INTEGER GENERATED ALWAYS AS (total_points - used_points) STORED,
    member_since DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended'))
);

-- Create loyalty_transactions table for point history
CREATE TABLE IF NOT EXISTS loyalty_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('earned', 'redeemed', 'expired', 'adjusted')),
    points INTEGER NOT NULL,
    sale_id INTEGER,
    description TEXT,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES loyalty_customers(id),
    FOREIGN KEY (sale_id) REFERENCES sales(id)
);

-- Note: Column additions are handled by the Python script to avoid duplicate column errors
-- The Python script will check if columns exist before adding them

-- Add loyalty settings to settings table
INSERT OR REPLACE INTO settings (key, value) VALUES
('loyalty_enabled', 'true'),
('points_per_dollar', '1'),
('redemption_rate', '100'),  -- 100 points = $1.00
('points_expiry_months', '24'),
('min_points_redemption', '100');

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_loyalty_customers_phone ON loyalty_customers(phone);
CREATE INDEX IF NOT EXISTS idx_loyalty_transactions_customer ON loyalty_transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_loyalty_transactions_date ON loyalty_transactions(transaction_date);

-- Insert sample loyalty customer for testing
INSERT OR IGNORE INTO loyalty_customers (customer_name, phone, total_points)
VALUES ('Demo Customer', '+1234567890', 500);