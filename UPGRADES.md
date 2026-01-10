# Upgrade Packages (Kiosk POS)

This document describes the upgrade package format and safety notes for applying upgrades to Kiosk POS installations.

## Package format
- A package is a ZIP file containing:
  - `upgrade.json` (manifest) — required
  - step files referenced by the manifest (SQL, Python scripts, files to copy, commands, etc.)

Example manifest:

{
  "version": "1.1.0",
  "min_app_version": "1.0.0",
  "steps": [
    {"type": "sql", "file": "sql/001_create_table.sql"},
    {"type": "python", "file": "py/002_migration.py"},
    {"type": "copy", "src": "bin/myplugin.py", "dest": "plugins/myplugin.py"},
    {"type": "command", "cmd": "echo done"}
  ]
}

## Steps
- sql: executes an SQL script with `executescript` on the SQLite DB.
- python: runs a Python script in a subprocess (isolated process). Use this for complex logic.
- copy: copies files from the package into the install directory. Overwritten files are backed up.
- command: runs a shell command from the package directory.

## Safety & rollback
- The apply runner creates a DB backup before applying. On error, it attempts to restore the DB.
- Files that are overwritten are backed up before replacement; the runner does not yet support automatic restore of file backups on all error paths — apply with care.
- Use the `--dry-run` mode or the UI Dry Run to validate packages prior to applying.

## Usage
- CLI: `python scripts/apply_upgrade.py package.zip [--dry-run] [--db-path path]`
- UI: `ui/upgrade_manager.py` (admin-only window in the app; select package, Preview, Dry Run, Apply)

## Security
- **Important**: Only apply packages from trusted sources. Implementing signature verification is recommended for distribution environments.

