"""CSV import/export helpers for inventory."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from modules import items


def export_inventory_csv(output_path: Path | str) -> int:
    """Export all items to CSV; returns count exported."""
    rows = items.list_items()
    output_path = Path(output_path)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "category", "cost_price", "selling_price", "quantity", "barcode"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "name": row["name"],
                    "category": row.get("category", ""),
                    "cost_price": row["cost_price"],
                    "selling_price": row["selling_price"],
                    "quantity": row["quantity"],
                    "barcode": row.get("barcode", ""),
                }
            )
    return len(rows)


def import_inventory_csv(input_path: Path | str, skip_duplicates: bool = True) -> int:
    """Import items from CSV; returns count imported. Skips duplicates by name if skip_duplicates=True."""
    input_path = Path(input_path)
    count = 0
    existing_names = {i["name"] for i in items.list_items()} if skip_duplicates else set()

    with open(input_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if not name or (skip_duplicates and name in existing_names):
                continue
            try:
                items.create_item(
                    name=name,
                    category=row.get("category", "").strip() or None,
                    cost_price=float(row.get("cost_price", 0) or 0),
                    selling_price=float(row.get("selling_price", 0) or 0),
                    quantity=int(row.get("quantity", 0) or 0),
                    barcode=row.get("barcode", "").strip() or None,
                )
                count += 1
                existing_names.add(name)
            except (ValueError, Exception):
                pass  # skip invalid rows
    return count
