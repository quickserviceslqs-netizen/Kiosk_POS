"""Dashboard UI with visual widgets and charts."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from modules import dashboard
from utils.security import get_currency_code


class DashboardFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self._build_ui()
        self._refresh_data()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="📊 Dashboard", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="🔄 Refresh", command=self._refresh_data).pack(side=tk.RIGHT, padx=4)
        if self.on_home:
            ttk.Button(top, text="← Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)

        # Summary cards row
        cards_frame = ttk.Frame(self)
        cards_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 12))
        
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
        left_column.grid(row=2, column=0, sticky=tk.NSEW, padx=(0, 6))
        left_column.rowconfigure(0, weight=1)
        left_column.rowconfigure(1, weight=1)
        
        # Sales Trend Chart
        trend_frame = ttk.LabelFrame(left_column, text="📈 7-Day Sales Trend", padding=8)
        trend_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 6))
        self.trend_canvas = tk.Canvas(trend_frame, height=200, bg="white", highlightthickness=1, highlightbackground="gray")
        self.trend_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Top Products
        top_products_frame = ttk.LabelFrame(left_column, text="🏆 Top Products Today", padding=8)
        top_products_frame.grid(row=1, column=0, sticky=tk.NSEW)
        top_products_frame.rowconfigure(0, weight=1)
        
        self.top_products_tree = ttk.Treeview(
            top_products_frame,
            columns=("name", "qty", "revenue"),
            show="headings",
            height=5
        )
        self.top_products_tree.heading("name", text="Product")
        self.top_products_tree.heading("qty", text="Qty Sold")
        self.top_products_tree.heading("revenue", text="Revenue")
        self.top_products_tree.column("name", width=200)
        self.top_products_tree.column("qty", width=80)
        self.top_products_tree.column("revenue", width=100)
        self.top_products_tree.grid(row=0, column=0, sticky=tk.NSEW)
        
        scroll = ttk.Scrollbar(top_products_frame, orient=tk.VERTICAL, command=self.top_products_tree.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.top_products_tree.configure(yscroll=scroll.set)

        # Right column - Alerts and Recent Sales
        right_column = ttk.Frame(self)
        right_column.grid(row=2, column=1, sticky=tk.NSEW, padx=(6, 0))
        right_column.rowconfigure(0, weight=1)
        right_column.rowconfigure(1, weight=1)
        
        # Low Stock Alerts
        alerts_frame = ttk.LabelFrame(right_column, text="⚠ Low Stock Alerts", padding=8)
        alerts_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 6))
        alerts_frame.rowconfigure(0, weight=1)
        
        self.alerts_tree = ttk.Treeview(
            alerts_frame,
            columns=("name", "qty", "threshold"),
            show="headings",
            height=5
        )
        self.alerts_tree.heading("name", text="Item")
        self.alerts_tree.heading("qty", text="Stock")
        self.alerts_tree.heading("threshold", text="Threshold")
        self.alerts_tree.column("name", width=150)
        self.alerts_tree.column("qty", width=70)
        self.alerts_tree.column("threshold", width=80)
        self.alerts_tree.grid(row=0, column=0, sticky=tk.NSEW)
        
        scroll2 = ttk.Scrollbar(alerts_frame, orient=tk.VERTICAL, command=self.alerts_tree.yview)
        scroll2.grid(row=0, column=1, sticky=tk.NS)
        self.alerts_tree.configure(yscroll=scroll2.set)
        
        # Recent Sales
        recent_frame = ttk.LabelFrame(right_column, text="🕐 Recent Transactions", padding=8)
        recent_frame.grid(row=1, column=0, sticky=tk.NSEW)
        recent_frame.rowconfigure(0, weight=1)
        
        self.recent_tree = ttk.Treeview(
            recent_frame,
            columns=("id", "time", "items", "total"),
            show="headings",
            height=5
        )
        self.recent_tree.heading("id", text="Sale #")
        self.recent_tree.heading("time", text="Time")
        self.recent_tree.heading("items", text="Items")
        self.recent_tree.heading("total", text="Total")
        self.recent_tree.column("id", width=60)
        self.recent_tree.column("time", width=80)
        self.recent_tree.column("items", width=60)
        self.recent_tree.column("total", width=80)
        self.recent_tree.grid(row=0, column=0, sticky=tk.NSEW)
        
        scroll3 = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=self.recent_tree.yview)
        scroll3.grid(row=0, column=1, sticky=tk.NS)
        self.recent_tree.configure(yscroll=scroll3.set)

        # Empty-state label for alerts
        alerts_frame.rowconfigure(1, weight=0)
        self.alerts_empty = ttk.Label(alerts_frame, text="No low stock alerts 🎉", foreground="gray")
        self.alerts_empty.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

    def _create_summary_card(self, parent: tk.Widget, title: str, icon: str) -> ttk.Frame:
        """Create a summary statistics card."""
        card = ttk.LabelFrame(parent, text=f"{icon} {title}", padding=12)
        currency = get_currency_code()
        
        # Revenue label
        revenue_label = ttk.Label(card, text=f"{currency} 0.00", font=("Segoe UI", 18, "bold"), foreground="#2E7D32")
        revenue_label.pack()
        
        # Transactions label
        trans_label = ttk.Label(card, text="0 transactions", font=("Segoe UI", 10), foreground="gray")
        trans_label.pack()
        
        # Store labels for updating
        card.revenue_label = revenue_label
        card.trans_label = trans_label
        
        return card

    def _refresh_data(self) -> None:
        """Refresh all dashboard data."""
        currency = get_currency_code()
        
        # Update summary cards
        today = dashboard.get_today_summary()
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
        for product in dashboard.get_top_products(5):
            self.top_products_tree.insert("", tk.END, values=(
                product["name"],
                product["quantity_sold"],
                f"{currency} {product['revenue']:.2f}"
            ))
        
        # Update low stock alerts
        self.alerts_tree.delete(*self.alerts_tree.get_children())
        low_stock_items = dashboard.get_low_stock_items(10)
        if not low_stock_items:
            self.alerts_tree.insert("", tk.END, values=("None", "-", "-"), tags=("empty",))
        else:
            for item in low_stock_items:
                self.alerts_tree.insert("", tk.END, values=(
                    item["name"],
                    item["quantity"],
                    item.get("threshold", 10)
                ), tags=("critical" if item["quantity"] <= item.get("threshold", 10) / 2 else "warning",))
        self.alerts_tree.tag_configure("critical", foreground="red")
        self.alerts_tree.tag_configure("warning", foreground="orange")
        self.alerts_tree.tag_configure("empty", foreground="gray")
        
        # Update recent sales
        self.recent_tree.delete(*self.recent_tree.get_children())
        for sale in dashboard.get_recent_sales(10):
            self.recent_tree.insert("", tk.END, values=(
                sale.get("sale_code", f"#{sale['sale_id']}"),
                sale["time"],
                sale["items"],
                f"KSH {sale['total']:.2f}"
            ))
        
        # Update trend chart
        self._draw_trend_chart()

    def _draw_trend_chart(self) -> None:
        """Draw a simple bar chart for sales trend."""
        self.trend_canvas.delete("all")
        
        data = dashboard.get_sales_trend_data(7)
        if not data:
            return
        
        width = self.trend_canvas.winfo_width()
        height = self.trend_canvas.winfo_height()
        # If canvas not laid out yet, retry shortly so the chart appears on first load
        if width < 20 or height < 20:
            self.after(120, self._draw_trend_chart)
            return
        
        padding = 40
        
        max_revenue = max([d["revenue"] for d in data]) or 1
        bar_width = (width - 2 * padding) / len(data)
        
        # Draw bars
        for i, day in enumerate(data):
            x1 = padding + i * bar_width
            bar_height = (day["revenue"] / max_revenue) * (height - 2 * padding) if max_revenue > 0 else 0
            y1 = height - padding - bar_height
            x2 = x1 + bar_width - 4
            y2 = height - padding
            
            # Bar
            color = "#4CAF50" if day["revenue"] > 0 else "#E0E0E0"
            self.trend_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)
            
            # Date label
            date_label = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%m/%d")
            self.trend_canvas.create_text(
                x1 + bar_width/2 - 2,
                height - padding + 15,
                text=date_label,
                font=("Segoe UI", 8)
            )
            
            # Revenue label on bar
            if day["revenue"] > 0:
                self.trend_canvas.create_text(
                    x1 + bar_width/2 - 2,
                    y1 - 10,
                    text=f"{day['revenue']:.0f}",
                    font=("Segoe UI", 8, "bold"),
                    fill="#2E7D32"
                )
