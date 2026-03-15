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


class InventoryStockMovementGenerator(ReportGenerator):
    """Generate stock movement analysis report."""

    def generate_data(self) -> ReportData:
        """Generate stock movement data showing how items are selling."""
        try:
            from database.init_db import get_connection
            
            with get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

            # Build the WHERE clause for optional item filter
            # For now, we'll get all items, but we can add filtering later
            
            # Get detailed stock movement data
            cursor.execute("""
                SELECT 
                    i.item_id,
                    i.name,
                    i.category,
                    i.unit_of_measure as unit,
                    i.quantity as current_stock,
                    i.cost_price,
                    i.selling_price,
                    i.low_stock_threshold,
                    COALESCE(sales_data.total_sold, 0) as total_sold,
                    COALESCE(sales_data.sales_count, 0) as sales_transactions,
                    COALESCE(sales_data.total_revenue, 0) as total_revenue,
                    COALESCE(sales_data.avg_sale_qty, 0) as avg_sale_quantity,
                    sales_data.first_sale_date,
                    sales_data.last_sale_date
                FROM items i
                LEFT JOIN (
                    SELECT 
                        si.item_id,
                        SUM(si.quantity) as total_sold,
                        COUNT(DISTINCT si.sale_id) as sales_count,
                        SUM(si.quantity * si.price) as total_revenue,
                        AVG(si.quantity) as avg_sale_qty,
                        MIN(s.date) as first_sale_date,
                        MAX(s.date) as last_sale_date
                    FROM sales_items si
                    JOIN sales s ON si.sale_id = s.sale_id
                    WHERE s.date BETWEEN ? AND ?
                    GROUP BY si.item_id
                ) sales_data ON i.item_id = sales_data.item_id
                WHERE (sales_data.item_id IS NOT NULL OR 1=1)
                ORDER BY sales_data.total_sold DESC, i.name
            """, (self.start_date, self.end_date))

            rows = cursor.fetchall()

            # Process data
            data = []
            total_items = 0
            total_sold = 0
            total_revenue = 0
            items_with_movement = 0
            items_without_movement = 0
            
            for r in rows:
                item = dict(r)
                
                # Calculate additional metrics
                current_stock = item.get('current_stock') or 0
                sold_qty = item.get('total_sold') or 0
                
                # Calculate stock turnover rate (sold / average stock)
                # Estimate average stock as current + (sold/2) 
                estimated_avg_stock = current_stock + (sold_qty / 2) if sold_qty > 0 else current_stock  
                turnover_rate = sold_qty / estimated_avg_stock if estimated_avg_stock > 0 else 0
                
                # Calculate days between first and last sale
                days_active = 0
                velocity_per_day = 0
                if item['first_sale_date'] and item['last_sale_date']:
                    try:
                        first_date = datetime.strptime(item['first_sale_date'], '%Y-%m-%d')
                        last_date = datetime.strptime(item['last_sale_date'], '%Y-%m-%d')
                        days_active = (last_date - first_date).days + 1  # +1 to include both days
                        velocity_per_day = sold_qty / days_active if days_active > 0 else sold_qty
                    except:
                        days_active = 1
                        velocity_per_day = sold_qty
                elif sold_qty > 0:
                    # If sold but no date range, assume 1 day
                    days_active = 1
                    velocity_per_day = sold_qty
                
                # Stock status
                low_threshold = item.get('low_stock_threshold') or 0
                is_low_stock = low_threshold > 0 and current_stock <= low_threshold
                
                # Add calculated fields
                item.update({
                    'unit': item.get('unit') or 'pcs',
                    'category': item.get('category') or 'Uncategorized', 
                    'turnover_rate': round(turnover_rate, 2),
                    'days_active': days_active,
                    'velocity_per_day': round(velocity_per_day, 2),
                    'is_low_stock': is_low_stock,
                    'stock_status': 'Low Stock' if is_low_stock else ('No Movement' if sold_qty == 0 else 'Active')
                })
                
                data.append(item)
                total_items += 1
                total_sold += sold_qty
                total_revenue += item.get('total_revenue') or 0
                
                if sold_qty > 0:
                    items_with_movement += 1
                else:
                    items_without_movement += 1
            
            # Calculate period length for metadata
            period_days = 1
            try:
                start_dt = datetime.strptime(self.start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(self.end_date, '%Y-%m-%d')
                period_days = (end_dt - start_dt).days + 1
            except:
                period_days = 1
            
            metadata = {
                'total_items': total_items,
                'items_with_movement': items_with_movement,
                'items_without_movement': items_without_movement,
                'total_quantity_sold': total_sold,
                'total_revenue': total_revenue,
                'period_days': period_days,
                'avg_daily_movement': round(total_sold / period_days, 2) if period_days > 0 else 0,
                'currency_symbol': get_currency_symbol()
            }
            
            return ReportData('inventory_stock_movement', self.start_date, self.end_date, data, metadata)

        except Exception as e:
            return ReportData('inventory_stock_movement', self.start_date, self.end_date, [],
                            {'error': f'Failed to generate stock movement report: {str(e)}'})

    def get_formatter(self, report_data: ReportData) -> TextReportFormatter:
        """Get the formatter for stock movement report."""
        return InventoryStockMovementTextFormatter(report_data)


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


class InventoryStockMovementFormatter(TextReportFormatter):
    """Formatter for stock movement analysis report."""

    def _get_report_title(self) -> str:
        """Get the report title."""
        return "STOCK MOVEMENT ANALYSIS REPORT"

    def format_body(self) -> str:
        """Format the main report content."""
        if self.report_data.is_empty:
            return "No stock movement data found for the specified period."

        lines = []
        currency = self.report_data.currency_symbol

        # Summary section
        metadata = self.report_data.metadata
        lines.append("📈 MOVEMENT SUMMARY")
        lines.append("-" * 50)
        lines.append(f"Period Length: {metadata.get('period_days', 'N/A')} days")
        lines.append(f"Total Items Analyzed: {metadata.get('total_items', 'N/A')}")
        lines.append(f"Items With Movement: {metadata.get('items_with_movement', 'N/A')}")
        lines.append(f"Items Without Movement: {metadata.get('items_without_movement', 'N/A')}")
        lines.append(f"Total Quantity Sold: {metadata.get('total_quantity_sold', 'N/A'):,.0f}")
        lines.append(f"Total Revenue: {currency}{metadata.get('total_revenue', 0):,.2f}")
        lines.append(f"Average Daily Movement: {metadata.get('avg_daily_movement', 'N/A'):,.1f} items/day")
        lines.append("")

        # Table header
        lines.append("📦 DETAILED STOCK MOVEMENT")
        lines.append("-" * 110)
        header = f"{'Item Name':<25} {'Category':<15} {'Current':<8} {'Sold':<8} {'Sales':<6} {'Revenue':<12} {'Velocity':<9} {'Status':<12}"
        lines.append(header)
        lines.append(f"{'':>25} {'':>15} {'Stock':>8} {'Qty':>8} {'Count':>6} {'':>12} {'(per day)':>9} {'':>12}")
        lines.append("-" * 110)

        # Sort by total sold descending
        sorted_data = sorted(self.report_data.data, key=lambda x: x.get('total_sold', 0), reverse=True)

        for item in sorted_data:
            name = (item.get('name') or 'Unknown')[:24]
            category = (item.get('category') or 'N/A')[:14]
            current_stock = item.get('current_stock', 0)
            total_sold = item.get('total_sold', 0)
            sales_count = item.get('sales_transactions', 0)
            revenue = item.get('total_revenue', 0)
            velocity = item.get('velocity_per_day', 0)
            status = (item.get('stock_status') or 'Unknown')[:11]
            unit = item.get('unit', 'pcs')

            line = f"{name:<25} {category:<15} {current_stock:>6}{unit[:2]:<2} {total_sold:>8.0f} {sales_count:>6} {currency}{revenue:>11.2f} {velocity:>9.1f} {status:<12}"
            lines.append(line)

        # Additional analysis
        lines.append("")
        lines.append("📊 MOVEMENT ANALYSIS")
        lines.append("-" * 50)
        
        # Find top movers
        top_movers = sorted([item for item in self.report_data.data if item.get('total_sold', 0) > 0], 
                           key=lambda x: x.get('total_sold', 0), reverse=True)[:5]
        
        if top_movers:
            lines.append("🏆 TOP 5 MOVING ITEMS:")
            for i, item in enumerate(top_movers, 1):
                name = item.get('name', 'Unknown')
                sold = item.get('total_sold', 0)
                velocity = item.get('velocity_per_day', 0)
                lines.append(f"  {i}. {name} - {sold:.0f} sold ({velocity:.1f}/day)")
        
        # Find slow movers (items with stock but no sales)
        slow_movers = [item for item in self.report_data.data 
                      if item.get('current_stock', 0) > 0 and item.get('total_sold', 0) == 0]
        
        if slow_movers:
            lines.append("")
            lines.append(f"⚠️  SLOW MOVERS: {len(slow_movers)} items with stock but no sales")
            for item in slow_movers[:5]:  # Show first 5
                name = item.get('name', 'Unknown')
                stock = item.get('current_stock', 0)
                unit = item.get('unit', 'pcs')
                lines.append(f"  • {name} - {stock} {unit} in stock")
            if len(slow_movers) > 5:
                lines.append(f"  ... and {len(slow_movers) - 5} more")

        return "\n".join(lines)