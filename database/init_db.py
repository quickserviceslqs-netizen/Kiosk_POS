"""SQLite schema initialization for the Kiosk POS app."""
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).with_name("pos.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'cashier')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    cost_price REAL NOT NULL DEFAULT 0,
    selling_price REAL NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 0,
    image_path TEXT,
    barcode TEXT,
    vat_rate REAL NOT NULL DEFAULT 16.0,
    low_stock_threshold INTEGER NOT NULL DEFAULT 10,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    total REAL NOT NULL DEFAULT 0,
    payment REAL NOT NULL DEFAULT 0,
    change REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sales_items (
    sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price REAL NOT NULL DEFAULT 0,
    cost_price REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS expenses (
    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    amount REAL NOT NULL DEFAULT 0,
    user_id INTEGER,
    username TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS vat_rates (
    vat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rate REAL NOT NULL UNIQUE,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def _ensure_expense_columns(conn: sqlite3.Connection) -> None:
    """Add user tracking columns to expenses table if missing."""
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(expenses);")}
    if "user_id" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER")
    if "username" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN username TEXT")
    if "created_at" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN created_at TEXT")


def _ensure_user_columns(conn: sqlite3.Connection) -> None:
    """Apply lightweight migrations for the users table (idempotent)."""
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(users);")}
    if "password_salt" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_salt TEXT;")


def _ensure_item_columns(conn: sqlite3.Connection) -> None:
    """Apply lightweight migrations for the items table (idempotent)."""
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(items);")}
    
    # Add low_stock_threshold if missing
    if "low_stock_threshold" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN low_stock_threshold INTEGER NOT NULL DEFAULT 10")
    
    # Migrate exempt_vat to vat_rate if needed
    if "exempt_vat" in existing_columns and "vat_rate" not in existing_columns:
        # Add vat_rate column
        conn.execute("ALTER TABLE items ADD COLUMN vat_rate REAL NOT NULL DEFAULT 16.0;")
        # Set vat_rate to 0 where exempt_vat = 1, else keep 16
        conn.execute("UPDATE items SET vat_rate = 0 WHERE exempt_vat = 1;")
    elif "vat_rate" not in existing_columns:
        # If neither exists (fresh DB), add vat_rate
        conn.execute("ALTER TABLE items ADD COLUMN vat_rate REAL NOT NULL DEFAULT 16.0;")


def _seed_default_vat_rates(conn: sqlite3.Connection) -> None:
    """Seed default VAT rates if table is empty."""
    count = conn.execute("SELECT COUNT(*) FROM vat_rates").fetchone()[0]
    if count == 0:
        default_rates = [
            (0.0, "VAT Exempt"),
            (8.0, "Reduced Rate"),
            (16.0, "Standard Rate"),
            (18.0, "Higher Rate"),
        ]
        conn.executemany(
            "INSERT INTO vat_rates (rate, description, active) VALUES (?, ?, 1)",
            default_rates
        )
        conn.commit()


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled."""
    resolved = Path(db_path) if db_path else DB_PATH
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database(db_path: Path | None = None) -> Path:
    """Create required tables if they are missing and return the database path."""
    resolved = Path(db_path) if db_path else DB_PATH
    with get_connection(resolved) as conn:
        conn.executescript(SCHEMA)
        _ensure_user_columns(conn)
        _ensure_item_columns(conn)
        _ensure_expense_columns(conn)
        _seed_default_vat_rates(conn)
    return resolved.resolve()
