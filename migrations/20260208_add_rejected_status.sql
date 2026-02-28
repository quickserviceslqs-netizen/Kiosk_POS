-- Migration: Add 'rejected' to reconciliation_sessions.status CHECK
-- Date: 2026-02-08

PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

-- Create new table with updated CHECK constraint
CREATE TABLE IF NOT EXISTS reconciliation_sessions_new (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reconciliation_date TEXT NOT NULL,
    period_type TEXT NOT NULL CHECK(period_type IN ('daily', 'weekly', 'monthly', 'yearly', 'custom')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    total_system_sales REAL NOT NULL DEFAULT 0,
    total_actual_cash REAL NOT NULL DEFAULT 0,
    total_variance REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'completed', 'approved', 'rejected')),
    reconciled_by INTEGER,
    reconciled_at TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reconciled_by) REFERENCES users(user_id)
);

-- Copy data from old table
INSERT INTO reconciliation_sessions_new (
    session_id, reconciliation_date, period_type, start_date, end_date,
    total_system_sales, total_actual_cash, total_variance, status,
    reconciled_by, reconciled_at, notes, created_at, updated_at
)
SELECT
    session_id, reconciliation_date, period_type, start_date, end_date,
    total_system_sales, total_actual_cash, total_variance, status,
    reconciled_by, reconciled_at, notes, created_at, updated_at
FROM reconciliation_sessions;

-- Replace old table
DROP TABLE reconciliation_sessions;
ALTER TABLE reconciliation_sessions_new RENAME TO reconciliation_sessions;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_reconciliation_sessions_date ON reconciliation_sessions(reconciliation_date);
CREATE INDEX IF NOT EXISTS idx_reconciliation_sessions_period ON reconciliation_sessions(start_date, end_date);

COMMIT;
PRAGMA foreign_keys=on;
