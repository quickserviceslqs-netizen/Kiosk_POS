"""Inventory report formatters for display."""

from .reports_base import TextReportFormatter


class InventoryStockLevelsTextFormatter(TextReportFormatter):
    """Text formatter for inventory stock levels report."""

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


class InventoryLowStockTextFormatter(TextReportFormatter):
    """Text formatter for low stock items report."""

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


class InventoryValueTextFormatter(TextReportFormatter):
    """Text formatter for inventory value report."""

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


class InventoryStockMovementTextFormatter(TextReportFormatter):
    """Text formatter for stock movement analysis report."""

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