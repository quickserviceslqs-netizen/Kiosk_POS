"""Dashboard UI with visual widgets and charts."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from modules import dashboard
from utils.security import get_currency_code


class DashboardFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(8, 8, 8, 12), **kwargs)
        self.on_home = on_home
        self._build_ui()
        self._refresh_data()

    def _build_ui(self) -> None:
        # Ensure dashboard grid stretches fully
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.grid_propagate(True)  # Allow frame to expand

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 12))
        ttk.Label(top, text="📊 Dashboard", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="← Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)

        # Summary cards row
        cards_frame = ttk.Frame(self)
        cards_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 16))
        
        # Today's Summary
        self.today_card = self._create_summary_card(cards_frame, "TODAY", "💰")
        self.today_card.pack(side=tk.LEFT, padx=4, fill=tk.BOTH, expand=True)
        
        # This Week
        self.week_card = self._create_summary_card(cards_frame, "THIS WEEK", "📅")
        self.week_card.pack(side=tk.LEFT, padx=4, fill=tk.BOTH, expand=True)
        
        # This Month
        self.month_card = self._create_summary_card(cards_frame, "THIS MONTH", "📆")
        self.month_card.pack(side=tk.LEFT, padx=4, fill=tk.BOTH, expand=True)

        # Left column - Charts and Top Products
        left_column = ttk.Frame(self)
        left_column.grid(row=2, column=0, sticky=tk.NSEW, padx=(0, 12))
        left_column.columnconfigure(0, weight=1)
        left_column.rowconfigure(0, weight=1)
        left_column.rowconfigure(1, weight=1)
        
        # Sales Trend Chart
        trend_frame = ttk.LabelFrame(left_column, text="📈 7-Day Sales Trend", padding=8)
        trend_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 12))
        self.trend_canvas = tk.Canvas(trend_frame, bg="#FAFAFA", highlightthickness=1, highlightbackground="#E0E0E0")
        self.trend_canvas.pack(fill=tk.BOTH, expand=True)
        # Redraw chart when the canvas is resized to avoid disappearing bars
        self.trend_canvas.bind("<Configure>", lambda _e: self._draw_trend_chart())
        
        # Top Products
        top_products_frame = ttk.LabelFrame(left_column, text="🏆 Top Products Today", padding=8)
        top_products_frame.grid(row=1, column=0, sticky=tk.NSEW)
        top_products_frame.rowconfigure(0, weight=1)
        top_products_frame.columnconfigure(0, weight=1)
        top_products_frame.columnconfigure(1, weight=0)
        
        self.top_products_tree = ttk.Treeview(
            top_products_frame,
            columns=("name", "qty", "revenue"),
            show="headings",
            height=8
        )
        self.top_products_tree.heading("name", text="Product")
        self.top_products_tree.heading("qty", text="Qty Sold")
        self.top_products_tree.heading("revenue", text="Revenue")
        self.top_products_tree.column("name", width=320, minwidth=160, stretch=True)
        self.top_products_tree.column("qty", width=100, minwidth=70, stretch=True)
        self.top_products_tree.column("revenue", width=140, minwidth=80, stretch=True)
        self.top_products_tree.grid(row=0, column=0, sticky=tk.NSEW)
        
        scroll = ttk.Scrollbar(top_products_frame, orient=tk.VERTICAL, command=self.top_products_tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.top_products_tree.configure(yscroll=scroll.set)

        # Right column - Alerts and Recent Sales
        right_column = ttk.Frame(self)
        right_column.grid(row=2, column=1, sticky=tk.NSEW, padx=(12, 0))
        right_column.columnconfigure(0, weight=1)
        right_column.rowconfigure(0, weight=1)
        right_column.rowconfigure(1, weight=1)
        
        # Low Stock Alerts
        alerts_frame = ttk.LabelFrame(right_column, text="⚠ Low Stock Alerts", padding=8)
        alerts_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 12))
        alerts_frame.rowconfigure(0, weight=1)
        alerts_frame.columnconfigure(0, weight=1)
        alerts_frame.columnconfigure(1, weight=0)
        
        self.alerts_tree = ttk.Treeview(
            alerts_frame,
            columns=("name", "qty", "threshold"),
            show="headings",
            height=8
        )
        self.alerts_tree.heading("name", text="Item")
        self.alerts_tree.heading("qty", text="Stock")
        self.alerts_tree.heading("threshold", text="Threshold")
        self.alerts_tree.column("name", width=220, minwidth=120, stretch=True)
        self.alerts_tree.column("qty", width=100, minwidth=60, stretch=True)
        self.alerts_tree.column("threshold", width=100, minwidth=60, stretch=True)
        self.alerts_tree.grid(row=0, column=0, sticky=tk.NSEW)
        
        scroll2 = ttk.Scrollbar(alerts_frame, orient=tk.VERTICAL, command=self.alerts_tree.yview)
        scroll2.grid(row=0, column=1, sticky=tk.NS)
        self.alerts_tree.configure(yscroll=scroll2.set)
        
        # Recent Sales
        recent_frame = ttk.LabelFrame(right_column, text="🕐 Recent Transactions", padding=8)
        recent_frame.grid(row=1, column=0, sticky=tk.NSEW)
        recent_frame.rowconfigure(0, weight=1)
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.columnconfigure(1, weight=0)
        
        self.recent_tree = ttk.Treeview(
            recent_frame,
            columns=("id", "time", "items", "total"),
            show="headings",
            height=8
        )
        self.recent_tree.heading("id", text="Receipt #")
        self.recent_tree.heading("time", text="Time")
        self.recent_tree.heading("items", text="Items")
        self.recent_tree.heading("total", text="Total")
        self.recent_tree.column("id", width=80, minwidth=60, stretch=True)
        self.recent_tree.column("time", width=120, minwidth=80, stretch=True)
        self.recent_tree.column("items", width=100, minwidth=60, stretch=True)
        self.recent_tree.column("total", width=120, minwidth=80, stretch=True)
        self.recent_tree.grid(row=0, column=0, sticky=tk.NSEW)
        
        scroll3 = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=self.recent_tree.yview)
        scroll3.grid(row=0, column=1, sticky=tk.NS)
        self.recent_tree.configure(yscroll=scroll3.set)

        # Empty-state label for alerts
        alerts_frame.rowconfigure(1, weight=0)
        self.alerts_empty = ttk.Label(alerts_frame, text="No low stock alerts 🎉", foreground="gray")
        self.alerts_empty.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        # Ensure summary cards and columns have proper grid weights so content expands
        # Keep layout flexible and responsive using grid column/row configure
        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(1, weight=1)
        cards_frame.columnconfigure(2, weight=1)
        left_column.columnconfigure(0, weight=1)
        left_column.rowconfigure(0, weight=1)
        left_column.rowconfigure(1, weight=1)
        right_column.columnconfigure(0, weight=1)
        right_column.rowconfigure(0, weight=1)
        right_column.rowconfigure(1, weight=1)

    def _create_summary_card(self, parent: tk.Widget, title: str, icon: str) -> ttk.Frame:
        """Create a summary statistics card."""
        card = ttk.Frame(parent, padding=12, relief="raised", borderwidth=2)
        
        # Title with icon
        title_label = ttk.Label(card, text=f"{icon} {title}", font=("Segoe UI", 12, "bold"), foreground="#1976D2")
        title_label.pack(anchor=tk.W)
        
        # Revenue label
        revenue_label = ttk.Label(card, text="KSH 0.00", font=("Segoe UI", 18, "bold"), foreground="#2E7D32")
        revenue_label.pack(pady=(8, 0))
        
        # Transactions label
        trans_label = ttk.Label(card, text="0 transactions", font=("Segoe UI", 10), foreground="gray")
        trans_label.pack()
        
        # Store labels for updating
        card.revenue_label = revenue_label
        card.trans_label = trans_label
        
        return card

    def _refresh_data(self) -> None:
        """Refresh all dashboard data."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Refreshing dashboard data")
        currency = get_currency_code()
        
        # Update summary cards
        today = dashboard.get_today_summary()
        logger.info(f"Today summary: {today}")
        self.today_card.revenue_label.config(text=f"{currency} {today['revenue']:.2f}")
        self.today_card.trans_label.config(text=f"{today['transactions']} transactions | {today['items_sold']} items sold")
        
        week = dashboard.get_week_summary()
        self.week_card.revenue_label.config(text=f"{currency} {week['revenue']:.2f}")
        self.week_card.trans_label.config(text=f"{week['transactions']} transactions")
        
        month = dashboard.get_month_summary()
        self.month_card.revenue_label.config(text=f"{currency} {month['revenue']:.2f}")
        self.month_card.trans_label.config(text=f"{month['transactions']} transactions")
        
        # Update top products
        self.top_products_tree.delete(*self.top_products_tree.get_children())
        top_products = dashboard.get_top_products(5)
        if not top_products:
            self.top_products_tree.insert("", tk.END, values=("No sales yet", "-", "-"), tags=("empty",))
        else:
            for i, product in enumerate(top_products):
                tags = []
                if i % 2 == 0:
                    tags.append("even")
                else:
                    tags.append("odd")
                # Use qty_display for proper unit formatting (e.g., "2.5 L" or "10")
                qty_display = product.get("qty_display", str(product.get("quantity_sold", 0)))
                self.top_products_tree.insert("", tk.END, values=(
                    product["name"],
                    qty_display,
                    f"{currency} {product['revenue']:.2f}"
                ), tags=tuple(tags))
        self.top_products_tree.tag_configure("even", background="#F8F9FA")
        self.top_products_tree.tag_configure("odd", background="#FFFFFF")
        self.top_products_tree.tag_configure("empty", foreground="gray", background="#F5F5F5")
        
        # Update low stock alerts
        self.alerts_tree.delete(*self.alerts_tree.get_children())
        low_stock_items = dashboard.get_low_stock_items(10)
        if not low_stock_items:
            self.alerts_tree.insert("", tk.END, values=("None", "-", "-"), tags=("empty",))
        else:
            for i, item in enumerate(low_stock_items):
                actual = item.get("actual_volume", item["quantity"])
                threshold_val = item.get("threshold", 10)
                display_unit = item.get("display_unit", "units")
                
                tags = ["critical" if actual <= threshold_val / 2 else "warning"]
                if i % 2 == 0:
                    tags.append("even")
                else:
                    tags.append("odd")
                
                # Format display with units for fractional items
                if item.get("is_special_volume"):
                    qty_display = f"{actual:.1f} {display_unit}"
                    threshold_display = f"{threshold_val} {display_unit}"
                else:
                    qty_display = f"{int(actual)}"
                    threshold_display = f"{threshold_val}"
                
                self.alerts_tree.insert("", tk.END, values=(
                    item["name"],
                    qty_display,
                    threshold_display
                ), tags=tuple(tags))
        self.alerts_tree.tag_configure("critical", foreground="red", background="#FFEBEE")
        self.alerts_tree.tag_configure("warning", foreground="orange", background="#FFF3E0")
        self.alerts_tree.tag_configure("empty", foreground="gray", background="#F5F5F5")
        self.alerts_tree.tag_configure("even", background="#F8F9FA")
        self.alerts_tree.tag_configure("odd", background="#FFFFFF")
        
        # Update recent sales
        self.recent_tree.delete(*self.recent_tree.get_children())
        recent_sales = dashboard.get_recent_sales(10)
        if not recent_sales:
            self.recent_tree.insert("", tk.END, values=("No transactions yet", "-", "-", "-"), tags=("empty",))
        else:
            for i, txn in enumerate(recent_sales):
                tags = []
                if txn["type"] == "refund":
                    tags.append("refund")
                if i % 2 == 0:
                    tags.append("even")
                else:
                    tags.append("odd")
                
                # Format display
                code = txn.get("code", f"#{txn['id']}")
                if txn["type"] == "refund":
                    code = f"🔄 {code} (← {txn.get('original_receipt', '')})"
                
                self.recent_tree.insert("", tk.END, values=(
                    code,
                    txn["time"],
                    txn["items"],
                    f"{currency} {abs(txn['amount']):.2f}"
                ), tags=tuple(tags))
        
        self.recent_tree.tag_configure("refund", foreground="#D32F2F", background="#FFEBEE")
        self.recent_tree.tag_configure("even", background="#F8F9FA")
        self.recent_tree.tag_configure("odd", background="#FFFFFF")
        self.recent_tree.tag_configure("empty", foreground="gray", background="#F5F5F5")
        
        # Update trend chart
        self._draw_trend_chart()

    def _draw_trend_chart(self) -> None:
        """Draw a simple bar chart for sales trend."""
        self.trend_canvas.delete("all")
        
        data = dashboard.get_sales_trend_data(7)
        if not data:
            # Draw "No data" message
            width = self.trend_canvas.winfo_width()
            height = self.trend_canvas.winfo_height()
            if width < 20 or height < 20:
                self.after(120, self._draw_trend_chart)
                return
            self.trend_canvas.create_text(width // 2, height // 2, text="No sales data yet", font=("Segoe UI", 12), fill="gray")
            return
        
        width = self.trend_canvas.winfo_width()
        height = self.trend_canvas.winfo_height()
        # If canvas not laid out yet, retry shortly so the chart appears on first load
        if width < 20 or height < 20:
            self.after(120, self._draw_trend_chart)
            return

        # padding proportional to width so chart looks good on wide screens
        padding = max(24, int(width * 0.06))
        
        max_revenue = max([d["revenue"] for d in data]) or 1
        bar_width = max(18, (width - 2 * padding) / max(1, len(data)))
        
        # Draw bars
        for i, day in enumerate(data):
            x1 = padding + i * bar_width
            bar_height = (day["revenue"] / max_revenue) * (height - 2 * padding) if max_revenue > 0 else 0
            y1 = height - padding - bar_height
            x2 = x1 + bar_width - 6
            y2 = height - padding
            
            # Bar with gradient effect
            color = "#4CAF50" if day["revenue"] > 0 else "#E0E0E0"
            self.trend_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#2E7D32", width=1)
            
            # Date label
            date_label = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%m/%d")
            self.trend_canvas.create_text(
                x1 + bar_width/2,
                height - padding + 12,
                text=date_label,
                font=("Segoe UI", 8)
            )
            
            # Revenue label on bar
            if day["revenue"] > 0 and (y2 - y1) > 16:
                self.trend_canvas.create_text(
                    x1 + bar_width/2,
                    y1 - 8,
                    text=f"{day['revenue']:.0f}",
                    font=("Segoe UI", 8, "bold"),
                    fill="#2E7D32"
                )

        # Add grid lines
        grid_color = "#E0E0E0"
        # Horizontal grid lines
        for i in range(1, 5):
            y = height - padding - (i * (height - 2 * padding) / 4)
            self.trend_canvas.create_line(padding, y, width - padding, y, fill=grid_color, width=1, dash=(2, 2))
            # Value labels
            value = max_revenue * i / 4 if max_revenue > 0 else 0
            self.trend_canvas.create_text(padding - 5, y, text=f"{value:.0f}", anchor=tk.E, font=("Segoe UI", 7), fill="gray")

        # If all values are zero, show placeholder text
        if all(d["revenue"] == 0 for d in data):
            self.trend_canvas.create_text(width//2, height//2, text="No sales data to display", font=("Segoe UI", 10), fill="gray")
