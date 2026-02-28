-- Migration: Add reviewed flag to reconciliation_entries
-- Date: 2026-01-25

ALTER TABLE reconciliation_entries ADD COLUMN reviewed INTEGER NOT NULL DEFAULT 0;
