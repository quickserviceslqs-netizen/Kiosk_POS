"""Stock Receiving Module for managing inventory purchases.

This module provides functions for receiving new stock into inventory,
creating stock lots with proper cost tracking, and managing suppliers.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import sqlite3
import logging

from database.init_db import get_connection
from modules.inventory_costing import (
    create_stock_lot, StockLot, get_stock_lots, 
    MovementType, migrate_existing_inventory_to_lots
)

logger = logging.getLogger(__name__)


@dataclass
class StockReceipt:
    """Represents a stock receipt/purchase order."""
    receipt_id: Optional[int] = None
    receipt_number: str = ""
    supplier: Optional[str] = None
    receipt_date: str = ""
    total_amount: float = 0.0
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[str] = None
    items: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []


def generate_receipt_number() -> str:
    """Generate a unique receipt number for stock purchases."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"SR-{timestamp}"


def receive_stock(
    item_id: int,
    quantity: int,
    cost_price: float,
    supplier: Optional[str] = None,
    reference_number: Optional[str] = None,
    expiry_date: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[int] = None,
    variant_id: Optional[int] = None,
    purchase_date: Optional[str] = None
) -> StockLot:
    """Receive stock for an item, creating a new stock lot.
    
    This is the primary function for adding inventory with proper
    cost tracking and lot management.
    
    Args:
        item_id: ID of the item to receive stock for
        quantity: Quantity received
        cost_price: Cost price per unit
        supplier: Supplier name
        reference_number: Invoice/PO number
        expiry_date: Expiry date for perishables (YYYY-MM-DD format)
        notes: Additional notes
        user_id: User receiving the stock
        variant_id: Optional variant ID if receiving for a specific variant
        purchase_date: Purchase date (defaults to today)
        
    Returns:
        Created StockLot object
        
    Raises:
        ValueError: If item doesn't exist or invalid parameters
    """
    # Validate item exists
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        item = conn.execute(
            "SELECT item_id, name FROM items WHERE item_id = ?",
            (item_id,)
        ).fetchone()
        
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")
        
        # Validate variant if specified
        if variant_id:
            variant = conn.execute(
                "SELECT variant_id FROM item_variants WHERE variant_id = ? AND item_id = ?",
                (variant_id, item_id)
            ).fetchone()
            if not variant:
                raise ValueError(f"Variant {variant_id} not found for item {item_id}")
    
    # Validate inputs
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if cost_price < 0:
        raise ValueError("Cost price cannot be negative")
    
    # Create the stock lot
    lot = create_stock_lot(
        item_id=item_id,
        quantity=quantity,
        cost_price=cost_price,
        purchase_date=purchase_date,
        variant_id=variant_id,
        supplier=supplier,
        reference_number=reference_number,
        expiry_date=expiry_date,
        notes=notes,
        user_id=user_id
    )
    
    logger.info(
        f"Stock received: {quantity} units of item {item_id} @ {cost_price} each "
        f"(Lot ID: {lot.lot_id}, Reference: {reference_number or 'N/A'})"
    )
    
    return lot


def receive_stock_batch(
    items: List[Dict[str, Any]],
    supplier: Optional[str] = None,
    reference_number: Optional[str] = None,
    user_id: Optional[int] = None,
    purchase_date: Optional[str] = None
) -> List[StockLot]:
    """Receive multiple items in a single batch.
    
    Args:
        items: List of dicts with keys:
            - item_id (required)
            - quantity (required)
            - cost_price (required)
            - variant_id (optional)
            - expiry_date (optional)
            - notes (optional)
        supplier: Supplier for all items
        reference_number: Reference number for the batch
        user_id: User receiving the stock
        purchase_date: Purchase date (defaults to today)
        
    Returns:
        List of created StockLot objects
    """
    lots = []

    for idx, item in enumerate(items):
        try:
            lot = receive_stock(
                item_id=item["item_id"],
                quantity=item["quantity"],
                cost_price=item["cost_price"],
                supplier=supplier,
                reference_number=reference_number,
                expiry_date=item.get("expiry_date"),
                notes=item.get("notes"),
                user_id=user_id,
                variant_id=item.get("variant_id"),
                purchase_date=purchase_date
            )
            lots.append(lot)
        except Exception as e:
            logger.error(f"Failed to receive item {item.get('item_id')} at index {idx}: {e}")
            raise ValueError(
                f"Batch receiving failed at item index {idx} "
                f"(item_id={item.get('item_id')}): {e}. "
                f"{len(lots)} prior item(s) were already committed."
            ) from e

    return lots


def get_recent_purchases(
    item_id: Optional[int] = None,
    days: int = 30,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get recent stock purchases/receipts.
    
    Args:
        item_id: Optional filter by item
        days: Number of days to look back
        limit: Maximum number of records
        
    Returns:
        List of purchase records with item details
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT 
                sl.lot_id,
                sl.item_id,
                i.name as item_name,
                i.category,
                sl.variant_id,
                iv.variant_name,
                sl.purchase_date,
                sl.quantity_received,
                sl.quantity_remaining,
                sl.cost_price,
                sl.quantity_received * sl.cost_price as total_cost,
                sl.supplier,
                sl.reference_number,
                sl.expiry_date,
                sl.notes,
                sl.created_at
            FROM stock_lots sl
            JOIN items i ON sl.item_id = i.item_id
            LEFT JOIN item_variants iv ON sl.variant_id = iv.variant_id
            WHERE DATE(sl.purchase_date) >= DATE('now', ? || ' days')
        """
        params: List[Any] = [f"-{days}"]
        
        if item_id:
            query += " AND sl.item_id = ?"
            params.append(item_id)
        
        query += " ORDER BY sl.purchase_date DESC, sl.lot_id DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_suppliers() -> List[str]:
    """Get list of unique suppliers from stock lots."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT supplier 
            FROM stock_lots 
            WHERE supplier IS NOT NULL AND supplier != ''
            ORDER BY supplier
        """).fetchall()
        return [row[0] for row in rows]


def update_lot_details(
    lot_id: int,
    supplier: Optional[str] = None,
    reference_number: Optional[str] = None,
    expiry_date: Optional[str] = None,
    notes: Optional[str] = None
) -> bool:
    """Update editable details of a stock lot.
    
    Note: Cannot modify quantity_received or cost_price after creation.
    
    Args:
        lot_id: Lot ID to update
        supplier: New supplier name
        reference_number: New reference number
        expiry_date: New expiry date
        notes: New notes
        
    Returns:
        True if updated successfully
    """
    updates = []
    params = []
    
    if supplier is not None:
        updates.append("supplier = ?")
        params.append(supplier)
    if reference_number is not None:
        updates.append("reference_number = ?")
        params.append(reference_number)
    if expiry_date is not None:
        updates.append("expiry_date = ?")
        params.append(expiry_date)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    
    if not updates:
        return False
    
    params.append(lot_id)
    
    with get_connection() as conn:
        conn.execute(
            f"UPDATE stock_lots SET {', '.join(updates)} WHERE lot_id = ?",
            params
        )
        conn.commit()
    
    return True


def get_item_stock_summary(item_id: int) -> Dict[str, Any]:
    """Get a summary of stock lots for an item.
    
    Args:
        item_id: Item ID
        
    Returns:
        Dictionary with stock summary including:
        - total_quantity: Total stock across all lots
        - lot_count: Number of active lots
        - oldest_lot_date: Date of oldest lot with stock
        - newest_lot_date: Date of newest lot
        - average_cost: Weighted average cost
        - lowest_cost: Lowest cost among active lots
        - highest_cost: Highest cost among active lots
        - lots: List of active lots
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Get summary stats
        summary = conn.execute("""
            SELECT 
                COALESCE(SUM(quantity_remaining), 0) as total_quantity,
                COUNT(*) as lot_count,
                MIN(purchase_date) as oldest_lot_date,
                MAX(purchase_date) as newest_lot_date,
                CASE WHEN SUM(quantity_remaining) > 0 
                    THEN SUM(quantity_remaining * cost_price) / SUM(quantity_remaining)
                    ELSE 0 END as average_cost,
                MIN(cost_price) as lowest_cost,
                MAX(cost_price) as highest_cost
            FROM stock_lots
            WHERE item_id = ? AND quantity_remaining > 0
        """, (item_id,)).fetchone()
        
        # Get active lots
        lots = conn.execute("""
            SELECT 
                lot_id, purchase_date, quantity_received, quantity_remaining,
                cost_price, supplier, reference_number, expiry_date
            FROM stock_lots
            WHERE item_id = ? AND quantity_remaining > 0
            ORDER BY purchase_date ASC
        """, (item_id,)).fetchall()
        
        return {
            "total_quantity": summary["total_quantity"] or 0,
            "lot_count": summary["lot_count"] or 0,
            "oldest_lot_date": summary["oldest_lot_date"],
            "newest_lot_date": summary["newest_lot_date"],
            "average_cost": summary["average_cost"] or 0,
            "lowest_cost": summary["lowest_cost"] or 0,
            "highest_cost": summary["highest_cost"] or 0,
            "lots": [dict(lot) for lot in lots]
        }


def calculate_reorder_suggestions(
    threshold_percent: float = 25.0
) -> List[Dict[str, Any]]:
    """Calculate reorder suggestions based on stock levels.
    
    Args:
        threshold_percent: Suggest reorder when stock is at this % of threshold
        
    Returns:
        List of items needing reorder with suggested quantities and costs
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT 
                i.item_id,
                i.name,
                i.category,
                i.quantity as current_stock,
                i.low_stock_threshold,
                i.cost_price as last_cost,
                COALESCE(
                    (SELECT AVG(sl.cost_price) 
                     FROM stock_lots sl 
                     WHERE sl.item_id = i.item_id),
                    i.cost_price
                ) as average_cost,
                i.low_stock_threshold - i.quantity as shortage,
                (i.low_stock_threshold - i.quantity) * i.cost_price as estimated_reorder_cost
            FROM items i
            WHERE i.quantity <= i.low_stock_threshold * (? / 100.0)
            ORDER BY i.quantity ASC, i.name ASC
        """
        
        rows = conn.execute(query, (100 + threshold_percent,)).fetchall()
        
        suggestions = []
        for row in rows:
            suggested_qty = max(row["low_stock_threshold"] * 2 - row["current_stock"], 0)
            suggestions.append({
                "item_id": row["item_id"],
                "name": row["name"],
                "category": row["category"],
                "current_stock": row["current_stock"],
                "low_stock_threshold": row["low_stock_threshold"],
                "suggested_quantity": int(suggested_qty),
                "average_cost": row["average_cost"],
                "estimated_cost": suggested_qty * row["average_cost"]
            })
        
        return suggestions


def check_and_migrate_legacy_inventory(user_id: Optional[int] = None) -> int:
    """Check if migration is needed and run it.
    
    This function checks if there are items with quantity but no stock lots,
    indicating they need to be migrated to the new lot-based system.
    
    Args:
        user_id: User performing the migration
        
    Returns:
        Number of items migrated (0 if already done)
    """
    with get_connection() as conn:
        # Check if migration is needed
        count = conn.execute("""
            SELECT COUNT(*) FROM items i
            WHERE i.quantity > 0
              AND NOT EXISTS (SELECT 1 FROM stock_lots sl WHERE sl.item_id = i.item_id)
        """).fetchone()[0]
        
        if count == 0:
            logger.info("No legacy inventory to migrate")
            return 0
    
    # Run migration
    return migrate_existing_inventory_to_lots(user_id)
