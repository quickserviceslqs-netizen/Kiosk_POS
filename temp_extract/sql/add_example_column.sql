-- Example upgrade: Add a sample column to demonstrate SQL upgrades
-- This adds an 'example_column' to the settings table for demonstration

ALTER TABLE settings ADD COLUMN example_column TEXT DEFAULT 'upgrade_demo';

-- Insert a sample setting to show the upgrade worked
INSERT OR REPLACE INTO settings (key, value) VALUES ('upgrade_demo_version', '1.0.1');

-- Log the upgrade
INSERT OR IGNORE INTO settings (key, value) VALUES ('last_upgrade_applied', datetime('now'));