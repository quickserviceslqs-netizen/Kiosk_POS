"""Database migration system for schema updates."""
from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any

from database.init_db import get_connection


MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"
MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    checksum TEXT NOT NULL
);
"""


class Migration:
    """Represents a database migration."""

    def __init__(self, migration_id: str, name: str, up_sql: str, down_sql: str = ""):
        self.id = migration_id
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """Calculate checksum of migration content."""
        import hashlib
        content = f"{self.up_sql}{self.down_sql}"
        return hashlib.sha256(content.encode()).hexdigest()


def initialize_migrations():
    """Initialize the migrations system."""
    MIGRATIONS_DIR.mkdir(exist_ok=True)

    with get_connection() as conn:
        conn.execute(MIGRATIONS_TABLE)
        conn.commit()


def get_applied_migrations() -> Dict[str, str]:
    """Get list of applied migrations with their checksums."""
    with get_connection() as conn:
        rows = conn.execute("SELECT migration_id, checksum FROM schema_migrations").fetchall()
        return {row[0]: row[1] for row in rows}


def apply_migration(migration: Migration) -> None:
    """Apply a migration."""
    with get_connection() as conn:
        try:
            # Execute migration SQL
            conn.executescript(migration.up_sql)

            # Record the migration
            conn.execute(
                "INSERT INTO schema_migrations (migration_id, name, checksum) VALUES (?, ?, ?)",
                (migration.id, migration.name, migration.checksum)
            )

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to apply migration {migration.id}: {e}")


def rollback_migration(migration_id: str) -> None:
    """Rollback a migration."""
    # Load migration file to get down SQL
    migration_file = MIGRATIONS_DIR / f"{migration_id}.json"
    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file {migration_id}.json not found")

    with open(migration_file, 'r') as f:
        data = json.load(f)

    migration = Migration(
        data['id'],
        data['name'],
        data['up_sql'],
        data.get('down_sql', '')
    )

    if not migration.down_sql:
        raise ValueError(f"Migration {migration_id} does not have rollback SQL")

    with get_connection() as conn:
        try:
            # Execute rollback SQL
            conn.executescript(migration.down_sql)

            # Remove migration record
            conn.execute("DELETE FROM schema_migrations WHERE migration_id = ?", (migration_id,))

            conn.commit()
        except Exception as e:
            conn.rollback()
            raise RuntimeError(f"Failed to rollback migration {migration_id}: {e}")


def create_migration(name: str, up_sql: str, down_sql: str = "") -> str:
    """Create a new migration file."""
    import uuid
    migration_id = str(uuid.uuid4())[:8]

    migration_data = {
        'id': migration_id,
        'name': name,
        'up_sql': up_sql,
        'down_sql': down_sql,
        'created_at': str(Path(__file__).parent.parent / "migrations" / f"{migration_id}.json")
    }

    migration_file = MIGRATIONS_DIR / f"{migration_id}.json"
    with open(migration_file, 'w') as f:
        json.dump(migration_data, f, indent=2)

    return migration_id


def run_pending_migrations() -> List[str]:
    """Run all pending migrations."""
    initialize_migrations()

    applied = get_applied_migrations()
    applied_migrations = []

    # Get all migration files
    migration_files = sorted(MIGRATIONS_DIR.glob("*.json"))

    for migration_file in migration_files:
        migration_id = migration_file.stem

        if migration_id in applied:
            continue

        # Load migration
        with open(migration_file, 'r') as f:
            data = json.load(f)

        migration = Migration(
            data['id'],
            data['name'],
            data['up_sql'],
            data.get('down_sql', '')
        )

        # Check if checksum matches (prevent tampering)
        if migration.checksum != applied.get(migration_id):
            apply_migration(migration)
            applied_migrations.append(migration_id)

    return applied_migrations


def get_migration_status() -> Dict[str, Any]:
    """Get status of all migrations."""
    initialize_migrations()

    applied = get_applied_migrations()

    status = {
        'applied': [],
        'pending': []
    }

    # Get all migration files
    migration_files = sorted(MIGRATIONS_DIR.glob("*.json"))

    for migration_file in migration_files:
        migration_id = migration_file.stem

        with open(migration_file, 'r') as f:
            data = json.load(f)

        migration_info = {
            'id': migration_id,
            'name': data['name'],
            'applied': migration_id in applied
        }

        if migration_info['applied']:
            status['applied'].append(migration_info)
        else:
            status['pending'].append(migration_info)

    return status