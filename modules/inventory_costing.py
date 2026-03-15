"""Inventory Costing Module for Stock Lot Management.

This module provides FIFO, LIFO, and Weighted Average Cost (WAC) inventory
costing methods for accurate profit calculations and stock tracking.

Key Features:
- Stock lot creation and management
- Cost allocation based on selected method (FIFO/LIFO/WAC)
- Stock movement audit trail
- Inventory valuation calculations
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
import sqlite3
import logging

from database.init_db import get_connection

logger = logging.getLogger(__name__)


class CostingMethod(Enum):
    """Supported inventory costing methods."""
    FIFO = "FIFO"  # First-In, First-Out
    LIFO = "LIFO"  # Last-In, First-Out
    WAC = "WAC"    # Weighted Average Cost
    SPECIFIC = "SPECIFIC"  # Specific identification (manual selection)


class MovementType(Enum):
    """Types of stock movements."""
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
    WASTE = "waste"
    OPENING_STOCK = "opening_stock"


@dataclass
class StockLot:
    """Represents a batch of inventory received at a specific cost."""
    lot_id: Optional[int] = None
    item_id: int = 0
    variant_id: Optional[int] = None
    purchase_date: str = ""
    quantity_received: int = 0
    quantity_remaining: int = 0
    cost_price: float = 0.0
    selling_price: Optional[float] = None  # Lot-specific selling price
    supplier: Optional[str] = None
    reference_number: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class StockMovement:
    """Represents a stock movement event."""
    movement_id: Optional[int] = None
    item_id: int = 0
    variant_id: Optional[int] = None
    lot_id: Optional[int] = None
    movement_type: MovementType = MovementType.ADJUSTMENT
    quantity: int = 0
    unit_cost: Optional[float] = None
    total_cost: Optional[float] = None
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    user_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class LotAllocation:
    """Represents allocation from a stock lot for a sale."""
    lot_id: int
    quantity: int
    unit_cost: float
    
    @property
    def total_cost(self) -> float:
        return self.quantity * self.unit_cost


def get_costing_method() -> CostingMethod:
    """Get the current inventory costing method from settings."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        result = conn.execute(
            "SELECT value FROM settings WHERE key = 'inventory_costing_method'"
        ).fetchone()
        
        if result:
            method_str = result["value"]
            try:
                return CostingMethod(method_str)
            except ValueError:
                logger.warning(f"Unknown costing method '{method_str}', defaulting to FIFO")
                return CostingMethod.FIFO
        return CostingMethod.FIFO


def set_costing_method(method: CostingMethod) -> None:
    """Set the inventory costing method in settings."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            ('inventory_costing_method', method.value)
        )
        conn.commit()


# =============================================================================
# STOCK LOT MANAGEMENT
# =============================================================================

def create_stock_lot(
    item_id: int,
    quantity: int,
    cost_price: float,
    purchase_date: Optional[str] = None,
    variant_id: Optional[int] = None,
    supplier: Optional[str] = None,
    reference_number: Optional[str] = None,
    expiry_date: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[int] = None,
    selling_price: Optional[float] = None
) -> StockLot:
    """Create a new stock lot and record the purchase movement.
    
    Args:
        item_id: ID of the item
        quantity: Quantity received
        cost_price: Cost price per unit
        purchase_date: Date of purchase (defaults to today)
        variant_id: Optional variant ID
        supplier: Supplier name
        reference_number: Invoice/PO number
        expiry_date: Expiry date for perishables
        notes: Additional notes
        user_id: ID of user creating the lot
        selling_price: Optional lot-specific selling price
        
    Returns:
        Created StockLot object
    """
    if purchase_date is None:
        purchase_date = datetime.now().strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            # Create the lot
            cursor = conn.execute(
                """
                INSERT INTO stock_lots 
                (item_id, variant_id, purchase_date, quantity_received, quantity_remaining,
                 cost_price, selling_price, supplier, reference_number, expiry_date, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, variant_id, purchase_date, quantity, quantity, 
                 cost_price, selling_price, supplier, reference_number, expiry_date, notes, user_id)
            )
            lot_id = cursor.lastrowid
            
            # Record the purchase movement
            conn.execute(
                """
                INSERT INTO stock_movements
                (item_id, variant_id, lot_id, movement_type, quantity, unit_cost, total_cost,
                 reference_type, user_id, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, variant_id, lot_id, MovementType.PURCHASE.value, quantity,
                 cost_price, quantity * cost_price, 'stock_lot', user_id, 
                 f"Stock lot created: {reference_number or 'N/A'}")
            )
            
            # Update item's total quantity
            conn.execute(
                "UPDATE items SET quantity = quantity + ? WHERE item_id = ?",
                (quantity, item_id)
            )
            
            # Update variant's quantity if applicable
            if variant_id:
                conn.execute(
                    "UPDATE item_variants SET quantity = quantity + ? WHERE variant_id = ?",
                    (quantity, variant_id)
                )
            
            conn.commit()
            
            logger.info(f"Created stock lot {lot_id} for item {item_id}: {quantity} units @ {cost_price}")
            
            return StockLot(
                lot_id=lot_id,
                item_id=item_id,
                variant_id=variant_id,
                purchase_date=purchase_date,
                quantity_received=quantity,
                quantity_remaining=quantity,
                cost_price=cost_price,
                selling_price=selling_price,
                supplier=supplier,
                reference_number=reference_number,
                expiry_date=expiry_date,
                notes=notes,
                created_by=user_id
            )
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create stock lot: {e}")
            raise


def get_stock_lots(
    item_id: int,
    variant_id: Optional[int] = None,
    include_empty: bool = False
) -> List[StockLot]:
    """Get all stock lots for an item.
    
    Args:
        item_id: Item ID to get lots for
        variant_id: Optional variant ID filter
        include_empty: Include lots with zero remaining quantity
        
    Returns:
        List of StockLot objects
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT * FROM stock_lots
            WHERE item_id = ?
        """
        params: List[Any] = [item_id]
        
        if variant_id is not None:
            query += " AND variant_id = ?"
            params.append(variant_id)
        
        if not include_empty:
            query += " AND quantity_remaining > 0"
        
        query += " ORDER BY purchase_date ASC, lot_id ASC"
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            StockLot(
                lot_id=row["lot_id"],
                item_id=row["item_id"],
                variant_id=row["variant_id"],
                purchase_date=row["purchase_date"],
                quantity_received=row["quantity_received"],
                quantity_remaining=row["quantity_remaining"],
                cost_price=row["cost_price"],
                selling_price=row["selling_price"],
                supplier=row["supplier"],
                reference_number=row["reference_number"],
                expiry_date=row["expiry_date"],
                notes=row["notes"],
                created_by=row["created_by"],
                created_at=row["created_at"]
            )
            for row in rows
        ]


def get_lot_by_id(lot_id: int) -> Optional[StockLot]:
    """Get a specific stock lot by ID."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM stock_lots WHERE lot_id = ?",
            (lot_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return StockLot(
            lot_id=row["lot_id"],
            item_id=row["item_id"],
            variant_id=row["variant_id"],
            purchase_date=row["purchase_date"],
            quantity_received=row["quantity_received"],
            quantity_remaining=row["quantity_remaining"],
            cost_price=row["cost_price"],
            supplier=row["supplier"],
            reference_number=row["reference_number"],
            expiry_date=row["expiry_date"],
            notes=row["notes"],
            created_by=row["created_by"],
            created_at=row["created_at"]
        )


def get_effective_selling_price(
    item_id: int,
    variant_id: Optional[int] = None
) -> Tuple[float, float]:
    """Get the effective selling price for an item based on stock lots and costing method.
    
    The selling price is determined by:
    - Preferred Lot: If an item has a preferred lot set, always use that lot's selling price
    - FIFO: Uses the oldest lot's selling price (first lot to be sold)
    - LIFO: Uses the newest lot's selling price (last lot received)
    - WAC: Calculates weighted average selling price across all lots
    
    Args:
        item_id: Item ID to get selling price for
        variant_id: Optional variant ID
        
    Returns:
        Tuple of (effective_price, min_price, max_price) where:
        - effective_price: Price to use for sales
        - min_price: Minimum price across all lots
        - max_price: Maximum price across all lots
    """
    # Get all available stock lots for this item
    lots = get_stock_lots(item_id, variant_id=variant_id, include_empty=False)
    
    if not lots:
        # No stock lots, return 0
        return (0.0, 0.0, 0.0)
    
    # Check if there's a preferred lot set for this item
    preferred_lot_id = get_preferred_lot(item_id)
    
    if preferred_lot_id:
        # Use preferred lot if it exists and has a selling price
        for lot in lots:
            if lot.lot_id == preferred_lot_id:
                effective_price = lot.selling_price or 0.0
                logger.debug(f"Using preferred lot {preferred_lot_id} with selling price {effective_price}")
                break
        else:
            # Preferred lot not found, fall through to costing method
            effective_price = None
    else:
        effective_price = None
    
    # If no preferred lot, use costing method
    if effective_price is None:
        method = get_costing_method()
        
        if method == CostingMethod.FIFO:
            # FIFO: Use the oldest (first) lot's selling price
            effective_price = lots[0].selling_price or 0.0
        elif method == CostingMethod.LIFO:
            # LIFO: Use the newest (last) lot's selling price
            effective_price = lots[-1].selling_price or 0.0
        else:  # WAC (Weighted Average Cost)
            # Calculate weighted average selling price
            total_cost = sum(lot.quantity_remaining * (lot.selling_price or 0.0) for lot in lots)
            total_quantity = sum(lot.quantity_remaining for lot in lots)
            effective_price = total_cost / total_quantity if total_quantity > 0 else 0.0
    
    # Get min and max prices across all lots
    prices = [lot.selling_price for lot in lots if lot.selling_price]
    min_price = min(prices) if prices else 0.0
    max_price = max(prices) if prices else 0.0
    
    return (effective_price, min_price, max_price)


# =============================================================================
# COST ALLOCATION METHODS
# =============================================================================

def allocate_stock_fifo(
    item_id: int,
    quantity_needed: int,
    variant_id: Optional[int] = None
) -> List[LotAllocation]:
    """Allocate stock using First-In, First-Out (FIFO) method.
    
    Oldest inventory is sold first.
    
    Args:
        item_id: Item ID to allocate from
        quantity_needed: Quantity to allocate
        variant_id: Optional variant ID
        
    Returns:
        List of LotAllocation objects
    """
    allocations: List[LotAllocation] = []
    remaining = quantity_needed
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT lot_id, quantity_remaining, cost_price 
            FROM stock_lots 
            WHERE item_id = ? AND quantity_remaining > 0
        """
        params: List[Any] = [item_id]
        
        if variant_id is not None:
            query += " AND variant_id = ?"
            params.append(variant_id)
        
        # FIFO: Order by oldest first
        query += " ORDER BY purchase_date ASC, lot_id ASC"
        
        lots = conn.execute(query, params).fetchall()
        
        for lot in lots:
            if remaining <= 0:
                break
            
            take = min(remaining, lot["quantity_remaining"])
            allocations.append(LotAllocation(
                lot_id=lot["lot_id"],
                quantity=take,
                unit_cost=lot["cost_price"]
            ))
            remaining -= take
    
    if remaining > 0:
        logger.warning(
            f"Insufficient stock for item {item_id}: needed {quantity_needed}, "
            f"could only allocate {quantity_needed - remaining}"
        )
    
    return allocations


def allocate_stock_lifo(
    item_id: int,
    quantity_needed: int,
    variant_id: Optional[int] = None
) -> List[LotAllocation]:
    """Allocate stock using Last-In, First-Out (LIFO) method.
    
    Newest inventory is sold first.
    
    Args:
        item_id: Item ID to allocate from
        quantity_needed: Quantity to allocate
        variant_id: Optional variant ID
        
    Returns:
        List of LotAllocation objects
    """
    allocations: List[LotAllocation] = []
    remaining = quantity_needed
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT lot_id, quantity_remaining, cost_price 
            FROM stock_lots 
            WHERE item_id = ? AND quantity_remaining > 0
        """
        params: List[Any] = [item_id]
        
        if variant_id is not None:
            query += " AND variant_id = ?"
            params.append(variant_id)
        
        # LIFO: Order by newest first
        query += " ORDER BY purchase_date DESC, lot_id DESC"
        
        lots = conn.execute(query, params).fetchall()
        
        for lot in lots:
            if remaining <= 0:
                break
            
            take = min(remaining, lot["quantity_remaining"])
            allocations.append(LotAllocation(
                lot_id=lot["lot_id"],
                quantity=take,
                unit_cost=lot["cost_price"]
            ))
            remaining -= take
    
    if remaining > 0:
        logger.warning(
            f"Insufficient stock for item {item_id}: needed {quantity_needed}, "
            f"could only allocate {quantity_needed - remaining}"
        )
    
    return allocations


def get_weighted_average_cost(
    item_id: int,
    variant_id: Optional[int] = None
) -> float:
    """Calculate weighted average cost across all lots with remaining stock.
    
    Args:
        item_id: Item ID
        variant_id: Optional variant ID
        
    Returns:
        Weighted average cost per unit, or 0 if no stock
    """
    with get_connection() as conn:
        query = """
            SELECT 
                SUM(quantity_remaining * cost_price) as total_value,
                SUM(quantity_remaining) as total_qty
            FROM stock_lots
            WHERE item_id = ? AND quantity_remaining > 0
        """
        params: List[Any] = [item_id]
        
        if variant_id is not None:
            query += " AND variant_id = ?"
            params.append(variant_id)
        
        result = conn.execute(query, params).fetchone()
        
        if result and result[1] and result[1] > 0:
            return result[0] / result[1]
        return 0.0


def allocate_stock_wac(
    item_id: int,
    quantity_needed: int,
    variant_id: Optional[int] = None
) -> List[LotAllocation]:
    """Allocate stock using Weighted Average Cost (WAC) method.
    
    All units are valued at the weighted average cost regardless of lot.
    Physically, we still use FIFO allocation but apply WAC for costing.
    
    Args:
        item_id: Item ID to allocate from
        quantity_needed: Quantity to allocate
        variant_id: Optional variant ID
        
    Returns:
        List of LotAllocation objects with WAC applied
    """
    wac = get_weighted_average_cost(item_id, variant_id)
    
    # Get physical allocation using FIFO
    physical_allocations = allocate_stock_fifo(item_id, quantity_needed, variant_id)
    
    # Apply WAC to all allocations
    wac_allocations = [
        LotAllocation(
            lot_id=alloc.lot_id,
            quantity=alloc.quantity,
            unit_cost=wac
        )
        for alloc in physical_allocations
    ]
    
    return wac_allocations


def allocate_stock(
    item_id: int,
    quantity_needed: int,
    variant_id: Optional[int] = None,
    method: Optional[CostingMethod] = None
) -> List[LotAllocation]:
    """Allocate stock using the configured or specified costing method.
    
    Args:
        item_id: Item ID to allocate from
        quantity_needed: Quantity to allocate
        variant_id: Optional variant ID
        method: Override costing method (uses system setting if None)
        
    Returns:
        List of LotAllocation objects
    """
    if method is None:
        method = get_costing_method()
    
    if method == CostingMethod.FIFO:
        return allocate_stock_fifo(item_id, quantity_needed, variant_id)
    elif method == CostingMethod.LIFO:
        return allocate_stock_lifo(item_id, quantity_needed, variant_id)
    elif method == CostingMethod.WAC:
        return allocate_stock_wac(item_id, quantity_needed, variant_id)
    else:
        # Default to FIFO for unknown methods
        return allocate_stock_fifo(item_id, quantity_needed, variant_id)


# =============================================================================
# STOCK DEDUCTION & MOVEMENT RECORDING
# =============================================================================

def deduct_stock_from_lots(
    allocations: List[LotAllocation],
    item_id: int,
    sale_item_id: Optional[int] = None,
    user_id: Optional[int] = None,
    variant_id: Optional[int] = None
) -> float:
    """Deduct stock from lots based on allocations and record movements.
    
    Args:
        allocations: List of LotAllocation objects
        item_id: Item ID
        sale_item_id: Optional sale_item_id for reference
        user_id: User performing the deduction
        variant_id: Optional variant ID
        
    Returns:
        Total cost of goods sold
    """
    total_cogs = 0.0
    
    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            for alloc in allocations:
                # Deduct from lot
                conn.execute(
                    "UPDATE stock_lots SET quantity_remaining = quantity_remaining - ? WHERE lot_id = ?",
                    (alloc.quantity, alloc.lot_id)
                )
                
                # Record movement
                conn.execute(
                    """
                    INSERT INTO stock_movements
                    (item_id, variant_id, lot_id, movement_type, quantity, unit_cost, total_cost,
                     reference_id, reference_type, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item_id, variant_id, alloc.lot_id, MovementType.SALE.value, 
                     -alloc.quantity, alloc.unit_cost, alloc.total_cost,
                     sale_item_id, 'sale_item', user_id)
                )
                
                # Record lot allocation for sale item
                if sale_item_id:
                    conn.execute(
                        """
                        INSERT INTO sale_lot_allocations
                        (sale_item_id, lot_id, quantity, unit_cost)
                        VALUES (?, ?, ?, ?)
                        """,
                        (sale_item_id, alloc.lot_id, alloc.quantity, alloc.unit_cost)
                    )
                
                total_cogs += alloc.total_cost
            
            # Update item's total quantity
            total_qty = sum(a.quantity for a in allocations)
            conn.execute(
                "UPDATE items SET quantity = quantity - ? WHERE item_id = ?",
                (total_qty, item_id)
            )
            
            # Update variant quantity if applicable
            if variant_id:
                conn.execute(
                    "UPDATE item_variants SET quantity = quantity - ? WHERE variant_id = ?",
                    (total_qty, variant_id)
                )
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to deduct stock: {e}")
            raise
    
    return total_cogs


def record_stock_adjustment(
    item_id: int,
    quantity_change: int,
    reason: str,
    user_id: Optional[int] = None,
    variant_id: Optional[int] = None,
    lot_id: Optional[int] = None,
    unit_cost: Optional[float] = None
) -> StockMovement:
    """Record a stock adjustment (increase or decrease).
    
    Args:
        item_id: Item ID
        quantity_change: Positive for increase, negative for decrease
        reason: Reason for adjustment
        user_id: User making the adjustment
        variant_id: Optional variant ID
        lot_id: Optional lot ID for specific lot adjustments
        unit_cost: Unit cost for the adjustment
        
    Returns:
        Created StockMovement object
    """
    movement_type = MovementType.ADJUSTMENT
    
    # Determine if this is waste (negative adjustment with reason)
    waste_keywords = ('waste', 'spoil', 'damage', 'expired', 'breakage', 'theft')
    if quantity_change < 0 and any(kw in reason.lower() for kw in waste_keywords):
        movement_type = MovementType.WASTE
    
    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            # Deduct from lots when reducing stock
            if quantity_change < 0:
                if lot_id:
                    # Deduct from the specific lot
                    conn.execute(
                        "UPDATE stock_lots SET quantity_remaining = quantity_remaining + ? WHERE lot_id = ?",
                        (quantity_change, lot_id)  # quantity_change is negative
                    )
                else:
                    # No specific lot — use costing method to pick lots (FIFO by default)
                    conn.row_factory = sqlite3.Row
                    available_lots = conn.execute(
                        "SELECT lot_id, quantity_remaining FROM stock_lots "
                        "WHERE item_id = ? AND quantity_remaining > 0 "
                        "ORDER BY purchase_date ASC, lot_id ASC",
                        (item_id,)
                    ).fetchall()
                    remaining = abs(quantity_change)
                    for a_lot in available_lots:
                        if remaining <= 0:
                            break
                        take = min(remaining, a_lot["quantity_remaining"])
                        conn.execute(
                            "UPDATE stock_lots SET quantity_remaining = quantity_remaining - ? WHERE lot_id = ?",
                            (take, a_lot["lot_id"])
                        )
                        remaining -= take
                        # Use the first lot_id for the movement record
                        if lot_id is None:
                            lot_id = a_lot["lot_id"]
            
            # Record the movement
            cursor = conn.execute(
                """
                INSERT INTO stock_movements
                (item_id, variant_id, lot_id, movement_type, quantity, unit_cost, total_cost,
                 user_id, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, variant_id, lot_id, movement_type.value, quantity_change,
                 unit_cost, (unit_cost or 0) * abs(quantity_change), user_id, reason)
            )
            movement_id = cursor.lastrowid
            
            # Update item quantity
            conn.execute(
                "UPDATE items SET quantity = quantity + ? WHERE item_id = ?",
                (quantity_change, item_id)
            )
            
            # Update variant quantity if applicable
            if variant_id:
                conn.execute(
                    "UPDATE item_variants SET quantity = quantity + ? WHERE variant_id = ?",
                    (quantity_change, variant_id)
                )
            
            conn.commit()
            
            return StockMovement(
                movement_id=movement_id,
                item_id=item_id,
                variant_id=variant_id,
                lot_id=lot_id,
                movement_type=movement_type,
                quantity=quantity_change,
                unit_cost=unit_cost,
                user_id=user_id,
                notes=reason
            )
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record adjustment: {e}")
            raise


def record_return_to_stock(
    item_id: int,
    quantity: int,
    original_sale_item_id: int,
    user_id: Optional[int] = None,
    variant_id: Optional[int] = None,
    notes: Optional[str] = None
) -> None:
    """Return stock from a refund back to the original lots.
    
    Args:
        item_id: Item ID
        quantity: Quantity being returned
        original_sale_item_id: Original sale_item_id for tracking
        user_id: User processing the return
        variant_id: Optional variant ID
        notes: Additional notes
    """
    with get_connection() as conn:
        conn.execute("BEGIN")
        try:
            # Get original lot allocations for this sale item
            conn.row_factory = sqlite3.Row
            allocations = conn.execute(
                """
                SELECT lot_id, quantity, unit_cost
                FROM sale_lot_allocations
                WHERE sale_item_id = ?
                ORDER BY allocation_id ASC
                """,
                (original_sale_item_id,)
            ).fetchall()
            
            remaining_return = quantity
            
            for alloc in allocations:
                if remaining_return <= 0:
                    break
                
                return_qty = min(remaining_return, alloc["quantity"])
                
                # Return to lot
                conn.execute(
                    "UPDATE stock_lots SET quantity_remaining = quantity_remaining + ? WHERE lot_id = ?",
                    (return_qty, alloc["lot_id"])
                )
                
                # Record return movement
                conn.execute(
                    """
                    INSERT INTO stock_movements
                    (item_id, variant_id, lot_id, movement_type, quantity, unit_cost, total_cost,
                     reference_id, reference_type, user_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item_id, variant_id, alloc["lot_id"], MovementType.RETURN.value,
                     return_qty, alloc["unit_cost"], return_qty * alloc["unit_cost"],
                     original_sale_item_id, 'return', user_id, notes)
                )
                
                remaining_return -= return_qty
            
            # Update item quantity
            conn.execute(
                "UPDATE items SET quantity = quantity + ? WHERE item_id = ?",
                (quantity, item_id)
            )
            
            # Update variant quantity if applicable
            if variant_id:
                conn.execute(
                    "UPDATE item_variants SET quantity = quantity + ? WHERE variant_id = ?",
                    (quantity, variant_id)
                )
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record return: {e}")
            raise


# =============================================================================
# INVENTORY VALUATION & REPORTING
# =============================================================================

def get_inventory_valuation(item_id: Optional[int] = None) -> Dict[str, Any]:
    """Get inventory valuation using the current costing method.
    
    Args:
        item_id: Optional item ID for single item valuation
        
    Returns:
        Dictionary with valuation details
    """
    method = get_costing_method()
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        if item_id:
            # Single item valuation
            query = """
                SELECT 
                    i.item_id,
                    i.name,
                    i.category,
                    COALESCE(SUM(sl.quantity_remaining), 0) as total_qty,
                    COALESCE(SUM(sl.quantity_remaining * sl.cost_price), 0) as total_value,
                    COUNT(DISTINCT sl.lot_id) as lot_count
                FROM items i
                LEFT JOIN stock_lots sl ON i.item_id = sl.item_id AND sl.quantity_remaining > 0
                WHERE i.item_id = ?
                GROUP BY i.item_id
            """
            rows = conn.execute(query, (item_id,)).fetchall()
        else:
            # All items valuation
            query = """
                SELECT 
                    i.item_id,
                    i.name,
                    i.category,
                    COALESCE(SUM(sl.quantity_remaining), 0) as total_qty,
                    COALESCE(SUM(sl.quantity_remaining * sl.cost_price), 0) as total_value,
                    COUNT(DISTINCT sl.lot_id) as lot_count
                FROM items i
                LEFT JOIN stock_lots sl ON i.item_id = sl.item_id AND sl.quantity_remaining > 0
                GROUP BY i.item_id
                HAVING total_qty > 0
                ORDER BY i.name
            """
            rows = conn.execute(query).fetchall()
        
        items = []
        total_value = 0.0
        total_units = 0
        
        for row in rows:
            avg_cost = row["total_value"] / row["total_qty"] if row["total_qty"] > 0 else 0
            item_data = {
                "item_id": row["item_id"],
                "name": row["name"],
                "category": row["category"],
                "quantity": row["total_qty"],
                "total_value": row["total_value"],
                "average_cost": avg_cost,
                "lot_count": row["lot_count"]
            }
            items.append(item_data)
            total_value += row["total_value"]
            total_units += row["total_qty"]
        
        return {
            "costing_method": method.value,
            "items": items,
            "summary": {
                "total_items": len(items),
                "total_units": total_units,
                "total_value": total_value
            }
        }


def get_stock_movements_history(
    item_id: Optional[int] = None,
    movement_type: Optional[MovementType] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> List[StockMovement]:
    """Get stock movement history with optional filters.
    
    Args:
        item_id: Optional item ID filter
        movement_type: Optional movement type filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum records to return
        
    Returns:
        List of StockMovement objects
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        query = "SELECT * FROM stock_movements WHERE 1=1"
        params: List[Any] = []
        
        if item_id:
            query += " AND item_id = ?"
            params.append(item_id)
        
        if movement_type:
            query += " AND movement_type = ?"
            params.append(movement_type.value)
        
        if start_date:
            query += " AND DATE(created_at) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(created_at) <= ?"
            params.append(end_date)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        
        return [
            StockMovement(
                movement_id=row["movement_id"],
                item_id=row["item_id"],
                variant_id=row["variant_id"],
                lot_id=row["lot_id"],
                movement_type=MovementType(row["movement_type"]),
                quantity=row["quantity"],
                unit_cost=row["unit_cost"],
                total_cost=row["total_cost"],
                reference_id=row["reference_id"],
                reference_type=row["reference_type"],
                user_id=row["user_id"],
                notes=row["notes"],
                created_at=row["created_at"]
            )
            for row in rows
        ]


def get_lot_expiry_report(days_ahead: int = 30) -> List[Dict[str, Any]]:
    """Get lots expiring within the specified days.
    
    Args:
        days_ahead: Days to look ahead for expiring items
        
    Returns:
        List of lots with expiry information
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        query = """
            SELECT 
                sl.lot_id,
                sl.item_id,
                i.name as item_name,
                sl.quantity_remaining,
                sl.cost_price,
                sl.expiry_date,
                sl.supplier,
                JULIANDAY(sl.expiry_date) - JULIANDAY('now') as days_until_expiry
            FROM stock_lots sl
            JOIN items i ON sl.item_id = i.item_id
            WHERE sl.quantity_remaining > 0
              AND sl.expiry_date IS NOT NULL
              AND DATE(sl.expiry_date) <= DATE('now', ? || ' days')
            ORDER BY sl.expiry_date ASC
        """
        
        rows = conn.execute(query, (f"+{days_ahead}",)).fetchall()
        
        return [dict(row) for row in rows]


# =============================================================================
# MIGRATION HELPERS
# =============================================================================

def migrate_existing_inventory_to_lots(user_id: Optional[int] = None) -> int:
    """Migrate existing inventory to stock lots for fresh installations.
    
    Creates initial stock lots for items that have quantity but no lots.
    
    Args:
        user_id: User performing the migration
        
    Returns:
        Number of items migrated
    """
    migrated = 0
    
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Find items with quantity but no lots
        items = conn.execute("""
            SELECT i.item_id, i.quantity, i.cost_price, i.name
            FROM items i
            WHERE i.quantity > 0
              AND NOT EXISTS (
                  SELECT 1 FROM stock_lots sl WHERE sl.item_id = i.item_id
              )
        """).fetchall()
        
        for item in items:
            if item["quantity"] > 0:
                # Create opening stock lot
                try:
                    conn.execute(
                        """
                        INSERT INTO stock_lots 
                        (item_id, purchase_date, quantity_received, quantity_remaining,
                         cost_price, notes, created_by)
                        VALUES (?, DATE('now'), ?, ?, ?, ?, ?)
                        """,
                        (item["item_id"], item["quantity"], item["quantity"],
                         item["cost_price"], "Opening stock migration", user_id)
                    )
                    
                    # Record opening stock movement
                    conn.execute(
                        """
                        INSERT INTO stock_movements
                        (item_id, movement_type, quantity, unit_cost, total_cost, user_id, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (item["item_id"], MovementType.OPENING_STOCK.value, item["quantity"],
                         item["cost_price"], item["quantity"] * item["cost_price"],
                         user_id, "Opening stock from migration")
                    )
                    
                    migrated += 1
                    logger.info(f"Migrated item {item['name']} ({item['quantity']} units)")
                except Exception as e:
                    logger.error(f"Failed to migrate item {item['item_id']}: {e}")
        
        conn.commit()
    
    logger.info(f"Migration complete: {migrated} items converted to stock lots")
    return migrated


def has_stock_lots(item_id: int) -> bool:
    """Check if an item has any stock lots (for migration detection)."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM stock_lots WHERE item_id = ?",
            (item_id,)
        ).fetchone()
        return result[0] > 0 if result else False


def get_item_cost_price(item_id: int, variant_id: Optional[int] = None) -> float:
    """Get the cost price for an item based on costing method.
    
    For items with lots, returns cost based on method.
    For items without lots, falls back to item's cost_price field.
    
    Args:
        item_id: Item ID
        variant_id: Optional variant ID
        
    Returns:
        Cost price per unit
    """
    method = get_costing_method()
    
    # Check if item has lots
    if has_stock_lots(item_id):
        if method == CostingMethod.WAC:
            return get_weighted_average_cost(item_id, variant_id)
        else:
            # For FIFO/LIFO, get the next lot that would be sold
            allocations = allocate_stock(item_id, 1, variant_id, method)
            if allocations:
                return allocations[0].unit_cost
    
    # Fall back to item's cost_price
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        if variant_id:
            result = conn.execute(
                "SELECT cost_price FROM item_variants WHERE variant_id = ?",
                (variant_id,)
            ).fetchone()
            if result:
                return result["cost_price"]
        
        result = conn.execute(
            "SELECT cost_price FROM items WHERE item_id = ?",
            (item_id,)
        ).fetchone()
        
        return result["cost_price"] if result else 0.0


def set_item_preferred_lot(item_id: int, lot_id: int) -> bool:
    """Set the preferred lot for pricing an item.
    
    This saves which lot should be used for determining the item's pricing
    in the POS system. Useful for items with multiple stock lots where you
    want to prioritize a specific lot.
    
    Args:
        item_id: Item ID
        lot_id: Lot ID to set as preferred
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_connection() as conn:
            # Check if the lot exists and belongs to this item
            lot = conn.execute(
                "SELECT lot_id FROM stock_lots WHERE lot_id = ? AND item_id = ?",
                (lot_id, item_id)
            ).fetchone()
            
            if not lot:
                logger.warning(f"Lot {lot_id} not found for item {item_id}")
                return False
            
            # Update the items table with the preferred lot
            conn.execute(
                "UPDATE items SET preferred_lot_id = ? WHERE item_id = ?",
                (lot_id, item_id)
            )
            conn.commit()
            
            logger.info(f"Set preferred lot {lot_id} for item {item_id}")
            
            # Notify subscribers that the item's pricing has changed
            try:
                from utils.inventory_notifications import notify_inventory_changed
                notify_inventory_changed('price_changed', item_id, 0.0, lot_id=lot_id)
            except ImportError:
                pass  # Notification system not available
            
            return True
            
    except Exception as e:
        logger.error(f"Failed to set preferred lot: {e}")
        return False


def get_preferred_lot(item_id: int) -> Optional[int]:
    """Get the preferred lot ID for an item.
    
    Args:
        item_id: Item ID
        
    Returns:
        Lot ID if a preferred lot is set, None otherwise
    """
    try:
        with get_connection() as conn:
            result = conn.execute(
                "SELECT preferred_lot_id FROM items WHERE item_id = ?",
                (item_id,)
            ).fetchone()
            
            if result and result[0]:
                return result[0]
            return None
            
    except Exception as e:
        logger.error(f"Failed to get preferred lot: {e}")
        return None
