"""Simple script tests for variant-aware low-stock alerts."""
import sys
sys.path.append('.')
from database.init_db import initialize_database, get_connection
from modules import items, variants, dashboard

# Initialize DB (idempotent)
initialize_database()

# Clean test data to be deterministic
conn = get_connection()
cur = conn.cursor()
cur.execute("DELETE FROM item_variants")
cur.execute("DELETE FROM items")
conn.commit()

# Create an item with two variants
item = items.create_item(name="Test Product", category="Test", selling_price=10.0, cost_price=5.0, quantity=0, low_stock_threshold=10, unit_of_measure="pieces")
item_id = item["item_id"]

# Variant A: quantity below threshold
v1_id = variants.create_variant(item_id, "Small", 9.0, 4.0, quantity=2, low_stock_threshold=5)
# Variant B: quantity above threshold
v2_id = variants.create_variant(item_id, "Large", 11.0, 5.0, quantity=10, low_stock_threshold=5)

print("Created item and two variants")

# Case 1: only one variant low -> expect 1 variant alert, no parent alert
alerts = dashboard.get_low_stock_items(threshold=5)
print("Alerts (case 1):")
for a in alerts:
    print(a)

variant_alerts = [a for a in alerts if a.get("type") == "variant"]
parent_alerts = [a for a in alerts if a.get("type") == "parent"]

assert len(variant_alerts) == 1, "Expected 1 variant alert"
assert len(parent_alerts) == 0, "Expected no parent alert"

print("Case 1 assertions passed")

# Case 2: make second variant low as well -> expect 2 variant alerts and NO parent alert (variant-only mode)
variants.update_variant(v2_id, quantity=1)

alerts = dashboard.get_low_stock_items(threshold=5)
print("Alerts (case 2):")
for a in alerts:
    print(a)

variant_alerts = [a for a in alerts if a.get("type") == "variant"]
parent_alerts = [a for a in alerts if a.get("type") == "parent"]

assert len(variant_alerts) == 2, f"Expected 2 variant alerts, got {len(variant_alerts)}"
assert len(parent_alerts) == 0, f"Expected no parent alert for variant-managed item, got {len(parent_alerts)}"

print("Case 2 assertions passed")

print("All low-stock variant tests passed")
