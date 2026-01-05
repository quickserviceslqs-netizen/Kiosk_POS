"""SQLite schema initialization for the Kiosk POS app."""
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).parent / "pos.db"

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


def _ensure_expense_columns(conn: sqlite3.Connection) -> None:
    """Add user tracking columns to expenses table if missing."""
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(expenses);")}
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
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(refunds);")}

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
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(users);")}
    if "password_salt" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_salt TEXT;")


def _ensure_item_columns(conn: sqlite3.Connection) -> None:
    """Apply lightweight migrations for the items table (idempotent)."""
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(items);")}
    
    # Add low_stock_threshold if missing
    if "low_stock_threshold" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN low_stock_threshold INTEGER NOT NULL DEFAULT 10")

    # Add currency_code if missing
    if "currency_code" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN currency_code TEXT DEFAULT NULL")

    # Add fractional/volume support columns
    if "is_special_volume" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN is_special_volume INTEGER NOT NULL DEFAULT 0")
    if "unit_size_ml" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN unit_size_ml INTEGER NOT NULL DEFAULT 1")
        # Migrate legacy records: if an older DB used the previous default (1000)
        # and the item is measured in 'pieces' (non-volume), reset to 1.
        try:
            conn.execute("UPDATE items SET unit_size_ml = 1 WHERE unit_of_measure = 'pieces' AND unit_size_ml = 1000")
        except Exception:
            # If update fails (e.g., no such rows), continue silently
            pass
    if "unit_multiplier" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN unit_multiplier REAL NOT NULL DEFAULT 1.0")
    if "unit_of_measure" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN unit_of_measure TEXT DEFAULT 'pieces'")

    # Add per-unit price/cost columns used by POS calculations
    if "price_per_ml" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN price_per_ml REAL DEFAULT NULL")
    if "cost_price_per_unit" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN cost_price_per_unit REAL DEFAULT NULL")
    if "selling_price_per_unit" not in existing_columns:
        conn.execute("ALTER TABLE items ADD COLUMN selling_price_per_unit REAL DEFAULT NULL")

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
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(units_of_measure);")}
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
    existing = {row[1] for row in conn.execute("PRAGMA table_info(sales);")}
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
    """Return a SQLite connection with foreign keys enabled.

    If no explicit path is provided, try to use the configured/initialized
    DB path. If that file does not exist, look for any previously initialized
    `pos_*.db` file in the database folder and adopt it to avoid connecting to
    a fresh `pos.db` when an initialized DB already exists.
    """
    global DB_PATH
    resolved = Path(db_path) if db_path else DB_PATH
    resolved = Path(resolved)

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


if __name__ == "__main__":
    initialize_database()
