"""
Stock Reconciliation Module

Stock reconciliation by comparing physical counts against POS records.
Supports daily, weekly, monthly, and custom period types.

Formula:
    Daily Sales (actual) = Opening Stock + Stock Received - Closing Stock (physical count)
    Expected Closing     = Opening Stock + Stock Received - POS Sales - Other Outflows
    Variance             = Actual Closing - Expected Closing
        positive = more stock than expected (e.g. unrecorded receipt)
        negative = less stock than expected (e.g. theft, waste, breakage)

Opening Stock logic:
    1. If a completed stock reconciliation exists for a prior period,
       use its actual_closing as the new period's opening.
    2. Otherwise, back-calculate from current system quantity:
       Opening = Current Qty + Period Sales - Period Received + Period OtherOut
"""

from __future__ import annotations
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from database.init_db import get_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Data classes
# ---------------------------------------------------------------------------
@dataclass
class StockReconEntry:
    """One item row in a stock reconciliation session."""
    item_id: int
    item_name: str
    opening_stock: float = 0.0
    stock_received: float = 0.0
    system_sales: float = 0.0
    other_out: float = 0.0          # adjustments, waste, transfers out
    expected_closing: float = 0.0   # opening + received - sales - other_out
    actual_closing: float = 0.0     # user's physical count
    variance: float = 0.0           # actual_closing - expected_closing
    notes: str = ""
    entry_id: Optional[int] = None

    def recalculate(self) -> None:
        """Recompute expected closing and variance."""
        self.expected_closing = (
            self.opening_stock + self.stock_received
            - self.system_sales - self.other_out
        )
        self.variance = self.actual_closing - self.expected_closing


@dataclass
class StockReconSession:
    """A stock reconciliation session for a date range / period."""
    reconciliation_date: str
    period_type: str = "daily"          # daily, weekly, monthly, custom
    start_date: str = ""                # first day of the period
    end_date: str = ""                  # last day of the period
    status: str = "draft"
    created_by: Optional[int] = None
    completed_at: Optional[str] = None
    notes: str = ""
    entries: List[StockReconEntry] = field(default_factory=list)
    session_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def total_variance(self) -> float:
        return sum(e.variance for e in self.entries)

    @property
    def total_system_sales(self) -> float:
        return sum(e.system_sales for e in self.entries)

    @property
    def total_actual_sales(self) -> float:
        """Actual sales derived from counts: opening + received - actual_closing - other_out."""
        return sum(
            e.opening_stock + e.stock_received - e.actual_closing - e.other_out
            for e in self.entries
        )


# ---------------------------------------------------------------------------
#  Query helpers – data pulled from existing tables
# ---------------------------------------------------------------------------

def _get_items_with_stock() -> List[Dict[str, Any]]:
    """Return all items that have ever had stock (quantity > 0 or movements exist)."""
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT item_id, name, quantity
                FROM items
                ORDER BY name COLLATE NOCASE
            """).fetchall()
        return [dict(r) for r in rows] if rows is not None else []
    except Exception as e:
        logger.error(f"Failed to get items with stock: {e}")
        return None


def _get_sales_qty_by_item(start_date: str, end_date: str) -> Dict[int, float]:
    """Total quantity sold per item in a date range (excludes voided sales)."""
    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT si.item_id, SUM(si.quantity) as qty
                FROM sales_items si
                JOIN sales s ON si.sale_id = s.sale_id
                WHERE s.date BETWEEN ? AND ?
                  AND (s.voided IS NULL OR s.voided = 0)
                GROUP BY si.item_id
            """, (start_date, end_date)).fetchall()
        return {r[0]: r[1] for r in rows} if rows is not None else {}
    except Exception as e:
        logger.error(f"Failed to get sales qty by item: {e}")
        return None


def _get_received_qty_by_item(start_date: str, end_date: str) -> Dict[int, float]:
    """Total quantity received (purchase movements) per item in a date range."""
    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT item_id, SUM(quantity) as qty
                FROM stock_movements
                WHERE DATE(created_at) BETWEEN ? AND ?
                  AND movement_type = 'purchase'
                GROUP BY item_id
            """, (start_date, end_date)).fetchall()
        return {r[0]: r[1] for r in rows} if rows is not None else {}
    except Exception as e:
        logger.error(f"Failed to get received qty by item: {e}")
        return None


def _get_other_outflows_by_item(start_date: str, end_date: str) -> Dict[int, float]:
    """Total outflow (adjustment, waste, transfer) per item in a date range.

    Only negative-direction movements count here (quantity is usually
    stored as negative for deductions, but some implementations store
    positive + movement_type). We take ABS of negatives.
    """
    try:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT item_id, SUM(ABS(quantity)) as qty
                FROM stock_movements
                WHERE DATE(created_at) BETWEEN ? AND ?
                  AND movement_type IN ('adjustment', 'waste', 'transfer')
                  AND quantity < 0
                GROUP BY item_id
            """, (start_date, end_date)).fetchall()
        return {r[0]: r[1] for r in rows} if rows is not None else {}
    except Exception as e:
        logger.error(f"Failed to get other outflows by item: {e}")
        return None


def _get_previous_closing(item_id: int, start_date: str) -> Optional[float]:
    """Get the actual_closing from the most recent completed stock recon
    session whose end_date is before `start_date` for a given item."""
    try:
        with get_connection() as conn:
            # Try using end_date first (period-aware), fall back to reconciliation_date
            row = conn.execute("""
                SELECT e.actual_closing
                FROM stock_reconciliation_entries e
                JOIN stock_reconciliation_sessions s ON e.session_id = s.session_id
                WHERE e.item_id = ?
                  AND COALESCE(NULLIF(s.end_date, ''), s.reconciliation_date) < ?
                  AND s.status = 'completed'
                ORDER BY COALESCE(NULLIF(s.end_date, ''), s.reconciliation_date) DESC
                LIMIT 1
            """, (item_id, start_date)).fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Failed to get previous closing for item {item_id}: {e}")
        return None


def _calculate_opening_stock(
    item_id: int,
    current_system_qty: float,
    start_date: str,
    period_sales: float,
    period_received: float,
    period_other_out: float,
) -> float:
    """Determine opening stock for an item at the start of a period.

    Priority:
        1. Previous completed stock recon's actual_closing.
        2. Back-calculate: current_qty + period_sales - period_received + period_other_out
    """
    prev = _get_previous_closing(item_id, start_date)
    if prev is not None:
        return prev

    # Back-calculate from system's current quantity
    opening = current_system_qty + period_sales - period_received + period_other_out
    return max(opening, 0)  # clamp to 0 if somehow negative


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def calculate_stock_date_range(period_type: str, reference_date: str) -> tuple:
    """Calculate start/end dates for a stock reconciliation period.

    Returns (start_date, end_date) as ISO strings.
    """
    from utils.date_utils import parse_date_flexible

    ref = parse_date_flexible(reference_date)

    if period_type == "daily":
        start = end = ref
    elif period_type == "weekly":
        start = ref - timedelta(days=ref.weekday())  # Monday
        end = start + timedelta(days=6)               # Sunday
    elif period_type == "monthly":
        start = ref.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
    else:  # custom – caller supplies dates directly
        start = end = ref

    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def create_stock_recon_session(
    reconciliation_date: str,
    user_id: int = 1,
    item_ids: Optional[List[int]] = None,
    period_type: str = "daily",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> StockReconSession:
    """Create a new stock reconciliation session (in memory, not saved yet).

    Populates every item (or selected items) with:
        - opening_stock  (from previous recon or back-calculated)
        - stock_received (purchases in the period)
        - system_sales   (POS sales in the period)
        - other_out      (adjustments, waste, transfers in the period)
        - expected_closing
    actual_closing defaults to 0 (user fills in physical count).
    """
    # Resolve date range
    if start_date and end_date:
        sd, ed = start_date, end_date
    else:
        sd, ed = calculate_stock_date_range(period_type, reconciliation_date)

    items = _get_items_with_stock()
    if items is None:
        raise ValueError("Failed to retrieve items from database")
    
    sales = _get_sales_qty_by_item(sd, ed)
    if sales is None:
        raise ValueError("Failed to retrieve sales data from database")
    
    received = _get_received_qty_by_item(sd, ed)
    if received is None:
        raise ValueError("Failed to retrieve received data from database")
    
    other_out = _get_other_outflows_by_item(sd, ed)
    if other_out is None:
        raise ValueError("Failed to retrieve other outflows data from database")

    entries: List[StockReconEntry] = []
    for item in items:
        iid = item["item_id"]

        # If specific items requested, skip the rest
        if item_ids and iid not in item_ids:
            continue

        s = sales.get(iid, 0.0)
        r = received.get(iid, 0.0)
        o = other_out.get(iid, 0.0)

        opening = _calculate_opening_stock(
            iid, item["quantity"], sd, s, r, o
        )

        entry = StockReconEntry(
            item_id=iid,
            item_name=item["name"],
            opening_stock=opening,
            stock_received=r,
            system_sales=s,
            other_out=o,
        )
        entry.recalculate()
        entries.append(entry)

    return StockReconSession(
        reconciliation_date=reconciliation_date,
        period_type=period_type,
        start_date=sd,
        end_date=ed,
        created_by=user_id,
        entries=entries,
    )


def save_stock_recon_session(session: StockReconSession) -> int:
    """Persist a session and its entries. Returns session_id."""
    with get_connection() as conn:
        cur = conn.cursor()

        if session.session_id is None:
            # Check for existing draft on same date + period
            existing = cur.execute("""
                SELECT session_id FROM stock_reconciliation_sessions
                WHERE reconciliation_date = ? AND period_type = ? AND status = 'draft'
            """, (session.reconciliation_date, session.period_type)).fetchone()

            if existing:
                # Update existing draft
                session.session_id = existing[0]
                cur.execute("""
                    UPDATE stock_reconciliation_sessions
                    SET start_date = ?, end_date = ?, notes = ?, updated_at = ?
                    WHERE session_id = ?
                """, (session.start_date, session.end_date,
                      session.notes, datetime.now().isoformat(), session.session_id))

                # Delete old entries and re-insert
                cur.execute("DELETE FROM stock_reconciliation_entries WHERE session_id = ?",
                            (session.session_id,))
            else:
                cur.execute("""
                    INSERT INTO stock_reconciliation_sessions
                    (reconciliation_date, period_type, start_date, end_date, status, created_by, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session.reconciliation_date, session.period_type,
                      session.start_date, session.end_date,
                      session.status, session.created_by, session.notes))
                session.session_id = cur.lastrowid
        else:
            # Update existing
            cur.execute("""
                UPDATE stock_reconciliation_sessions
                SET status = ?, completed_at = ?, notes = ?, updated_at = ?
                WHERE session_id = ?
            """, (session.status, session.completed_at, session.notes,
                  datetime.now().isoformat(), session.session_id))

            cur.execute("DELETE FROM stock_reconciliation_entries WHERE session_id = ?",
                        (session.session_id,))

        # Insert entries
        for e in session.entries:
            cur.execute("""
                INSERT INTO stock_reconciliation_entries
                (session_id, item_id, item_name, opening_stock, stock_received,
                 system_sales, other_out, expected_closing, actual_closing, variance, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session.session_id, e.item_id, e.item_name, e.opening_stock,
                  e.stock_received, e.system_sales, e.other_out,
                  e.expected_closing, e.actual_closing, e.variance, e.notes))

        conn.commit()
    return session.session_id


def get_stock_recon_session(session_id: int) -> Optional[StockReconSession]:
    """Load a stock reconciliation session by ID."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("""
            SELECT * FROM stock_reconciliation_sessions WHERE session_id = ?
        """, (session_id,)).fetchone()
        if not row:
            return None

        entries_rows = conn.execute("""
            SELECT * FROM stock_reconciliation_entries
            WHERE session_id = ?
            ORDER BY item_name COLLATE NOCASE
        """, (session_id,)).fetchall()

    entries = []
    for er in entries_rows:
        entries.append(StockReconEntry(
            entry_id=er["entry_id"],
            item_id=er["item_id"],
            item_name=er["item_name"],
            opening_stock=er["opening_stock"],
            stock_received=er["stock_received"],
            system_sales=er["system_sales"],
            other_out=er["other_out"],
            expected_closing=er["expected_closing"],
            actual_closing=er["actual_closing"],
            variance=er["variance"],
            notes=er["notes"] or "",
        ))

    return StockReconSession(
        session_id=row["session_id"],
        reconciliation_date=row["reconciliation_date"],
        period_type=row["period_type"] if "period_type" in row.keys() else "daily",
        start_date=row["start_date"] if "start_date" in row.keys() else row["reconciliation_date"],
        end_date=row["end_date"] if "end_date" in row.keys() else row["reconciliation_date"],
        status=row["status"],
        created_by=row["created_by"],
        completed_at=row["completed_at"],
        notes=row["notes"] or "",
        entries=entries,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def get_stock_recon_sessions(
    limit: int = 50,
    status: Optional[str] = None,
) -> List[StockReconSession]:
    """List stock reconciliation sessions (most recent first)."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        q = "SELECT * FROM stock_reconciliation_sessions"
        params: list = []
        if status:
            q += " WHERE status = ?"
            params.append(status)
        q += " ORDER BY reconciliation_date DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(q, params).fetchall()

    sessions = []
    for r in rows:
        sessions.append(StockReconSession(
            session_id=r["session_id"],
            reconciliation_date=r["reconciliation_date"],
            period_type=r["period_type"] if "period_type" in r.keys() else "daily",
            start_date=r["start_date"] if "start_date" in r.keys() else r["reconciliation_date"],
            end_date=r["end_date"] if "end_date" in r.keys() else r["reconciliation_date"],
            status=r["status"],
            created_by=r["created_by"],
            completed_at=r["completed_at"],
            notes=r["notes"] or "",
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        ))
    return sessions


def complete_stock_recon_session(session_id: int, notes: str = "") -> bool:
    """Mark a stock reconciliation session as completed."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE stock_reconciliation_sessions
            SET status = 'completed', completed_at = ?, notes = ?, updated_at = ?
            WHERE session_id = ? AND status = 'draft'
        """, (datetime.now().isoformat(), notes,
              datetime.now().isoformat(), session_id))
        conn.commit()
        return cur.rowcount > 0


def delete_stock_recon_session(session_id: int) -> None:
    """Delete a stock reconciliation session and its entries."""
    with get_connection() as conn:
        conn.execute("DELETE FROM stock_reconciliation_entries WHERE session_id = ?",
                     (session_id,))
        conn.execute("DELETE FROM stock_reconciliation_sessions WHERE session_id = ?",
                     (session_id,))
        conn.commit()


def update_entry_actual(
    session: StockReconSession,
    item_id: int,
    actual_closing: float,
) -> None:
    """Update the actual closing stock for one item and recalculate variance."""
    for e in session.entries:
        if e.item_id == item_id:
            e.actual_closing = actual_closing
            e.recalculate()
            break


def get_stock_recon_summary(session: StockReconSession) -> Dict[str, Any]:
    """Return summary statistics for a session."""
    total_items = len(session.entries)
    counted = sum(1 for e in session.entries if e.actual_closing > 0)
    items_with_variance = sum(
        1 for e in session.entries if abs(e.variance) >= 0.01
    )
    total_variance_qty = sum(e.variance for e in session.entries)

    return {
        "total_items": total_items,
        "counted_items": counted,
        "uncounted_items": total_items - counted,
        "items_with_variance": items_with_variance,
        "total_variance_qty": total_variance_qty,
        "total_system_sales": session.total_system_sales,
        "total_actual_sales": session.total_actual_sales,
        "sales_variance": session.total_actual_sales - session.total_system_sales,
    }
