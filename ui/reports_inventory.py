"""Inventory report generators for stock management and analysis."""

from typing import Dict, List, Any, Optional
import sqlite3
from datetime import datetime
from .reports_base import ReportGenerator, ReportData, TextReportFormatter, CSVReportFormatter
from utils.i18n import get_currency_symbol


class InventoryStockLevelsGenerator(ReportGenerator):
    """Generate current inventory stock levels report."""

    def generate_data(self) -> ReportData:
        """Generate current stock levels data."""
        try:
            conn = sqlite3.connect('database/pos.db')
            cursor = conn.cursor()

            # Get all items with their stock information
            cursor.execute("""
                SELECT
                    item_id,
                    name,
                    category,
                    quantity,
                    low_stock_threshold,
                    cost_price,
                    selling_price,
                    unit_of_measure,
                    created_at
                FROM items
                ORDER BY category, name
            """)

            items = cursor.fetchall()
            conn.close()

            # Process data
            data = []
            total_value = 0
            low_stock_count = 0

            for item in items:
                item_id, name, category, quantity, low_stock_threshold, cost_price, selling_price, unit, created_at = item

                # Calculate inventory value
                inventory_value = quantity * cost_price
                total_value += inventory_value

                # Check if low stock
                is_low_stock = quantity <= low_stock_threshold if low_stock_threshold else False
                if is_low_stock:
                    low_stock_count += 1

                data.append({
                    'item_id': item_id,
                    'name': name,
                    'category': category or 'Uncategorized',
                    'quantity': quantity,
                    'unit': unit or 'pcs',
                    'low_stock_threshold': low_stock_threshold,
                    'cost_price': cost_price,
                    'selling_price': selling_price,
                    'inventory_value': inventory_value,
                    'is_low_stock': is_low_stock,
                    'created_at': created_at
                })

            metadata = {
                'total_items': len(data),
                'total_value': total_value,
                'low_stock_count': low_stock_count,
                'currency_symbol': get_currency_symbol()
            }

            return ReportData('inventory_stock_levels', self.start_date, self.end_date, data, metadata)

        except Exception as e:
            return ReportData('inventory_stock_levels', self.start_date, self.end_date, [],
                            {'error': f'Failed to generate stock levels report: {str(e)}'})

    def fetch_page(self, page_size: int = 100, cursor: str | None = None, use_keyset: bool = False) -> tuple[list[dict], str | None, dict]:
        """Fetch a page of inventory items.

        Supports two modes:
          - offset pagination (default): cursor is an integer offset encoded as a string
          - keyset pagination (use_keyset=True): cursor is an opaque token 'key:category|name|item_id'

        Returns (rows, next_cursor, metadata).
        """
        try:
            conn = sqlite3.connect('database/pos.db')
            cursor_db = conn.cursor()

            # Total count for metadata
            cursor_db.execute("SELECT COUNT(*) FROM items")
            total = cursor_db.fetchone()[0]

            if use_keyset:
                # Keyset pagination: fetch page_size + 1 rows to detect `next_cursor`
                if cursor and cursor.startswith('key:'):
                    # parse last seen key
                    last = cursor[4:]
                    try:
                        last_cat, last_name, last_id = last.split('|', 2)
                        last_id = int(last_id)
                    except Exception:
                        last_cat = last_name = ''
                        last_id = 0

                    cursor_db.execute("""
                        SELECT
                            item_id,
                            name,
                            COALESCE(category, 'Uncategorized') as category,
                            quantity,
                            low_stock_threshold,
                            cost_price,
                            selling_price,
                            COALESCE(unit_of_measure, 'pcs') as unit_of_measure,
                            created_at
                        FROM items
                        WHERE (category > ?) OR (category = ? AND name > ?) OR (category = ? AND name = ? AND item_id > ?)
                        ORDER BY category, name, item_id
                        LIMIT ?
                    """, (last_cat, last_cat, last_name, last_cat, last_name, last_id, page_size + 1))
                else:
                    cursor_db.execute("""
                        SELECT
                            item_id,
                            name,
                            COALESCE(category, 'Uncategorized') as category,
                            quantity,
                            low_stock_threshold,
                            cost_price,
                            selling_price,
                            COALESCE(unit_of_measure, 'pcs') as unit_of_measure,
                            created_at
                        FROM items
                        ORDER BY category, name, item_id
                        LIMIT ?
                    """, (page_size + 1,))

                fetched = cursor_db.fetchall()
                has_more = len(fetched) > page_size
                page_rows = fetched[:page_size]

                rows = []
                for r in page_rows:
                    item_id, name, category, quantity, low_stock_threshold, cost_price, selling_price, unit, created_at = r
                    rows.append({
                        'item_id': item_id,
                        'name': name,
                        'category': category,
                        'quantity': quantity,
                        'unit': unit,
                        'low_stock_threshold': low_stock_threshold,
                        'cost_price': cost_price,
                        'selling_price': selling_price,
                        'inventory_value': quantity * cost_price,
                        'is_low_stock': quantity <= low_stock_threshold if low_stock_threshold else False,
                        'created_at': created_at
                    })

                conn.close()

                if has_more and rows:
                    last = rows[-1]
                    next_cursor = f"key:{last['category']}|{last['name']}|{last['item_id']}"
                else:
                    next_cursor = None

                metadata = {'total_items': total, 'page_size': page_size}
                return rows, next_cursor, metadata

            else:
                offset = int(cursor) if cursor else 0

                cursor_db.execute("""
                    SELECT
                        item_id,
                        name,
                        COALESCE(category, 'Uncategorized') as category,
                        quantity,
                        low_stock_threshold,
                        cost_price,
                        selling_price,
                        COALESCE(unit_of_measure, 'pcs') as unit_of_measure,
                        created_at
                    FROM items
                    ORDER BY category, name
                    LIMIT ? OFFSET ?
                """, (page_size, offset))

                rows = []
                for r in cursor_db.fetchall():
                    item_id, name, category, quantity, low_stock_threshold, cost_price, selling_price, unit, created_at = r
                    rows.append({
                        'item_id': item_id,
                        'name': name,
                        'category': category,
                        'quantity': quantity,
                        'unit': unit,
                        'low_stock_threshold': low_stock_threshold,
                        'cost_price': cost_price,
                        'selling_price': selling_price,
                        'inventory_value': quantity * cost_price,
                        'is_low_stock': quantity <= low_stock_threshold if low_stock_threshold else False,
                        'created_at': created_at
                    })

                conn.close()

                next_cursor = str(offset + len(rows)) if offset + len(rows) < total else None
                metadata = {'total_items': total, 'page_size': page_size}
                return rows, next_cursor, metadata

        except Exception as e:
            # Fall back to full generation if paging fails
            full = self.generate_data()
            offset = int(cursor) if cursor and cursor.isdigit() else 0
            rows = full.data[offset:offset + page_size]
            next_cursor = str(offset + len(rows)) if offset + len(rows) < len(full.data) else None
            metadata = {**full.metadata, 'total_items': len(full.data)}
            return rows, next_cursor, metadata

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get the formatter for stock levels report."""
        return InventoryStockLevelsFormatter(report_data)


class InventoryLowStockGenerator(ReportGenerator):
    """Generate low stock items report."""

    def generate_data(self) -> ReportData:
        """Generate low stock items data."""
        try:
            conn = sqlite3.connect('database/pos.db')
            cursor = conn.cursor()

            # Get items that are low on stock
            cursor.execute("""
                SELECT
                    item_id,
                    name,
                    category,
                    quantity,
                    low_stock_threshold,
                    cost_price,
                    selling_price,
                    unit_of_measure
                FROM items
                WHERE quantity <= low_stock_threshold AND low_stock_threshold > 0
                ORDER BY (low_stock_threshold - quantity) DESC, name
            """)

            items = cursor.fetchall()
            conn.close()

            # Process data
            data = []
            for item in items:
                item_id, name, category, quantity, low_stock_threshold, cost_price, selling_price, unit = item

                shortage = low_stock_threshold - quantity

                data.append({
                    'item_id': item_id,
                    'name': name,
                    'category': category or 'Uncategorized',
                    'current_stock': quantity,
                    'low_stock_threshold': low_stock_threshold,
                    'shortage': shortage,
                    'unit': unit or 'pcs',
                    'cost_price': cost_price,
                    'selling_price': selling_price,
                    'estimated_cost_to_restock': shortage * cost_price
                })

            metadata = {
                'low_stock_items': len(data),
                'currency_symbol': get_currency_symbol()
            }

            return ReportData('inventory_low_stock', self.start_date, self.end_date, data, metadata)

        except Exception as e:
            return ReportData('inventory_low_stock', self.start_date, self.end_date, [],
                            {'error': f'Failed to generate low stock report: {str(e)}'})

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get the formatter for low stock report."""
        return InventoryLowStockFormatter(report_data)


class InventoryValueGenerator(ReportGenerator):
    """Generate inventory value analysis report."""

    def generate_data(self) -> ReportData:
        """Generate inventory value data."""
        try:
            conn = sqlite3.connect('database/pos.db')
            cursor = conn.cursor()

            # Get inventory value by category
            cursor.execute("""
                SELECT
                    COALESCE(category, 'Uncategorized') as category,
                    COUNT(*) as item_count,
                    SUM(quantity) as total_quantity,
                    SUM(quantity * cost_price) as total_cost_value,
                    SUM(quantity * selling_price) as total_selling_value,
                    AVG(cost_price) as avg_cost_price,
                    AVG(selling_price) as avg_selling_price
                FROM items
                GROUP BY category
                ORDER BY total_cost_value DESC
            """)

            categories = cursor.fetchall()

            # Get overall totals
            cursor.execute("""
                SELECT
                    COUNT(*) as total_items,
                    SUM(quantity) as total_quantity,
                    SUM(quantity * cost_price) as total_cost_value,
                    SUM(quantity * selling_price) as total_selling_value
                FROM items
            """)

            totals = cursor.fetchone()
            conn.close()

            # Process category data
            data = []
            for category in categories:
                cat_name, item_count, total_qty, cost_value, selling_value, avg_cost, avg_selling = category

                data.append({
                    'category': cat_name,
                    'item_count': item_count,
                    'total_quantity': total_qty,
                    'total_cost_value': cost_value,
                    'total_selling_value': selling_value,
                    'avg_cost_price': avg_cost,
                    'avg_selling_price': avg_selling,
                    'potential_profit': selling_value - cost_value
                })

            metadata = {
                'total_items': totals[0],
                'total_quantity': totals[1],
                'total_cost_value': totals[2],
                'total_selling_value': totals[3],
                'total_categories': len(data),
                'currency_symbol': get_currency_symbol()
            }

            return ReportData('inventory_value', self.start_date, self.end_date, data, metadata)

        except Exception as e:
            return ReportData('inventory_value', self.start_date, self.end_date, [],
                            {'error': f'Failed to generate inventory value report: {str(e)}'})

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get the formatter for inventory value report."""
        return InventoryValueFormatter(report_data)


# Formatter classes

class InventoryStockLevelsFormatter(TextReportFormatter):
    """Formatter for inventory stock levels report."""

    def _get_report_title(self) -> str:
        """Get the report title."""
        return "INVENTORY STOCK LEVELS REPORT"

    def format_body(self) -> str:
        """Format the main report content."""
        if self.report_data.is_empty:
            return "No inventory items found."

        lines = []
        currency = self.report_data.currency_symbol

        # Summary
        metadata = self.report_data.metadata
        lines.append(f"Total Items: {metadata.get('total_items', 0)}")
        lines.append(f"Total Inventory Value: {currency}{metadata.get('total_value', 0):.2f}")
        lines.append(f"Low Stock Items: {metadata.get('low_stock_count', 0)}")
        lines.append("")

        # Table header
        header = f"{'Item Name':<30} {'Category':<20} {'Qty':<8} {'Unit':<6} {'Cost':<10} {'Sell':<10} {'Value':<12} {'Status':<8}"
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for item in self.report_data.data:
            low_stock_indicator = "LOW" if item['is_low_stock'] else ""
            line = f"{item['name'][:29]:<30} {item['category'][:19]:<20} {item['quantity']:<8} {item['unit'][:5]:<6} {currency}{item['cost_price']:<9.2f} {currency}{item['selling_price']:<9.2f} {currency}{item['inventory_value']:<11.2f} {low_stock_indicator:<8}"
            lines.append(line)

        return "\n".join(lines)


class InventoryLowStockFormatter(TextReportFormatter):
    """Formatter for low stock items report."""

    def _get_report_title(self) -> str:
        """Get the report title."""
        return "LOW STOCK ITEMS REPORT"

    def format_body(self) -> str:
        """Format the main report content."""
        if self.report_data.is_empty:
            return "No low stock items found."

        lines = []
        currency = self.report_data.currency_symbol

        # Summary
        metadata = self.report_data.metadata
        lines.append(f"Low Stock Items: {metadata.get('low_stock_items', 0)}")
        lines.append("")

        # Table header
        header = f"{'Item Name':<30} {'Category':<20} {'Current':<8} {'Min':<6} {'Shortage':<10} {'Unit':<6} {'Restock Cost':<14}"
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for item in self.report_data.data:
            line = f"{item['name'][:29]:<30} {item['category'][:19]:<20} {item['current_stock']:<8} {item['low_stock_threshold']:<6} {item['shortage']:<10} {item['unit'][:5]:<6} {currency}{item['estimated_cost_to_restock']:<13.2f}"
            lines.append(line)

        return "\n".join(lines)


class InventoryValueFormatter(TextReportFormatter):
    """Formatter for inventory value report."""

    def _get_report_title(self) -> str:
        """Get the report title."""
        return "INVENTORY VALUE ANALYSIS REPORT"

    def format_body(self) -> str:
        """Format the main report content."""
        if self.report_data.is_empty:
            return "No inventory data found."

        lines = []
        currency = self.report_data.currency_symbol

        # Summary
        metadata = self.report_data.metadata
        lines.append(f"Total Items: {metadata.get('total_items', 0)}")
        lines.append(f"Total Quantity: {metadata.get('total_quantity', 0)}")
        lines.append(f"Total Cost Value: {currency}{metadata.get('total_cost_value', 0):.2f}")
        lines.append(f"Total Selling Value: {currency}{metadata.get('total_selling_value', 0):.2f}")
        lines.append(f"Categories: {metadata.get('total_categories', 0)}")
        lines.append("")

        # Table header
        header = f"{'Category':<20} {'Items':<6} {'Qty':<8} {'Cost Value':<12} {'Sell Value':<12} {'Potential Profit':<16}"
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for item in self.report_data.data:
            line = f"{item['category'][:19]:<20} {item['item_count']:<6} {item['total_quantity']:<8} {currency}{item['total_cost_value']:<11.2f} {currency}{item['total_selling_value']:<11.2f} {currency}{item['potential_profit']:<15.2f}"
            lines.append(line)

        return "\n".join(lines)