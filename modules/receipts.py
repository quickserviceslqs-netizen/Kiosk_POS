"""Receipt/Invoice generation and management."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from database.init_db import get_connection


def get_sale_with_items(sale_id: int) -> dict | None:
    """Get a sale record with all line items."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Check if customers table exists
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        has_customers = 'customers' in tables
        
        # Get sale header with user and customer info
        if has_customers:
            sale = conn.execute(
                "SELECT s.*, u.username AS username, c.name AS customer_name, c.phone AS customer_phone, c.email AS customer_email "
                "FROM sales s "
                "LEFT JOIN users u ON s.user_id = u.user_id "
                "LEFT JOIN customers c ON s.customer_id = c.customer_id "
                "WHERE s.sale_id = ?",
                (sale_id,)
            ).fetchone()
        else:
            sale = conn.execute(
                "SELECT s.*, u.username AS username, NULL AS customer_name, NULL AS customer_phone, NULL AS customer_email "
                "FROM sales s "
                "LEFT JOIN users u ON s.user_id = u.user_id "
                "WHERE s.sale_id = ?",
                (sale_id,)
            ).fetchone()
        if not sale:
            return None
        
        # Get sale items with unit info for proper display
        items = conn.execute(
            """SELECT si.*, i.name, i.category, i.is_special_volume, i.unit_of_measure, 
                      i.unit_size_ml, i.unit_multiplier 
               FROM sales_items si 
               LEFT JOIN items i ON si.item_id = i.item_id 
               WHERE si.sale_id = ?""",
            (sale_id,)
        ).fetchall()
        
        # Convert Row to dict
        sale_dict = dict(sale)
        
        return {
            "sale_id": sale_dict["sale_id"],
            "receipt_number": sale_dict.get("receipt_number"),
            "date": sale_dict["date"],
            "time": sale_dict["time"],
            "total": sale_dict["total"],
            "subtotal": sale_dict.get("subtotal", 0),
            "vat_amount": sale_dict.get("vat_amount", 0),
            "discount_amount": sale_dict.get("discount_amount", 0),
            "payment_received": sale_dict.get("payment_received", 0),
            "change": sale_dict.get("change", 0),
            "payment_method": sale_dict.get("payment_method", "Cash"),
            "user_id": sale_dict.get("user_id"),
            "username": sale_dict.get("username"),
            "customer_id": sale_dict.get("customer_id"),
            "customer_name": sale_dict.get("customer_name"),
            "customer_phone": sale_dict.get("customer_phone"),
            "customer_email": sale_dict.get("customer_email"),
            "items": [dict(item) for item in items],
        }


def format_receipt(sale_data: dict, currency_code: str = "KES", store_name: str = "Kiosk POS") -> str:
    """Format sale data as a text receipt."""
    receipt = []
    receipt.append("=" * 50)
    receipt.append(store_name.center(50))
    receipt.append("=" * 50)
    receipt.append("")
    
    receipt.append(f"Receipt #: {sale_data.get('receipt_number', sale_data['sale_id'])}")
    receipt.append(f"Date: {sale_data['date']} {sale_data['time']}")
    receipt.append("")
    receipt.append("-" * 50)
    receipt.append(f"{'Item':<25} {'Qty':<8} {'Price':<12}")
    receipt.append("-" * 50)
    
    subtotal = 0.0
    for item in sale_data["items"]:
        item_total = item["price"] * item["quantity"]
        subtotal += item_total
        item_name = (item.get("name") or "Unknown")[:24]
        
        # Display quantity with proper units (base unit for special volume items)
        if item.get('is_special_volume'):
            unit_lower = (item.get('unit_of_measure') or '').lower()
            qty = item['quantity']
            multiplier = float(item.get('unit_multiplier') or 1000)
            
            # Convert fractional quantity to base unit display
            if unit_lower in ('liters', 'litre', 'liter', 'litres', 'l'):
                # qty is in ml, convert to L for display
                qty_in_liters = qty / multiplier
                if qty_in_liters >= 1:
                    qty_display = f"{qty_in_liters:.2f} L"
                else:
                    qty_display = f"{qty:.0f} ml"
            elif unit_lower in ('kilograms', 'kilogram', 'kg', 'kgs'):
                # qty is in g, convert to kg for display
                qty_in_kg = qty / multiplier
                if qty_in_kg >= 1:
                    qty_display = f"{qty_in_kg:.2f} kg"
                else:
                    qty_display = f"{qty:.0f} g"
            elif unit_lower in ('meters', 'meter', 'metre', 'metres', 'm'):
                # qty is in cm, convert to m for display
                qty_in_m = qty / multiplier
                if qty_in_m >= 1:
                    qty_display = f"{qty_in_m:.2f} m"
                else:
                    qty_display = f"{qty:.0f} cm"
            else:
                qty_display = f"{qty:.2f}"
        else:
            qty_display = f"{int(item['quantity'])}"
        
        receipt.append(f"{item_name:<25} {qty_display:<8} {currency_code} {item_total:<10.2f}")
    
    receipt.append("-" * 50)
    
    # Use stored subtotal if available, otherwise calculate
    display_subtotal = sale_data.get("subtotal", subtotal)
    receipt.append(f"Subtotal: {' ' * 30} {currency_code} {display_subtotal:.2f}")
    
    # Add VAT if present
    vat_amount = sale_data.get("vat_amount", 0)
    if vat_amount > 0:
        receipt.append(f"VAT (16%): {' ' * 30} {currency_code} {vat_amount:.2f}")
    
    # Add discount if present
    discount = sale_data.get("discount_amount", 0)
    if discount > 0:
        receipt.append(f"Discount: {' ' * 30} {currency_code} {discount:.2f}")
    
    receipt.append("=" * 50)
    receipt.append(f"TOTAL: {' ' * 35} {currency_code} {sale_data['total']:.2f}")
    receipt.append("=" * 50)
    receipt.append(f"Payment Method: {sale_data['payment_method']}")
    receipt.append(f"Amount Paid: {currency_code} {sale_data['payment_received']:.2f}")
    if sale_data["change"] > 0:
        receipt.append(f"Change: {currency_code} {sale_data['change']:.2f}")
    
    receipt.append("")
    receipt.append("Thank you for your purchase!".center(50))
    receipt.append("=" * 50)
    
    return "\n".join(receipt)


def list_sales_with_search(
    start_date: str = None,
    end_date: str = None,
    search_term: str = None,
    limit: int = 100
) -> list[dict]:
    """List sales with optional date range and search filters."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        
        # Check if customers table exists
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        has_customers = 'customers' in tables
        
        # Select sales with user and customer info for easier display
        if has_customers:
            query = (
                "SELECT s.*, u.username AS username, c.name AS customer_name "
                "FROM sales s "
                "LEFT JOIN users u ON s.user_id = u.user_id "
                "LEFT JOIN customers c ON s.customer_id = c.customer_id "
                "WHERE 1=1"
            )
        else:
            query = (
                "SELECT s.*, u.username AS username, NULL AS customer_name "
                "FROM sales s "
                "LEFT JOIN users u ON s.user_id = u.user_id "
                "WHERE 1=1"
            )
        params = []
        
        if start_date:
            query += " AND s.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND s.date <= ?"
            params.append(end_date)
        
        # Search by sale_id, receipt_number, username, or customer name
        if search_term:
            try:
                search_id = int(search_term)
                query += " AND (s.sale_id = ? OR s.user_id = ?)"
                params.extend([search_id, search_id])
            except ValueError:
                # Try searching by receipt_number or username or customer name (case-insensitive)
                if has_customers:
                    query += " AND (UPPER(s.receipt_number) LIKE UPPER(?) OR UPPER(u.username) LIKE UPPER(?) OR UPPER(c.name) LIKE UPPER(?))"
                    params.extend([f"%{search_term}%"] * 3)
                else:
                    query += " AND (UPPER(s.receipt_number) LIKE UPPER(?) OR UPPER(u.username) LIKE UPPER(?))"
                    params.extend([f"%{search_term}%"] * 2)
        
        query += " ORDER BY s.date DESC, s.time DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_receipt_by_id(sale_id: int) -> str | None:
    """Get formatted receipt text by sale ID."""
    from utils.security import get_currency_code
    sale_data = get_sale_with_items(sale_id)
    if not sale_data:
        return None
    currency = get_currency_code()
    return format_receipt(sale_data, currency_code=currency)
