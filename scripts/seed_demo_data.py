"""
Seed script for the Kiosk POS demo environment.

Creates realistic sample data: users, categories, inventory items,
60 days of sales history, expenses, VAT rates, and settings.

Usage (standalone):
    python scripts/seed_demo_data.py [db_path]

Called automatically by demo.py / main.py --demo on first launch.
"""
from __future__ import annotations

import sqlite3
import hashlib
import random
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def already_seeded(db_path: Path) -> bool:
    """Return True if this DB has already been seeded."""
    try:
        conn = _connect(db_path)
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'demo_seeded'"
        ).fetchone()
        conn.close()
        return row is not None and row["value"] == "1"
    except Exception:
        return False


# ── Public entry point ────────────────────────────────────────────────────────

def seed_demo_database(db_path: Path) -> None:
    """Populate db_path with demo data. Idempotent — safe to call on empty schema."""
    conn = _connect(db_path)
    rng = random.Random(42)   # fixed seed → reproducible, consistent data

    try:
        _seed_vat_rates(conn)
        _seed_settings(conn)
        _seed_users(conn)
        _seed_categories(conn)
        item_ids = _seed_items(conn)
        _seed_sales(conn, rng, item_ids)
        _seed_expenses(conn)
        _seed_reconciliation(conn)

        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('demo_seeded', '1')"
        )
        conn.commit()
        print("[demo] Database seeded successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"[demo] Seeding failed: {exc}", file=sys.stderr)
        raise
    finally:
        conn.close()


# ── Sections ──────────────────────────────────────────────────────────────────

def _seed_vat_rates(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM vat_rates")
    conn.executemany(
        "INSERT INTO vat_rates (rate, description, active) VALUES (?, ?, 1)",
        [
            (16.0, "Standard Rate (16%)"),
            (0.0,  "Zero Rated / Exempt"),
        ],
    )


def _seed_settings(conn: sqlite3.Connection) -> None:
    settings = {
        "business_name":       "Demo Convenience Store",
        "currency_symbol":     "KES",
        "tax_label":           "VAT",
        "tax_rate":            "16",
        "receipt_header":      "Demo Convenience Store\nNairobi, Kenya\nTel: +254 700 000 000",
        "receipt_footer":      "Thank you for shopping with us!\n*** DEMO ENVIRONMENT ***",
        "low_stock_threshold": "10",
        "auto_backup_enabled": "0",
        "backup_frequency":    "daily",
        "email_alerts":        "0",
    }
    for k, v in settings.items():
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v)
        )


def _seed_users(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM users")
    conn.executemany(
        "INSERT INTO users (username, password_hash, role, active) VALUES (?, ?, ?, 1)",
        [
            ("admin",     _hash("Admin1234!"),    "admin"),
            ("manager",   _hash("Manager1234!"),  "admin"),
            ("cashier1",  _hash("Cashier1234!"),  "cashier"),
            ("cashier2",  _hash("Cashier1234!"),  "cashier"),
            ("cashier3",  _hash("Cashier1234!"),  "cashier"),
        ],
    )


def _seed_categories(conn: sqlite3.Connection) -> None:
    inv_cats = [
        "Food & Beverages",
        "Snacks & Confectionery",
        "Dairy & Eggs",
        "Bakery",
        "Fresh Produce",
        "Meat & Poultry",
        "Frozen Foods",
        "Personal Care",
        "Electronics & Accessories",
        "Stationery & Office",
        "Cleaning & Household",
        "Baby Products",
        "Health & Pharmacy",
        "Clothing & Apparel",
        "Hardware & Tools",
        "Alcohol & Spirits",
        "Tobacco",
        "Cereals & Grains",
        "Condiments & Sauces",
        "Pet Supplies",
    ]
    exp_cats = [
        "Rent",
        "Utilities",
        "Salaries",
        "Restocking",
        "Repairs & Maintenance",
        "Marketing & Advertising",
        "Transport & Delivery",
        "Packaging",
        "Insurance",
        "Miscellaneous",
    ]
    conn.execute("DELETE FROM inventory_categories")
    conn.execute("DELETE FROM expense_categories")
    conn.executemany(
        "INSERT OR IGNORE INTO inventory_categories (name) VALUES (?)",
        [(c,) for c in inv_cats],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO expense_categories (name) VALUES (?)",
        [(c,) for c in exp_cats],
    )


def _seed_items(conn: sqlite3.Connection) -> list[tuple[int, float, float]]:
    """Insert demo products; return list of (item_id, selling_price, cost_price)."""
    conn.execute("DELETE FROM items")

    rows = [
        # (name, category, cost, sell, qty, vat_rate, low_thresh)

        # ── Food & Beverages ────────────────────────────────────────
        ("Coca-Cola 500ml",              "Food & Beverages",    55,    80,  200, 16.0, 20),
        ("Fanta Orange 500ml",           "Food & Beverages",    55,    80,  180, 16.0, 20),
        ("Sprite 500ml",                 "Food & Beverages",    55,    80,  160, 16.0, 20),
        ("Pepsi 500ml",                  "Food & Beverages",    55,    80,  150, 16.0, 20),
        ("Bottled Water 500ml",          "Food & Beverages",    25,    40,  300, 0.0,  30),
        ("Bottled Water 1L",             "Food & Beverages",    40,    70,  250, 0.0,  30),
        ("Orange Juice 300ml",           "Food & Beverages",    80,   130,  100, 16.0, 15),
        ("Mango Juice 300ml",            "Food & Beverages",    80,   130,   90, 16.0, 15),
        ("Energy Drink 250ml",           "Food & Beverages",   120,   200,   80, 16.0, 10),
        ("Coffee (Hot Cup)",             "Food & Beverages",    80,   150,   80, 16.0, 10),
        ("Tea (Hot Cup)",                "Food & Beverages",    50,   100,   80, 16.0, 10),
        ("Hot Chocolate Cup",            "Food & Beverages",    90,   160,   50, 16.0,  8),

        # ── Snacks & Confectionery ──────────────────────────────────
        ("Pringles Original 165g",       "Snacks & Confectionery", 250, 380,  80, 16.0,  8),
        ("Lays Classic Crisps 100g",     "Snacks & Confectionery", 140, 210, 100, 16.0, 10),
        ("Doritos Nacho 120g",           "Snacks & Confectionery", 160, 240,  90, 16.0, 10),
        ("Dairy Milk Chocolate 90g",     "Snacks & Confectionery", 130, 200,  80, 16.0, 10),
        ("Kit Kat 4-finger",             "Snacks & Confectionery",  90, 150, 120, 16.0, 15),
        ("Orbit Chewing Gum",            "Snacks & Confectionery",  30,  50, 200, 16.0, 25),
        ("Digestive Biscuits 400g",      "Snacks & Confectionery",  80, 130,  70, 16.0, 10),
        ("Peanuts 200g (roasted)",       "Snacks & Confectionery",  70, 110, 120, 16.0, 15),
        ("Popcorn 100g (salted)",        "Snacks & Confectionery",  50,  90,  90, 16.0, 15),
        ("Nut & Raisin Mix 150g",        "Snacks & Confectionery", 130, 200,  60, 16.0,  8),

        # ── Dairy & Eggs ────────────────────────────────────────────
        ("Fresh Milk 500ml",             "Dairy & Eggs",        60,   95,  120, 0.0,  20),
        ("Fresh Milk 1L",                "Dairy & Eggs",       110,  170,   90, 0.0,  15),
        ("Long-life Milk 500ml",         "Dairy & Eggs",        75,  110,  100, 0.0,  15),
        ("Yoghurt Strawberry 150g",      "Dairy & Eggs",        80,  130,   80, 16.0, 10),
        ("Yoghurt Natural 500g",         "Dairy & Eggs",       120,  190,   60, 16.0,  8),
        ("Butter 250g",                  "Dairy & Eggs",       200,  290,   50, 16.0,  8),
        ("Cheese Slices x10",            "Dairy & Eggs",       280,  420,   40, 16.0,  8),
        ("Eggs (Tray of 30)",            "Dairy & Eggs",       380,  550,   50, 0.0,  10),
        ("Eggs (6-pack)",                "Dairy & Eggs",        90,  130,   80, 0.0,  15),
        ("Sour Cream 200g",              "Dairy & Eggs",       130,  200,   40, 16.0,  5),

        # ── Bakery ─────────────────────────────────────────────────
        ("White Bread Loaf",             "Bakery",              70,  110,  100, 0.0,  15),
        ("Brown Bread Loaf",             "Bakery",              80,  120,   80, 0.0,  15),
        ("Croissant (each)",             "Bakery",              60,  100,   60, 16.0, 10),
        ("Doughnut Plain (each)",        "Bakery",              50,   80,   80, 16.0, 10),
        ("Mandazi (pack of 6)",          "Bakery",              60,  100,  100, 0.0,  15),
        ("Chapati (each)",               "Bakery",              30,   50,  150, 0.0,  20),
        ("Muffin Chocolate (each)",      "Bakery",              90,  150,   50, 16.0,  8),

        # ── Fresh Produce ───────────────────────────────────────────
        ("Bananas (bunch ~1.2kg)",       "Fresh Produce",       60,  100,   80, 0.0,  10),
        ("Tomatoes 500g",                "Fresh Produce",       80,  120,   80, 0.0,  10),
        ("Onions 1kg",                   "Fresh Produce",       70,  110,   70, 0.0,  10),
        ("Capsicum (each)",              "Fresh Produce",       30,   50,  100, 0.0,  15),
        ("Avocado (each)",               "Fresh Produce",       50,   80,  100, 0.0,  15),
        ("Passion Fruit x5",             "Fresh Produce",       80,  130,   60, 0.0,  10),
        ("Spinach Bunch",                "Fresh Produce",       40,   70,   80, 0.0,  15),
        ("Carrots 500g",                 "Fresh Produce",       60,  100,   70, 0.0,  10),

        # ── Personal Care ───────────────────────────────────────────
        ("Hand Sanitizer 200ml",         "Personal Care",      130,  200,   80, 16.0, 10),
        ("Soap Bar (each)",              "Personal Care",       50,   80,  150, 16.0, 20),
        ("Toothpaste 100ml",             "Personal Care",      120,  190,   70, 16.0, 10),
        ("Toothbrush (each)",            "Personal Care",       60,  100,  100, 16.0, 15),
        ("Shampoo 200ml",                "Personal Care",      220,  350,   50, 16.0,  8),
        ("Deodorant Roll-on 50ml",       "Personal Care",      280,  420,   40, 16.0,  8),
        ("Sanitary Pads (pack of 8)",    "Personal Care",      150,  230,   60, 0.0,  10),
        ("Body Lotion 250ml",            "Personal Care",      250,  379,   50, 16.0,  8),
        ("Razor 5-pack",                 "Personal Care",      120,  190,   60, 16.0,  8),
        ("Cotton Buds 100-pack",         "Personal Care",       70,  110,   80, 16.0, 10),

        # ── Electronics & Accessories ───────────────────────────────
        ("Phone Charger Cable 1m (USB-C)","Electronics & Accessories", 300, 500,  50, 16.0, 5),
        ("Phone Charger Cable 1m (Lightning)","Electronics & Accessories", 300, 500, 40, 16.0, 5),
        ("Earphones Basic",              "Electronics & Accessories", 500, 800,  30, 16.0, 5),
        ("Power Bank 10000mAh",          "Electronics & Accessories",1800,2500,  15, 16.0, 3),
        ("USB Flash Drive 16GB",         "Electronics & Accessories", 400, 650,  30, 16.0, 5),
        ("USB Flash Drive 32GB",         "Electronics & Accessories", 600, 950,  25, 16.0, 5),
        ("Screen Protector (Universal)", "Electronics & Accessories", 150, 280,  50, 16.0, 8),
        ("Phone Case (Generic)",         "Electronics & Accessories", 200, 380,  40, 16.0, 5),
        ("AA Batteries 4-pack",          "Electronics & Accessories", 100, 180, 100, 16.0,15),
        ("AAA Batteries 4-pack",         "Electronics & Accessories", 100, 180,  80, 16.0,15),
        ("Torch (LED)",                  "Electronics & Accessories", 250, 400,  30, 16.0, 5),
        ("Extension Cable 3-way",        "Electronics & Accessories", 500, 800,  25, 16.0, 5),

        # ── Stationery & Office ─────────────────────────────────────
        ("Bic Ballpoint Pen Blue",       "Stationery & Office",  20,  35, 300, 16.0, 50),
        ("Bic Ballpoint Pen Black",      "Stationery & Office",  20,  35, 250, 16.0, 50),
        ("Pencil HB (each)",             "Stationery & Office",  15,  25, 200, 16.0, 30),
        ("Notebook A5 (100 pages)",      "Stationery & Office",  70, 120,  80, 16.0, 10),
        ("Notebook A4 (200 pages)",      "Stationery & Office", 120, 200,  60, 16.0, 10),
        ("Stapler",                      "Stationery & Office", 250, 390,  20, 16.0,  5),
        ("Staples (box of 1000)",        "Stationery & Office",  60, 100,  50, 16.0,  8),
        ("Scotch Tape 12mm",             "Stationery & Office",  50,  90,  80, 16.0, 10),
        ("A4 Paper Ream (500 sheets)",   "Stationery & Office", 500, 750,  40, 16.0,  5),
        ("Correction Fluid",             "Stationery & Office",  60,  100, 60, 16.0, 10),
        ("Highlighter Pen (Yellow)",     "Stationery & Office",  50,  80,  80, 16.0, 10),
        ("Envelope A5 (pack of 10)",     "Stationery & Office",  60, 100,  50, 16.0,  8),

        # ── Cleaning & Household ────────────────────────────────────
        ("Tissue Box (200 sheets)",      "Cleaning & Household",170, 260,  80, 16.0, 10),
        ("Pocket Tissues x5",            "Cleaning & Household", 80, 130, 120, 16.0, 15),
        ("Dishwashing Liquid 500ml",     "Cleaning & Household",100, 170,  70, 16.0, 10),
        ("Disinfectant Spray 500ml",     "Cleaning & Household",300, 480,  50, 16.0,  8),
        ("Bleach 1L",                    "Cleaning & Household",120, 200,  60, 16.0, 10),
        ("Laundry Powder 500g",          "Cleaning & Household",200, 320,  60, 16.0,  8),
        ("Garbage Bags Roll (10-pack)",  "Cleaning & Household",150, 230,  70, 16.0, 10),
        ("Kitchen Roll (2-pack)",        "Cleaning & Household",200, 320,  60, 16.0,  8),
        ("Floor Cleaner 1L",             "Cleaning & Household",200, 330,  50, 16.0,  8),
        ("Sponge Scrubber (3-pack)",     "Cleaning & Household", 80, 130,  80, 16.0, 10),

        # ── Cereals & Grains ───────────────────────────────────────
        ("Rice 1kg",                     "Cereals & Grains",    100, 160, 150, 0.0,  20),
        ("Rice 2kg",                     "Cereals & Grains",    195, 310, 100, 0.0,  15),
        ("Wheat Flour 1kg",              "Cereals & Grains",     80, 130, 120, 0.0,  20),
        ("Maize Flour 2kg",              "Cereals & Grains",    130, 210, 100, 0.0,  15),
        ("Oats 400g",                    "Cereals & Grains",    130, 210,  70, 16.0, 10),
        ("Spaghetti 500g",               "Cereals & Grains",     90, 150,  80, 16.0, 10),
        ("Cornflakes 375g",              "Cereals & Grains",    220, 350,  60, 16.0,  8),
        ("Sugar 1kg",                    "Cereals & Grains",    120, 190, 150, 0.0,  20),

        # ── Condiments & Sauces ────────────────────────────────────
        ("Tomato Ketchup 500ml",         "Condiments & Sauces", 150, 240,  60, 16.0,  8),
        ("Mayonnaise 200ml",             "Condiments & Sauces", 130, 210,  50, 16.0,  8),
        ("Chilli Sauce 100ml",           "Condiments & Sauces",  80, 130,  60, 16.0, 10),
        ("Soy Sauce 150ml",              "Condiments & Sauces", 100, 160,  50, 16.0,  8),
        ("Cooking Oil 500ml",            "Condiments & Sauces", 200, 310,  80, 0.0,  10),
        ("Salt 500g",                    "Condiments & Sauces",  40,  70, 100, 0.0,  15),
        ("Pepper Powder 50g",            "Condiments & Sauces",  50,  90,  80, 16.0, 10),

        # ── Health & Pharmacy ──────────────────────────────────────
        ("Paracetamol 500mg (strip x10)","Health & Pharmacy",    30,  50, 200, 0.0,  30),
        ("Vitamin C Tablets x20",        "Health & Pharmacy",   130, 210,  80, 0.0,  10),
        ("Antacid Tablets x10",          "Health & Pharmacy",    60, 100,  80, 0.0,  10),
        ("Plasters (box of 10)",         "Health & Pharmacy",    60,  100, 80, 0.0,  10),
        ("Cough Syrup 100ml",            "Health & Pharmacy",   180, 290,  50, 0.0,   8),
        ("Condoms (3-pack)",             "Health & Pharmacy",   130, 220,  80, 0.0,  10),

        # ── Alcohol & Spirits ──────────────────────────────────────
        ("Beer (Bottle 500ml)",          "Alcohol & Spirits",   120, 200,  80, 16.0, 10),
        ("Beer (Can 330ml)",             "Alcohol & Spirits",    90, 150, 100, 16.0, 10),
        ("Wine Red (Glass 150ml)",       "Alcohol & Spirits",   200, 350,  40, 16.0,  5),
        ("Whisky 200ml (miniature)",     "Alcohol & Spirits",   350, 600,  30, 16.0,  5),
        ("Vodka 200ml (miniature)",      "Alcohol & Spirits",   300, 520,  30, 16.0,  5),
        ("Gin 200ml (miniature)",        "Alcohol & Spirits",   320, 550,  25, 16.0,  5),
    ]

    result: list[tuple[int, float, float]] = []
    for (name, cat, cost, sell, qty, vat, thresh) in rows:
        cur = conn.execute(
            """INSERT INTO items
               (name, category, cost_price, selling_price, quantity,
                vat_rate, low_stock_threshold)
               VALUES (?,?,?,?,?,?,?)""",
            (name, cat, float(cost), float(sell), qty, vat, thresh),
        )
        result.append((cur.lastrowid, float(sell), float(cost)))

    return result


def _seed_sales(
    conn: sqlite3.Connection,
    rng: random.Random,
    item_ids: list[tuple[int, float, float]],
) -> None:
    """Create 60 days of randomised sales (8–30 per day depending on weekday/weekend)."""
    conn.execute("DELETE FROM sales_items")
    conn.execute("DELETE FROM sales")

    today = date.today()
    start = today - timedelta(days=89)

    # Detect extra columns added by migrations
    sales_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(sales)").fetchall()
    }

    for day_offset in range(90):
        current_date = start + timedelta(days=day_offset)
        is_weekend = current_date.weekday() >= 5
        num_sales = rng.randint(15, 30) if is_weekend else rng.randint(8, 20)

        for _ in range(num_sales):
            hour   = rng.randint(8, 20)
            minute = rng.randint(0, 59)
            sale_time = f"{hour:02d}:{minute:02d}:00"

            chosen = rng.sample(item_ids, k=rng.randint(1, 5))
            total = 0.0
            line_items = []
            for (iid, sell, cost) in chosen:
                qty = rng.randint(1, 3)
                total += round(sell * qty, 2)
                line_items.append((iid, qty, sell, cost))

            total = round(total, 2)
            payment = (int(total / 50) + 1) * 50 if total % 50 != 0 else total
            change  = round(payment - total, 2)

            if "customer_id" in sales_cols and "voided" in sales_cols:
                cur = conn.execute(
                    """INSERT INTO sales
                       (date, time, total, payment, change, customer_id, voided)
                       VALUES (?,?,?,?,?,NULL,0)""",
                    (str(current_date), sale_time, total, payment, change),
                )
            else:
                cur = conn.execute(
                    "INSERT INTO sales (date, time, total, payment, change) VALUES (?,?,?,?,?)",
                    (str(current_date), sale_time, total, payment, change),
                )
            sid = cur.lastrowid

            conn.executemany(
                """INSERT INTO sales_items
                   (sale_id, item_id, quantity, price, cost_price)
                   VALUES (?,?,?,?,?)""",
                [(sid, iid, qty, sell, cost) for (iid, qty, sell, cost) in line_items],
            )


def _seed_expenses(conn: sqlite3.Connection) -> None:
    """3 months of realistic business expenses."""
    conn.execute("DELETE FROM expenses")

    today  = date.today()
    uid_row = conn.execute(
        "SELECT user_id FROM users WHERE username = 'admin'"
    ).fetchone()
    uid = uid_row["user_id"] if uid_row else None

    monthly = [
            ("Rent",                    "Shop Rent — Monthly",                        28000),
            ("Utilities",               "Electricity Bill",                           4500),
            ("Utilities",               "Water Bill",                                 1000),
            ("Utilities",               "Internet & WiFi",                            3500),
            ("Utilities",               "Generator Fuel",                             2000),
            ("Salaries",                "Cashier 1 Salary",                          25000),
            ("Salaries",                "Cashier 2 Salary",                          25000),
            ("Salaries",                "Cashier 3 Salary",                          25000),
            ("Salaries",                "Cleaner Salary (part-time)",                 8000),
            ("Insurance",               "Shop Insurance Premium",                     4000),
            ("Marketing & Advertising", "Monthly Social Media Ads",                   3000),
    ]

    for months_back in range(3):
        exp_date = (
            today.replace(day=1) - timedelta(days=months_back * 28)
        ).replace(day=1)
        for (cat, desc, amount) in monthly:
            conn.execute(
                """INSERT INTO expenses
                   (date, category, description, amount, user_id, username)
                   VALUES (?,?,?,?,?,?)""",
                (str(exp_date), cat, desc, amount, uid, "admin"),
            )

    rng = random.Random(99)
    for weeks_back in range(13):
        restock_date = today - timedelta(weeks=weeks_back)
        conn.execute(
            """INSERT INTO expenses
               (date, category, description, amount, user_id, username)
               VALUES (?,?,?,?,?,?)""",
            (
                str(restock_date), "Restocking",
                "Weekly stock replenishment",
                rng.randint(25000, 60000), uid, "admin",
            ),
        )

    adhoc = [
        (10, "Repairs & Maintenance",   "POS Printer Repair",             3500),
        (18, "Packaging",               "Paper Bags & Carrier Bags (x500)",2800),
        (25, "Marketing & Advertising", "Printed Flyers — 200 pcs",        4000),
        (33, "Repairs & Maintenance",   "Air Conditioner Service",         6000),
        (40, "Packaging",               "Thermal Receipt Paper Roll x20",  3500),
        (47, "Transport & Delivery",    "Stock Delivery Charges",          2500),
        (55, "Repairs & Maintenance",   "Refrigerator Servicing",          5000),
        (62, "Miscellaneous",           "Stationery & Office Supplies",    1500),
        (70, "Transport & Delivery",    "Emergency Stock Run",             1800),
        (78, "Miscellaneous",           "Staff Refreshments — Monthly",     900),
        (85, "Marketing & Advertising", "Loyalty Card Printing",           3200),
    ]
    for (days_back, cat, desc, amount) in adhoc:
        conn.execute(
            """INSERT INTO expenses
               (date, category, description, amount, user_id, username)
               VALUES (?,?,?,?,?,?)""",
            (str(today - timedelta(days=days_back)), cat, desc, amount, uid, "admin"),
        )


def _seed_reconciliation(conn: sqlite3.Connection) -> None:
    """Four completed weekly reconciliation sessions."""
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "reconciliation_sessions" not in tables:
        return

    conn.execute("DELETE FROM reconciliation_entries")
    conn.execute("DELETE FROM reconciliation_sessions")

    uid_row = conn.execute(
        "SELECT user_id FROM users WHERE username = 'admin'"
    ).fetchone()
    uid = uid_row["user_id"] if uid_row else None
    today = date.today()
    rng   = random.Random(77)

    for weeks_back in range(1, 9):
        period_end   = today - timedelta(weeks=weeks_back)
        period_start = period_end - timedelta(days=6)
        sys_sales    = round(rng.uniform(45000, 80000), 2)
        variance     = round(rng.uniform(-500, 500), 2)
        actual_cash  = round(sys_sales + variance, 2)

        cur = conn.execute(
            """INSERT INTO reconciliation_sessions
               (reconciliation_date, period_type, start_date, end_date,
                total_system_sales, total_actual_cash, total_variance,
                status, reconciled_by, reconciled_at, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(period_end), "weekly",
                str(period_start), str(period_end),
                sys_sales, actual_cash, variance,
                "completed", uid,
                datetime.now().isoformat(timespec="seconds"),
                "Weekly reconciliation — DEMO",
            ),
        )
        sid = cur.lastrowid

        for (method, share) in [("Cash", 0.65), ("M-Pesa", 0.30), ("Card", 0.05)]:
            sa = round(sys_sales * share, 2)
            vp = round(variance  * share, 2)
            conn.execute(
                """INSERT INTO reconciliation_entries
                   (session_id, payment_method, system_amount, actual_amount,
                    variance, reviewed)
                   VALUES (?,?,?,?,?,1)""",
                (sid, method, sa, round(sa + vp, 2), vp),
            )


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(app_dir))

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else app_dir / "database" / "demo.db"
    target.parent.mkdir(parents=True, exist_ok=True)

    import database.init_db as _idb
    _idb.DB_PATH = target
    _idb.initialize_database(target)

    from database.migrations import run_pending_migrations
    run_pending_migrations()

    if already_seeded(target):
        print(f"[demo] Already seeded: {target}")
    else:
        seed_demo_database(target)
        print(f"[demo] Done → {target}")