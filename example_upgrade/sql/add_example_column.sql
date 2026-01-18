-- Example upgrade: Sample SQL operations
-- The column addition is now handled by the Python migration script

-- Insert a sample setting to show the upgrade worked
INSERT OR REPLACE INTO settings (key, value) VALUES ('upgrade_demo_version', '1.0.1');

-- Log the upgrade
INSERT OR IGNORE INTO settings (key, value) VALUES ('last_upgrade_applied', datetime('now'));