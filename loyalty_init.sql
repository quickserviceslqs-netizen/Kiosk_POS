-- Initialize loyalty points data
-- This SQL runs after the schema is created

-- Insert sample loyalty customer for testing (if not exists)
INSERT OR IGNORE INTO loyalty_customers (customer_name, phone, total_points)
VALUES ('Demo Customer', '+1234567890', 500);

-- Insert a sample transaction for the demo customer
INSERT OR IGNORE INTO loyalty_transactions (customer_id, transaction_type, points, description)
SELECT id, 'earned', 500, 'Initial demo points'
FROM loyalty_customers
WHERE customer_name = 'Demo Customer'
LIMIT 1;

-- Update settings to ensure loyalty is enabled
INSERT OR REPLACE INTO settings (key, value) VALUES
('loyalty_enabled', 'true'),
('points_per_dollar', '1'),
('redemption_rate', '100'),
('points_expiry_months', '24'),
('min_points_redemption', '100');