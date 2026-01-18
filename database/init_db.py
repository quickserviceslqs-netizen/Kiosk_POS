"""SQLite schema initialization for the Kiosk POS app."""
from pathlib import Path
import sqlite3
import threading
from typing import Optional

DB_PATH = Path(__file__).parent / "pos.db"

# Thread-local storage for connection caching
_local = threading.local()

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

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS expense_categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS units_of_measure (
    uom_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    abbreviation TEXT,
    conversion_factor REAL NOT NULL DEFAULT 1,
    base_unit TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS item_variants (
    variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    variant_name TEXT NOT NULL,
    selling_price REAL NOT NULL DEFAULT 0,
    cost_price REAL NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 0,
    barcode TEXT,
    sku TEXT,
    vat_rate REAL NOT NULL DEFAULT 16.0,
    low_stock_threshold INTEGER NOT NULL DEFAULT 10,
    image_path TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS item_portions (
    portion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    portion_name TEXT NOT NULL,
    portion_ml REAL NOT NULL,
    selling_price REAL NOT NULL DEFAULT 0,
    cost_price REAL NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id INTEGER PRIMARY KEY AUTOINCREMENT,
    refund_code TEXT UNIQUE,
    original_sale_id INTEGER NOT NULL,
    refund_amount REAL NOT NULL DEFAULT 0,
    reason TEXT,
    receipt_number TEXT,
    user_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""


def _pragma_columns(conn: sqlite3.Connection, table_name: str) -> set:
    """Return a set of column names for the given table, tolerant of different row types."""
    cols = set()
    for r in conn.execute(f"PRAGMA table_info({table_name});"):
        try:
            cols.add(r[1])
        except Exception:
            try:
                cols.add(tuple(r)[1])
            except Exception:
                # Skip rows that cannot be parsed
                pass
    return cols


def _ensure_expense_columns(conn: sqlite3.Connection) -> None:
    """Add user tracking columns to expenses table if missing."""
    existing_columns = _pragma_columns(conn, 'expenses')
    if "user_id" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER")
    if "username" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN username TEXT")
    if "created_at" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN created_at TEXT")
    if "currency_code" not in existing_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN currency_code TEXT DEFAULT NULL")


def _ensure_refunds_table(conn: sqlite3.Connection) -> None:
    """Ensure refunds table has expected columns and migrate legacy names if present."""
    existing_columns = _pragma_columns(conn, 'refunds')

    # Add modern columns if missing
    if "refund_code" not in existing_columns:
        # SQLite cannot add UNIQUE constraints via ALTER TABLE; add column then create an index
        conn.execute("ALTER TABLE refunds ADD COLUMN refund_code TEXT")
        try:
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_refunds_refund_code ON refunds(refund_code);")
        except Exception:
            # If index creation fails for duplicate values, leave column as-is
            pass
    if "original_sale_id" not in existing_columns:
        conn.execute("ALTER TABLE refunds ADD COLUMN original_sale_id INTEGER NOT NULL DEFAULT 0")
        # Migrate old sale_id values if present
        if "sale_id" in existing_columns:
            conn.execute("UPDATE refunds SET original_sale_id = sale_id WHERE original_sale_id = 0")
    if "refund_amount" not in existing_columns:
        conn.execute("ALTER TABLE refunds ADD COLUMN refund_amount REAL NOT NULL DEFAULT 0")
        # Migrate old amount values if present
        if "amount" in existing_columns:
            conn.execute("UPDATE refunds SET refund_amount = amount WHERE refund_amount = 0")
    if "receipt_number" not in existing_columns:
        conn.execute("ALTER TABLE refunds ADD COLUMN receipt_number TEXT")
    if "created_at" not in existing_columns:
        conn.execute("ALTER TABLE refunds ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")

    # Ensure refunds_items table exists to track refunded line items (sale_item level)
    # This allows partial and multiple refunds per sale to be tracked precisely.
    existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "refunds_items" not in existing_tables:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refunds_items (
                refund_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                refund_id INTEGER NOT NULL,
                sale_item_id INTEGER,
                sale_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (refund_id) REFERENCES refunds(refund_id) ON DELETE CASCADE,
                FOREIGN KEY (sale_item_id) REFERENCES sales_items(sale_item_id) ON DELETE SET NULL,
                FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items(item_id)
            );
            """
        )
    # Ensure foreign key columns exist; leave existing legacy columns intact
    conn.commit()


def _ensure_user_columns(conn: sqlite3.Connection) -> None:
    """Apply lightweight migrations for the users table (idempotent)."""
    # Some DB connections may have different row types; be tolerant when extracting column names
    existing_columns = set()
    for r in conn.execute("PRAGMA table_info(users);"):
        try:
            existing_columns.add(r[1])
        except Exception:
            try:
                existing_columns.add(tuple(r)[1])
            except Exception:
                # Give up on this row if unexpectedly shaped
                pass

    if "password_salt" not in existing_columns:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN password_salt TEXT;")
        except Exception:
            # If column already exists or alter fails for any reason, continue silently
            pass
    if "plain_password" not in existing_columns:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN plain_password TEXT;")
        except Exception:
            pass


def _ensure_item_columns(conn: sqlite3.Connection) -> None:
    """Apply lightweight migrations for the items table (idempotent)."""
    existing_columns = _pragma_columns(conn, 'items')
    
    # Add low_stock_threshold if missing
    if "low_stock_threshold" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN low_stock_threshold INTEGER NOT NULL DEFAULT 10")
        except Exception:
            pass

    # Add currency_code if missing
    if "currency_code" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN currency_code TEXT DEFAULT NULL")
        except Exception:
            pass

    # Add fractional/volume support columns
    if "is_special_volume" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN is_special_volume INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
    if "unit_size_ml" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN unit_size_ml INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass
        # Migrate legacy records: if an older DB used the previous default (1000)
        # and the item is measured in 'pieces' (non-volume), reset to 1.
        try:
            conn.execute("UPDATE items SET unit_size_ml = 1 WHERE unit_of_measure = 'pieces' AND unit_size_ml = 1000")
        except Exception:
            # If update fails (e.g., no such rows), continue silently
            pass
    if "unit_multiplier" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN unit_multiplier REAL NOT NULL DEFAULT 1.0")
        except Exception:
            pass
    if "unit_of_measure" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN unit_of_measure TEXT DEFAULT 'pieces'")
        except Exception:
            pass

    # Add per-unit price/cost columns used by POS calculations
    if "price_per_ml" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN price_per_ml REAL DEFAULT NULL")
        except Exception:
            pass
    if "cost_price_per_unit" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN cost_price_per_unit REAL DEFAULT NULL")
        except Exception:
            pass
    if "selling_price_per_unit" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN selling_price_per_unit REAL DEFAULT NULL")
        except Exception:
            pass

    # Recalculate per-item small-unit pricing where it is missing or stale
    def _recalculate_per_unit_values(conn: sqlite3.Connection) -> None:
        conversions = {
            "litre": 1000, "liter": 1000, "liters": 1000, "litres": 1000, "l": 1000,
            "kilogram": 1000, "kilograms": 1000, "kg": 1000, "kgs": 1000,
            "meter": 100, "meters": 100, "metre": 100, "metres": 100, "m": 100,
        }
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT item_id, selling_price, cost_price, unit_of_measure, unit_size_ml FROM items').fetchall()
        for r in rows:
            unit = (r['unit_of_measure'] or 'pieces').lower()
            unit_size = float(r['unit_size_ml'] or 1)
            multiplier = conversions.get(unit, 1)
            total_small_units = unit_size * multiplier
            selling = float(r['selling_price'] or 0)
            cost = float(r['cost_price'] or 0)
            sp_small = selling / total_small_units if total_small_units > 0 else None
            cp_small = cost / total_small_units if total_small_units > 0 else None
            conn.execute('UPDATE items SET selling_price_per_unit = ?, cost_price_per_unit = ? WHERE item_id = ?', (sp_small, cp_small, r['item_id']))
        conn.commit()

    if "price_per_ml" not in existing_columns:
        # Newly added - safe to try an initial recalc
        try:
            _recalculate_per_unit_values(conn)
        except Exception:
            pass

    # Add has_variants flag to items if missing so UI can persist the checkbox state
    if "has_variants" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN has_variants INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

    # Add is_catalog_only flag so parent items can be marked as catalog-only (not sellable directly)
    if "is_catalog_only" not in existing_columns:
        try:
            conn.execute("ALTER TABLE items ADD COLUMN is_catalog_only INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        # If there are existing variants, mark those parents as catalog-only
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT DISTINCT item_id FROM item_variants").fetchall()
            for r in rows:
                iid = r['item_id'] if isinstance(r, dict) else r[0]
                conn.execute("UPDATE items SET is_catalog_only = 1 WHERE item_id = ?", (iid,))
            conn.commit()
        except Exception:
            # If item_variants table doesn't exist yet or any error occurs, ignore safely
            pass


def get_setting(key: str) -> str | None:
    """Retrieve a setting value from the settings table. Returns None if not found."""
    from typing import Optional
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return row['value'] if isinstance(row, dict) else row[0]
        return None
    except Exception:
        return None


def set_setting(key: str, value: str) -> None:
    """Persist a setting value into the settings table (insert or update)."""
    try:
        with get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
    except Exception:
        # Swallow errors to avoid breaking UI on non-critical settings
        pass


def recalculate_per_unit_values(db_path: Path | None = None) -> int:
    """Recalculate and persist per-small-unit prices for all items.

    Returns the number of items updated.
    """
    updated = 0
    with get_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT item_id, selling_price, cost_price, unit_of_measure, unit_size_ml FROM items').fetchall()
        for r in rows:
            unit = (r['unit_of_measure'] or 'pieces').lower()
            unit_size = float(r['unit_size_ml'] or 1)
            # Use the units_of_measure module for conversion where possible
            try:
                from modules import units_of_measure as _uom
                multiplier = float(_uom.get_conversion_factor(unit) or 1)
            except Exception:
                multiplier = 1
            total_small_units = unit_size * multiplier
            selling = float(r['selling_price'] or 0)
            cost = float(r['cost_price'] or 0)
            sp_small = selling / total_small_units if total_small_units > 0 else None
            cp_small = cost / total_small_units if total_small_units > 0 else None
            conn.execute('UPDATE items SET selling_price_per_unit = ?, cost_price_per_unit = ? WHERE item_id = ?', (sp_small, cp_small, r['item_id']))
            updated += 1
        conn.commit()
    return updated

    # Migrate exempt_vat to vat_rate if needed
    if "exempt_vat" in existing_columns and "vat_rate" not in existing_columns:
        # Add vat_rate column
        conn.execute("ALTER TABLE items ADD COLUMN vat_rate REAL NOT NULL DEFAULT 16.0;")
        # Set vat_rate to 0 where exempt_vat = 1, else keep 16
        conn.execute("UPDATE items SET vat_rate = 0 WHERE exempt_vat = 1;")
    elif "vat_rate" not in existing_columns:
        # If neither exists (fresh DB), add vat_rate
        conn.execute("ALTER TABLE items ADD COLUMN vat_rate REAL NOT NULL DEFAULT 16.0;")

def _ensure_inventory_categories_table(conn: sqlite3.Connection) -> None:
    """Ensure inventory_categories table exists."""
    existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "inventory_categories" not in existing_tables:
        conn.execute("""
            CREATE TABLE inventory_categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
    conn.commit()


def _ensure_expense_categories_table(conn: sqlite3.Connection) -> None:
    """Ensure expense_categories table exists."""
    existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "expense_categories" not in existing_tables:
        conn.execute("""
            CREATE TABLE expense_categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
    conn.commit()


def _ensure_units_of_measure_table(conn: sqlite3.Connection) -> None:
    """Ensure units_of_measure table exists with all required columns."""
    existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "units_of_measure" not in existing_tables:
        conn.execute("""
            CREATE TABLE units_of_measure (
                uom_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                abbreviation TEXT,
                conversion_factor REAL NOT NULL DEFAULT 1,
                base_unit TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # Add missing columns if table exists but is missing columns
        existing_columns = _pragma_columns(conn, 'units_of_measure')
        if "conversion_factor" not in existing_columns:
            conn.execute("ALTER TABLE units_of_measure ADD COLUMN conversion_factor REAL NOT NULL DEFAULT 1")
        if "base_unit" not in existing_columns:
            conn.execute("ALTER TABLE units_of_measure ADD COLUMN base_unit TEXT")
    conn.commit()


def _ensure_item_variants_table(conn: sqlite3.Connection) -> None:
    """Ensure item_variants table exists."""
    existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "item_variants" not in existing_tables:
        conn.execute("""
            CREATE TABLE item_variants (
                variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                variant_name TEXT NOT NULL,
                selling_price REAL NOT NULL DEFAULT 0,
                cost_price REAL NOT NULL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0,
                barcode TEXT,
                sku TEXT,
                vat_rate REAL NOT NULL DEFAULT 16.0,
                low_stock_threshold INTEGER NOT NULL DEFAULT 10,
                image_path TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
            )
        """)
    conn.commit()


def _ensure_item_portions_table(conn: sqlite3.Connection) -> None:
    """Ensure item_portions table exists with expected columns."""
    existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "item_portions" not in existing_tables:
        conn.execute("""
            CREATE TABLE item_portions (
                portion_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                portion_name TEXT NOT NULL,
                portion_ml REAL NOT NULL,
                selling_price REAL NOT NULL DEFAULT 0,
                cost_price REAL NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE
            )
        """)
    conn.commit()


def _ensure_sales_columns(conn: sqlite3.Connection) -> None:
    """Add missing columns to sales table used by POS logic."""
    existing = _pragma_columns(conn, 'sales')
    # Add receipt_number
    if "receipt_number" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN receipt_number TEXT")
    if "payment_received" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN payment_received REAL DEFAULT 0")
    if "payment_method" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT DEFAULT 'Cash'")
    if "subtotal" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN subtotal REAL DEFAULT 0")
    if "vat_amount" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN vat_amount REAL DEFAULT 0")
    if "discount_amount" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN discount_amount REAL DEFAULT 0")
    # Add user tracking column if missing (who processed the sale)
    if "user_id" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN user_id INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_user_id ON sales(user_id)")
    # Add voided sale tracking columns
    if "voided" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN voided INTEGER DEFAULT 0")
    if "voided_at" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN voided_at TEXT")
    if "voided_by" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN voided_by INTEGER")
    if "void_reason" not in existing:
        conn.execute("ALTER TABLE sales ADD COLUMN void_reason TEXT")
    conn.commit()


def _ensure_sales_items_columns(conn: sqlite3.Connection) -> None:
    """Add missing columns to sales_items table for variant and portion tracking."""
    existing = _pragma_columns(conn, 'sales_items')    # Add variant_id for tracking specific variants sold
    if "variant_id" not in existing:
        conn.execute("ALTER TABLE sales_items ADD COLUMN variant_id INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_items_variant_id ON sales_items(variant_id)")
    # Add portion_id for tracking preset portions sold
    if "portion_id" not in existing:
        conn.execute("ALTER TABLE sales_items ADD COLUMN portion_id INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_items_portion_id ON sales_items(portion_id)")
    conn.commit()


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


def _seed_default_units_of_measure(conn: sqlite3.Connection) -> None:
    """Seed default units of measure if table is empty."""
    count = conn.execute("SELECT COUNT(*) FROM units_of_measure").fetchone()[0]
    if count == 0:
        default_units = [
            ("pieces", "pcs", 1, None),
            ("kilograms", "kg", 1000, "grams"),
            ("grams", "g", 1, None),
            ("liters", "L", 1000, "milliliters"),
            ("milliliters", "ml", 1, None),
            ("meters", "m", 100, "centimeters"),
            ("centimeters", "cm", 1, None),
            ("boxes", "box", 1, None),
            ("packs", "pk", 1, None),
            ("bottles", "btl", 1, None),
        ]
        conn.executemany(
            "INSERT INTO units_of_measure (name, abbreviation, conversion_factor, base_unit, is_active) VALUES (?, ?, ?, ?, 1)",
            default_units
        )
    conn.commit()


def _seed_default_inventory_categories(conn: sqlite3.Connection) -> None:
    """Seed default inventory categories if table is empty."""
    count = conn.execute("SELECT COUNT(*) FROM inventory_categories").fetchone()[0]
    if count == 0:
        default_categories = [
            "Food & Groceries",
            "Beverages",
            "Household Items",
            "Electronics",
            "Clothing & Accessories",
            "Personal Care",
            "Cleaning Supplies",
            "Office Supplies",
            "Miscellaneous",
        ]
        conn.executemany(
            "INSERT INTO inventory_categories (name) VALUES (?)",
            [(cat,) for cat in default_categories]
        )
    conn.commit()


def _seed_default_expense_categories(conn: sqlite3.Connection) -> None:
    """Seed default expense categories if table is empty."""
    count = conn.execute("SELECT COUNT(*) FROM expense_categories").fetchone()[0]
    if count == 0:
        default_categories = [
            "Rent & Utilities",
            "Salaries & Wages",
            "Supplies & Materials",
            "Marketing & Advertising",
            "Insurance",
            "Equipment & Maintenance",
            "Transportation",
            "Professional Services",
            "Miscellaneous",
        ]
        conn.executemany(
            "INSERT INTO expense_categories (name) VALUES (?)",
            [(cat,) for cat in default_categories]
        )
    conn.commit()


import logging

_logger = logging.getLogger(__name__)

def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled and connection caching.

    Uses thread-local storage to cache connections and improve performance.
    """
    global DB_PATH
    resolved = Path(db_path) if db_path else DB_PATH
    resolved = Path(resolved)

    # Check if we have a cached connection for this thread
    cache_key = str(resolved.resolve())
    if hasattr(_local, 'connections') and cache_key in _local.connections:
        conn = _local.connections[cache_key]
        # Verify connection is still valid
        try:
            conn.execute("SELECT 1")
            return conn
        except sqlite3.Error:
            # Connection is stale, remove from cache
            del _local.connections[cache_key]

    # If the resolved path exists but appears to be an empty or stale DB, prefer
    # an initialized `pos_*.db` candidate (created by installer or first run).
    db_dir = Path(__file__).parent
    def _table_count(path: Path) -> int:
        try:
            with sqlite3.connect(path) as _conn:
                cur = _conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                return cur.fetchone()[0] or 0
        except Exception:
            return 0

    current_tables = _table_count(resolved) if resolved.exists() else 0
    if (not resolved.exists()) or (current_tables < 3):
        candidates = [p for p in db_dir.glob("pos_*.db") if p != resolved]
        # Prefer the candidate with the most tables (i.e., fully initialized)
        best = None
        best_count = current_tables
        for cand in candidates:
            cnt = _table_count(cand)
            if cnt > best_count:
                best = cand
                best_count = cnt
        if best:
            resolved = best
            DB_PATH = resolved.resolve()

    _logger.debug("Connecting to database at: %s", resolved.resolve())
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")  # Enable WAL mode for better concurrency
    conn.execute("PRAGMA synchronous = NORMAL;")  # Balance performance and safety

    # Cache the connection
    if not hasattr(_local, 'connections'):
        _local.connections = {}
    _local.connections[cache_key] = conn

    return conn


def get_default_db_path() -> Path:
    """Return the current default database path, finding the actual DB file if needed."""
    global DB_PATH
    resolved = DB_PATH

    # If the resolved path doesn't exist or appears stale, look for initialized pos_*.db files
    db_dir = Path(__file__).parent
    def _table_count(path: Path) -> int:
        try:
            with sqlite3.connect(path) as _conn:
                cur = _conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                return cur.fetchone()[0] or 0
        except Exception:
            return 0

    current_tables = _table_count(resolved) if resolved.exists() else 0
    if (not resolved.exists()) or (current_tables < 3):
        candidates = [p for p in db_dir.glob("pos_*.db") if p != resolved]
        # Prefer the candidate with the most tables (i.e., fully initialized)
        best = None
        best_count = current_tables
        for cand in candidates:
            cnt = _table_count(cand)
            if cnt > best_count:
                best = cand
                best_count = cnt
        if best:
            resolved = best

    return resolved


def validate_database_setup(db_path: Path | None = None) -> None:
    """
    Validate that the database is properly initialized with all required tables and data.
    
    Raises RuntimeError if the database is not properly set up.
    """
    try:
        with get_connection(db_path) as conn:
            # Check for required tables
            required_tables = [
                'users', 'items', 'sales', 'sales_items', 'refunds', 'refunds_items',
                'expenses', 'vat_rates', 'units_of_measure', 'inventory_categories',
                'expense_categories', 'item_variants', 'item_portions', 'settings'
            ]
            
            existing_tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            if missing_tables:
                raise RuntimeError(f"Database missing required tables: {', '.join(missing_tables)}")
            
            # Check for required data
            # Check if VAT rates are seeded
            vat_count = conn.execute("SELECT COUNT(*) FROM vat_rates").fetchone()[0]
            if vat_count == 0:
                raise RuntimeError("Database missing VAT rates data")
            
            # Check if units of measure are seeded
            uom_count = conn.execute("SELECT COUNT(*) FROM units_of_measure").fetchone()[0]
            if uom_count == 0:
                raise RuntimeError("Database missing units of measure data")
            
            # Check if inventory categories are seeded
            inv_cat_count = conn.execute("SELECT COUNT(*) FROM inventory_categories").fetchone()[0]
            if inv_cat_count == 0:
                raise RuntimeError("Database missing inventory categories data")
            
            # Check if expense categories are seeded
            exp_cat_count = conn.execute("SELECT COUNT(*) FROM expense_categories").fetchone()[0]
            if exp_cat_count == 0:
                raise RuntimeError("Database missing expense categories data")
            
    except sqlite3.Error as e:
        raise RuntimeError(f"Database validation failed: {e}")


def initialize_database(db_path: Path | None = None) -> Path:
    """Create required tables if they are missing and return the database path.

    This function also updates the module-level DB_PATH so callers that use
    get_connection() without an explicit path will connect to the initialized
    database (important when running as a bundled EXE).
    """
    global DB_PATH
    resolved = Path(db_path) if db_path else DB_PATH
    # Ensure DB_PATH references the initialized database for subsequent calls (use absolute path)
    DB_PATH = resolved.resolve()
    with get_connection(resolved) as conn:
        _logger.info("Executing SCHEMA script")
        conn.executescript(SCHEMA)
        _logger.info("SCHEMA executed, running migrations")
        _ensure_user_columns(conn)
        _ensure_item_columns(conn)
        _ensure_expense_columns(conn)
        _ensure_sales_columns(conn)
        _ensure_sales_items_columns(conn)
        _ensure_refunds_table(conn)
        _ensure_inventory_categories_table(conn)
        _ensure_expense_categories_table(conn)
        _ensure_units_of_measure_table(conn)
        _ensure_item_variants_table(conn)
        _ensure_item_portions_table(conn)
        _seed_default_vat_rates(conn)
        _seed_default_units_of_measure(conn)
        _seed_default_inventory_categories(conn)
        _seed_default_expense_categories(conn)
        _logger.info("Database initialized at %s", resolved.resolve())
    return resolved.resolve()


def validate_database(db_path: Path | None = None) -> tuple[bool, str]:
    """
    Validate database health and return (is_valid, message).
    
    Returns:
        tuple: (bool, str) - (True, "OK") if valid, (False, error_message) if invalid
    """
    try:
        validate_database_setup(db_path)
        return True, "Database validation passed"
    except RuntimeError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error during validation: {e}"


if __name__ == "__main__":
    initialize_database()
