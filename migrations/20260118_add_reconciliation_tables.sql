-- Migration: Add reconciliation tables
-- Date: 2026-01-18

-- Main reconciliation sessions table
CREATE TABLE IF NOT EXISTS reconciliation_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reconciliation_date TEXT NOT NULL,
    period_type TEXT NOT NULL CHECK(period_type IN ('daily', 'weekly', 'monthly', 'yearly', 'custom')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    total_system_sales REAL NOT NULL DEFAULT 0,
    total_actual_cash REAL NOT NULL DEFAULT 0,
    total_variance REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'completed', 'approved')),
    reconciled_by INTEGER,
    reconciled_at TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reconciled_by) REFERENCES users(user_id)
);

-- Reconciliation entries by payment method
CREATE TABLE IF NOT EXISTS reconciliation_entries (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    system_amount REAL NOT NULL DEFAULT 0,
    actual_amount REAL NOT NULL DEFAULT 0,
    variance REAL NOT NULL DEFAULT 0,
    explanation TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES reconciliation_sessions(session_id) ON DELETE CASCADE
);

-- Reconciliation explanations/notes
CREATE TABLE IF NOT EXISTS reconciliation_explanations (
    explanation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    explanation_type TEXT NOT NULL CHECK(explanation_type IN ('general', 'payment_method', 'variance')),
    payment_method TEXT, -- NULL for general explanations
    explanation TEXT NOT NULL,
    amount REAL DEFAULT 0,
    created_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES reconciliation_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_reconciliation_sessions_date ON reconciliation_sessions(reconciliation_date);
CREATE INDEX IF NOT EXISTS idx_reconciliation_sessions_period ON reconciliation_sessions(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_reconciliation_entries_session ON reconciliation_entries(session_id);
CREATE INDEX IF NOT EXISTS idx_reconciliation_explanations_session ON reconciliation_explanations(session_id);