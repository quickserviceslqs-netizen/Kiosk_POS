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