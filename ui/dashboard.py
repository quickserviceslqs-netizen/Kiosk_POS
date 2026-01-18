"""Dashboard UI with visual widgets and charts."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from modules import dashboard
from utils.security import get_currency_code


class DashboardFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(8, 8, 8, 12), **kwargs)
        self.on_home = on_home
        self._build_ui()
        self._refresh_data()

    def _build_ui(self) -> None:
        # Modern dashboard layout with clean structure
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)  # Header
        self.rowconfigure(1, weight=1)  # Main content
        self.grid_propagate(True)

        # Header section with title and summary cards
        self._build_header()

        # Main content area with analytics and data sections
        self._build_main_content()

        # Bind resize for responsive behavior
        self.bind("<Configure>", self._on_resize)
        self.after(150, self._on_resize_idle)

    def _build_header(self) -> None:
        """Build the header with title and summary cards."""
        header = ttk.Frame(self, style="Card.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 20))
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        # Title section
        title_frame = ttk.Frame(header)
        title_frame.grid(row=0, column=0, sticky=tk.W)
        ttk.Label(title_frame, text="📊 Dashboard", font=("Segoe UI", 18, "bold"),
                 foreground="#1976D2").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(title_frame, text="Real-time business insights",
                 font=("Segoe UI", 10), foreground="gray").pack(side=tk.LEFT)

        # Navigation
        if self.on_home:
            ttk.Button(header, text="← Home", command=self.on_home,
                      style="Accent.TButton").grid(row=0, column=1, sticky=tk.E)

        # Summary cards in a grid layout
        cards_container = ttk.Frame(header)
        cards_container.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(15, 0))
        cards_container.columnconfigure(0, weight=1)
        cards_container.columnconfigure(1, weight=1)
        cards_container.columnconfigure(2, weight=1)

        self.today_card = self._create_summary_card(cards_container, "TODAY", "💰")
        self.today_card.grid(row=0, column=0, padx=8, sticky=tk.EW)

        self.week_card = self._create_summary_card(cards_container, "THIS WEEK", "📅")
        self.week_card.grid(row=0, column=1, padx=8, sticky=tk.EW)

        self.month_card = self._create_summary_card(cards_container, "THIS MONTH", "📆")
        self.month_card.grid(row=0, column=2, padx=8, sticky=tk.EW)

    def _build_main_content(self) -> None:
        """Build the main content area with analytics and data sections."""
        main = ttk.Frame(self)
        main.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Analytics section (charts)
        analytics = self._build_analytics_section(main)
        analytics.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 10))

        # Data section (tables)
        data = self._build_data_section(main)
        data.grid(row=0, column=1, sticky=tk.NSEW, padx=(10, 0))

    def _build_analytics_section(self, parent) -> ttk.Frame:
        """Build the analytics section with compact summary and show more button."""
        section = ttk.LabelFrame(parent, text="📊 Analytics", padding=15)
        section.columnconfigure(0, weight=1)
        section.rowconfigure(0, weight=1)

        # Analytics summary card
        analytics_card = ttk.Frame(section, relief="raised", borderwidth=1)
        analytics_card.grid(row=0, column=0, sticky=tk.NSEW)
        analytics_card.columnconfigure(0, weight=1)
        analytics_card.rowconfigure(0, weight=0)
        analytics_card.rowconfigure(1, weight=1)
        analytics_card.rowconfigure(2, weight=0)

        ttk.Label(analytics_card, text="📊 Sales Analytics Summary",
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(5, 5), padx=10)

        # Summary content
        summary_frame = ttk.Frame(analytics_card)
        summary_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=10, pady=(0, 10))
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.columnconfigure(1, weight=1)
        summary_frame.columnconfigure(2, weight=1)

        # 7-day summary
        trend_summary = ttk.Frame(summary_frame)
        trend_summary.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 5))
        ttk.Label(trend_summary, text="7-Day Trend", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.trend_summary_label = ttk.Label(trend_summary, text="Loading...", font=("Segoe UI", 8))
        self.trend_summary_label.pack(anchor=tk.W)

        # Hourly summary
        hourly_summary = ttk.Frame(summary_frame)
        hourly_summary.grid(row=0, column=1, sticky=tk.NSEW, padx=(5, 5))
        ttk.Label(hourly_summary, text="Today's Hourly", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.hourly_summary_label = ttk.Label(hourly_summary, text="Loading...", font=("Segoe UI", 8))
        self.hourly_summary_label.pack(anchor=tk.W)

        # Expenses summary
        expenses_summary = ttk.Frame(summary_frame)
        expenses_summary.grid(row=0, column=2, sticky=tk.NSEW, padx=(5, 0))
        ttk.Label(expenses_summary, text="30-Day Expenses", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.expenses_summary_label = ttk.Label(expenses_summary, text="Loading...", font=("Segoe UI", 8))
        self.expenses_summary_label.pack(anchor=tk.W)

        # Chart buttons
        buttons_frame = ttk.Frame(analytics_card)
        buttons_frame.grid(row=2, column=0, pady=(0, 10), padx=10, sticky=tk.EW)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(2, weight=1)

        ttk.Button(buttons_frame, text="📈 Show Trend Chart", command=self._show_trend_chart_window,
                  style="Accent.TButton").grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        ttk.Button(buttons_frame, text="🕒 Show Hourly Chart", command=self._show_hourly_chart_window,
                  style="Accent.TButton").grid(row=0, column=1, sticky=tk.EW, padx=(5, 5))
        ttk.Button(buttons_frame, text="💰 Show Expenses Chart", command=self._show_expenses_chart_window,
                  style="Accent.TButton").grid(row=0, column=2, sticky=tk.EW, padx=(5, 0))

        return section

    def _build_data_section(self, parent) -> ttk.Frame:
        """Build the data section with compact tables and show more buttons."""
        section = ttk.LabelFrame(parent, text="📋 Data Overview", padding=15)
        section.columnconfigure(0, weight=1)
        section.rowconfigure(0, weight=1)
        section.rowconfigure(1, weight=1)
        section.rowconfigure(2, weight=1)

        # Top Products
        products_card = ttk.Frame(section, relief="raised", borderwidth=1)
        products_card.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 8))
        products_card.columnconfigure(0, weight=1)
        products_card.rowconfigure(0, weight=0)
        products_card.rowconfigure(1, weight=1)
        products_card.rowconfigure(2, weight=0)

        ttk.Label(products_card, text="🏆 Top Products Today",
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(5, 5), padx=10)

        products_frame = ttk.Frame(products_card)
        products_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=10, pady=(0, 5))
        products_frame.columnconfigure(0, weight=1)
        products_frame.rowconfigure(0, weight=1)

        self.top_products_tree = ttk.Treeview(
            products_frame,
            columns=("name", "qty", "revenue"),
            show="headings",
            height=3
        )
        self.top_products_tree.heading("name", text="Product")
        self.top_products_tree.heading("qty", text="Qty")
        self.top_products_tree.heading("revenue", text="Revenue")
        self.top_products_tree.column("name", width=200, minwidth=120, stretch=True)
        self.top_products_tree.column("qty", width=60, minwidth=50, stretch=True)
        self.top_products_tree.column("revenue", width=100, minwidth=80, stretch=True)
        self.top_products_tree.grid(row=0, column=0, sticky=tk.NSEW)

        ttk.Button(products_card, text="📋 Show All Products", command=self._show_top_products_window,
                  style="Accent.TButton").grid(row=2, column=0, pady=(0, 10), padx=10, sticky=tk.EW)

        # Low Stock Alerts
        alerts_card = ttk.Frame(section, relief="raised", borderwidth=1)
        alerts_card.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 8))
        alerts_card.columnconfigure(0, weight=1)
        alerts_card.rowconfigure(0, weight=0)
        alerts_card.rowconfigure(1, weight=1)
        alerts_card.rowconfigure(2, weight=0)

        ttk.Label(alerts_card, text="⚠️ Low Stock Alerts",
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(5, 5), padx=10)

        alerts_frame = ttk.Frame(alerts_card)
        alerts_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=10, pady=(0, 5))
        alerts_frame.columnconfigure(0, weight=1)
        alerts_frame.rowconfigure(0, weight=1)

        self.alerts_tree = ttk.Treeview(
            alerts_frame,
            columns=("name", "qty", "threshold"),
            show="headings",
            height=3
        )
        self.alerts_tree.heading("name", text="Item")
        self.alerts_tree.heading("qty", text="Stock")
        self.alerts_tree.heading("threshold", text="Threshold")
        self.alerts_tree.column("name", width=150, minwidth=100, stretch=True)
        self.alerts_tree.column("qty", width=60, minwidth=50, stretch=True)
        self.alerts_tree.column("threshold", width=80, minwidth=60, stretch=True)
        self.alerts_tree.grid(row=0, column=0, sticky=tk.NSEW)

        ttk.Button(alerts_card, text="⚠️ Show All Alerts", command=self._show_alerts_window,
                  style="Accent.TButton").grid(row=2, column=0, pady=(0, 10), padx=10, sticky=tk.EW)

        # Recent Transactions
        recent_card = ttk.Frame(section, relief="raised", borderwidth=1)
        recent_card.grid(row=2, column=0, sticky=tk.NSEW)
        recent_card.columnconfigure(0, weight=1)
        recent_card.rowconfigure(0, weight=0)
        recent_card.rowconfigure(1, weight=1)
        recent_card.rowconfigure(2, weight=0)

        ttk.Label(recent_card, text="🕐 Recent Transactions",
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(5, 5), padx=10)

        recent_frame = ttk.Frame(recent_card)
        recent_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=10, pady=(0, 5))
        recent_frame.columnconfigure(0, weight=1)
        recent_frame.rowconfigure(0, weight=1)

        self.recent_tree = ttk.Treeview(
            recent_frame,
            columns=("id", "time", "items", "total"),
            show="headings",
            height=3
        )
        self.recent_tree.heading("id", text="Receipt #")
        self.recent_tree.heading("time", text="Time")
        self.recent_tree.heading("items", text="Items")
        self.recent_tree.heading("total", text="Total")
        self.recent_tree.column("id", width=80, minwidth=60, stretch=True)
        self.recent_tree.column("time", width=100, minwidth=80, stretch=True)
        self.recent_tree.column("items", width=80, minwidth=60, stretch=True)
        self.recent_tree.column("total", width=100, minwidth=80, stretch=True)
        self.recent_tree.grid(row=0, column=0, sticky=tk.NSEW)

        ttk.Button(recent_card, text="🕐 Show All Transactions", command=self._show_recent_transactions_window,
                  style="Accent.TButton").grid(row=2, column=0, pady=(0, 10), padx=10, sticky=tk.EW)

        return section

    def _create_summary_card(self, parent: tk.Widget, title: str, icon: str) -> ttk.Frame:
        """Create a modern summary statistics card."""
        from utils.security import get_currency_code
        currency = get_currency_code()

        # Main card container with modern styling
        card = ttk.Frame(parent, relief="raised", borderwidth=2, style="Card.TFrame")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=0)
        card.rowconfigure(1, weight=1)

        # Header with icon and title
        header = ttk.Frame(card, style="CardHeader.TFrame")
        header.grid(row=0, column=0, sticky=tk.EW, padx=12, pady=(12, 8))
        ttk.Label(header, text=f"{icon} {title}", font=("Segoe UI", 10, "bold"),
                 foreground="#1976D2").pack(side=tk.LEFT)
        ttk.Separator(header, orient="horizontal").pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))

        # Content area
        content = ttk.Frame(card)
        content.grid(row=1, column=0, sticky=tk.NSEW, padx=12, pady=(0, 12))

        # Revenue display
        revenue_label = ttk.Label(content, text=f"{currency} 0.00",
                                 font=("Segoe UI", 20, "bold"), foreground="#2E7D32")
        revenue_label.pack(anchor=tk.W)

        # Transaction info
        trans_label = ttk.Label(content, text="0 transactions",
                               font=("Segoe UI", 9), foreground="gray")
        trans_label.pack(anchor=tk.W, pady=(4, 0))

        # Store references
        card.revenue_label = revenue_label
        card.trans_label = trans_label

        return card

    def _refresh_data(self) -> None:
        """Refresh all dashboard data."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            logger.info("Refreshing dashboard data")
            currency = get_currency_code()
            
            # Update summary cards
            today = dashboard.get_today_summary()
            logger.info(f"Today summary: {today}")
            if hasattr(self, 'today_card') and hasattr(self.today_card, 'revenue_label'):
                self.today_card.revenue_label.config(text=f"{currency} {today['revenue']:.2f}")
                self.today_card.trans_label.config(text=f"{today['transactions']} transactions | {today['items_sold']} items sold")
            
            week = dashboard.get_week_summary()
            if hasattr(self, 'week_card') and hasattr(self.week_card, 'revenue_label'):
                self.week_card.revenue_label.config(text=f"{currency} {week['revenue']:.2f}")
                self.week_card.trans_label.config(text=f"{week['transactions']} transactions")
            
            month = dashboard.get_month_summary()
            if hasattr(self, 'month_card') and hasattr(self.month_card, 'revenue_label'):
                self.month_card.revenue_label.config(text=f"{currency} {month['revenue']:.2f}")
                self.month_card.trans_label.config(text=f"{month['transactions']} transactions")
            
            # Update analytics summaries
            trend_data = dashboard.get_sales_trend_data(7)
            if trend_data:
                total_revenue = sum(d['revenue'] for d in trend_data)
                avg_daily = total_revenue / len(trend_data)
                self.trend_summary_label.config(text=f"Total: {currency} {total_revenue:.2f}\nAvg: {currency} {avg_daily:.2f}")
            else:
                self.trend_summary_label.config(text="No data")
            
            today_date = datetime.now().strftime("%Y-%m-%d")
            hourly_data = dashboard.get_hourly_sales_data(today_date)
            if hourly_data:
                total_revenue = sum(d['revenue'] for d in hourly_data)
                hours_with_sales = len([d for d in hourly_data if d['revenue'] > 0])
                self.hourly_summary_label.config(text=f"Total: {currency} {total_revenue:.2f}\nHours: {hours_with_sales}")
            else:
                self.hourly_summary_label.config(text="No data")
            
            # Update expenses summary
            expenses_summary = dashboard.get_expenses_summary(30)
            total_expenses = expenses_summary.get('total_expenses', 0) or 0
            expense_count = expenses_summary.get('expense_count', 0) or 0
            if total_expenses > 0:
                self.expenses_summary_label.config(text=f"Total: {currency} {total_expenses:.2f}\nCount: {expense_count}")
            else:
                self.expenses_summary_label.config(text="No expenses")
            
            # Update top products
            if hasattr(self, 'top_products_tree'):
                self.top_products_tree.delete(*self.top_products_tree.get_children())
                top_products = dashboard.get_top_products(3)
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
            if hasattr(self, 'alerts_tree'):
                self.alerts_tree.delete(*self.alerts_tree.get_children())
                low_stock_items = dashboard.get_low_stock_items(3)
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
            if hasattr(self, 'recent_tree'):
                self.recent_tree.delete(*self.recent_tree.get_children())
                recent_sales = dashboard.get_recent_sales(3)
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
            
            # Ensure treeview columns are sized to current layout
            self._adjust_tree_columns()
        
        except Exception as e:
            logger.error(f"Error refreshing dashboard data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Set fallback values
            try:
                if hasattr(self, 'today_card') and hasattr(self.today_card, 'revenue_label'):
                    self.today_card.revenue_label.config(text="Error loading data")
                    self.today_card.trans_label.config(text="Please check logs")
            except:
                pass

    def _draw_trend_chart(self) -> None:
        """Draw a bar chart for sales trend using Matplotlib."""
        from utils.security import get_currency_code
        currency = get_currency_code()
        
        data = dashboard.get_sales_trend_data(7)
        if not data:
            self.trend_ax.clear()
            self.trend_ax.set_facecolor('#ffffff')
            self.trend_ax.text(0.5, 0.5, "No sales data yet\n📊", ha='center', va='center', 
                             fontsize=14, color='#666666', fontweight='medium')
            self.trend_ax.set_xlim(0, 1)
            self.trend_ax.set_ylim(0, 1)
            self.trend_ax.axis('off')
            self.trend_figure.tight_layout(rect=[0.05, 0.25, 0.95, 0.95])
            self.trend_canvas.draw()
            return
        
        dates = [datetime.strptime(d["date"], "%Y-%m-%d").strftime("%m/%d") for d in data]
        revenues = [d["revenue"] for d in data]
        
        self.trend_ax.clear()
        bars = self.trend_ax.bar(dates, revenues, color='#1976D2', edgecolor='#0D47A1', width=0.6, alpha=0.8)
        self.trend_ax.set_title("7-Day Sales Trend", fontsize=10, fontweight='bold', pad=10)
        self.trend_ax.set_ylabel("Revenue", fontsize=8, fontweight='medium')
        self.trend_ax.tick_params(axis='both', which='major', labelsize=7)
        # Rotate x-axis labels and adjust spacing for better fit
        self.trend_ax.tick_params(axis='x', rotation=45, pad=8)
        
        # Add grid for better readability
        self.trend_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # Add value labels on top of bars
        for bar, revenue in zip(bars, revenues):
            height = bar.get_height()
            if height > 0:
                self.trend_ax.text(bar.get_x() + bar.get_width()/2., height + max(revenues) * 0.02,
                                 f'{currency} {revenue:.2f}', ha='center', va='bottom', 
                                 fontsize=6, fontweight='bold', color='#0D47A1')
        
        # Use tight layout for better spacing
        self.trend_figure.tight_layout(rect=[0.08, 0.15, 0.95, 0.9])
        self.trend_canvas.draw()

    def _draw_hourly_chart(self) -> None:
        """Draw a bar chart for today's hourly sales using Matplotlib."""
        from utils.security import get_currency_code
        currency = get_currency_code()
        
        today = datetime.now().strftime("%Y-%m-%d")
        data = dashboard.get_hourly_sales_data(today)
        if not data:
            self.hourly_ax.clear()
            self.hourly_ax.set_facecolor('#ffffff')
            self.hourly_ax.text(0.5, 0.5, "No sales data yet\n🕐", ha='center', va='center', 
                              fontsize=14, color='#666666', fontweight='medium')
            self.hourly_ax.set_xlim(0, 1)
            self.hourly_ax.set_ylim(0, 1)
            self.hourly_ax.axis('off')
            self.hourly_figure.tight_layout(rect=[0.05, 0.25, 0.95, 0.95])
            self.hourly_canvas.draw()
            return
        
        hours = [f"{int(d['hour']):02d}:00" for d in data]
        revenues = [d["revenue"] for d in data]
        
        self.hourly_ax.clear()
        bars = self.hourly_ax.bar(hours, revenues, color='#FF6B35', edgecolor='#E55A2B', width=0.6, alpha=0.8)
        self.hourly_ax.set_title("Today's Hourly Sales", fontsize=10, fontweight='bold', pad=10)
        self.hourly_ax.set_ylabel("Revenue", fontsize=8, fontweight='medium')
        self.hourly_ax.tick_params(axis='both', which='major', labelsize=7)
        # Rotate x-axis labels and adjust spacing for better fit
        self.hourly_ax.tick_params(axis='x', rotation=45, pad=8)
        
        # Add grid for better readability
        self.hourly_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # Add value labels on top of bars
        for bar, revenue in zip(bars, revenues):
            height = bar.get_height()
            if height > 0:
                self.hourly_ax.text(bar.get_x() + bar.get_width()/2., height + max(revenues) * 0.02,
                                  f'{currency} {revenue:.2f}', ha='center', va='bottom', 
                                  fontsize=6, fontweight='bold', color='#E55A2B')
        
        # Use tight layout for better spacing
        self.hourly_figure.tight_layout(rect=[0.08, 0.15, 0.95, 0.9])
        self.hourly_canvas.draw()

    # --- Responsive helpers ---
    def _on_resize(self, event):
        """Debounced configure handler to adjust layout on resize."""
        try:
            # Debounce frequent configure events
            if hasattr(self, '_resize_after_id'):
                self.after_cancel(self._resize_after_id)
            self._resize_after_id = self.after(120, self._on_resize_idle)
        except Exception:
            pass

    def _on_resize_idle(self):
        """Run layout adjustments: redraw charts with adjusted fonts and resize columns."""
        try:
            w = self.winfo_width() or 0
            h = self.winfo_height() or 0

            # Compact mode thresholds (tune as needed)
            compact = (h < 750) or (w < 1100)

            # Adjust treeview column widths
            self._adjust_tree_columns()
        except Exception:
            import traceback
            print('Resize handler error:', traceback.format_exc())

    def _adjust_tree_columns(self):
        """Dynamically size Treeview columns based on their frame widths."""
        try:
            # Top products columns
            if hasattr(self, 'top_products_tree'):
                frame = self.top_products_tree.master
                width = frame.winfo_width()
                if width and width > 60:
                    usable = max(80, width - 24)
                    self.top_products_tree.column('name', width=int(usable * 0.55))
                    self.top_products_tree.column('qty', width=int(usable * 0.2))
                    self.top_products_tree.column('revenue', width=int(usable * 0.25))

            # Alerts columns
            if hasattr(self, 'alerts_tree'):
                frame = self.alerts_tree.master
                width = frame.winfo_width()
                if width and width > 60:
                    usable = max(80, width - 24)
                    self.alerts_tree.column('name', width=int(usable * 0.6))
                    self.alerts_tree.column('qty', width=int(usable * 0.2))
                    self.alerts_tree.column('threshold', width=int(usable * 0.2))

            # Recent transactions columns
            if hasattr(self, 'recent_tree'):
                frame = self.recent_tree.master
                width = frame.winfo_width()
                if width and width > 60:
                    usable = max(100, width - 24)
                    self.recent_tree.column('id', width=int(usable * 0.15))
                    self.recent_tree.column('time', width=int(usable * 0.18))
                    self.recent_tree.column('items', width=int(usable * 0.47))
                    self.recent_tree.column('total', width=int(usable * 0.2))
        except Exception:
            pass

    def _show_analytics_window(self):
        """Open a window with full analytics charts."""
        window = tk.Toplevel(self)
        window.title("📊 Sales Analytics Charts")
        window.geometry("1400x900")
        window.resizable(True, True)
        
        # Set custom icon
        try:
            window.iconbitmap("assets/app_icon.ico")
        except:
            pass  # Fallback to default icon

        # Create main frame
        main_frame = ttk.Frame(window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 7-Day Trend Chart
        trend_frame = ttk.LabelFrame(main_frame, text="📈 7-Day Sales Trend", padding=10)
        trend_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        trend_figure = plt.Figure(figsize=(12, 6), dpi=100, facecolor='#ffffff')
        trend_ax = trend_figure.add_subplot(111)
        trend_ax.set_facecolor('#ffffff')
        trend_canvas = FigureCanvasTkAgg(trend_figure, master=trend_frame)
        trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Draw trend chart
        data = dashboard.get_sales_trend_data(7)
        currency = get_currency_code()
        if data:
            dates = [datetime.strptime(d["date"], "%Y-%m-%d").strftime("%m/%d") for d in data]
            revenues = [d["revenue"] for d in data]
            
            bars = trend_ax.bar(dates, revenues, color='#1976D2', edgecolor='#0D47A1', width=0.6, alpha=0.8)
            trend_ax.set_title("7-Day Sales Trend", fontsize=14, fontweight='bold', pad=15)
            trend_ax.set_ylabel("Revenue", fontsize=12, fontweight='medium')
            trend_ax.tick_params(axis='both', which='major', labelsize=10)
            trend_ax.tick_params(axis='x', rotation=45, pad=8)
            trend_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            
            for bar, revenue in zip(bars, revenues):
                height = bar.get_height()
                if height > 0:
                    trend_ax.text(bar.get_x() + bar.get_width()/2., height + max(revenues) * 0.02,
                                 f'{currency} {revenue:.2f}', ha='center', va='bottom', 
                                 fontsize=9, fontweight='bold', color='#0D47A1')
            
            trend_figure.tight_layout(rect=[0.08, 0.15, 0.95, 0.9])
            trend_canvas.draw()
        else:
            trend_ax.text(0.5, 0.5, "No sales data yet\n📊", ha='center', va='center', 
                         fontsize=16, color='#666666', fontweight='medium')
            trend_ax.set_xlim(0, 1)
            trend_ax.set_ylim(0, 1)
            trend_ax.axis('off')
            trend_figure.tight_layout(rect=[0.05, 0.25, 0.95, 0.95])
            trend_canvas.draw()

        # Hourly Sales Chart
        hourly_frame = ttk.LabelFrame(main_frame, text="🕒 Today's Hourly Sales", padding=10)
        hourly_frame.pack(fill=tk.BOTH, expand=True)

        hourly_figure = plt.Figure(figsize=(12, 6), dpi=100, facecolor='#ffffff')
        hourly_ax = hourly_figure.add_subplot(111)
        hourly_ax.set_facecolor('#ffffff')
        hourly_canvas = FigureCanvasTkAgg(hourly_figure, master=hourly_frame)
        hourly_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Draw hourly chart
        today = datetime.now().strftime("%Y-%m-%d")
        data = dashboard.get_hourly_sales_data(today)
        if data:
            hours = [f"{int(d['hour']):02d}:00" for d in data]
            revenues = [d["revenue"] for d in data]
            
            bars = hourly_ax.bar(hours, revenues, color='#FF6B35', edgecolor='#E55A2B', width=0.6, alpha=0.8)
            hourly_ax.set_title("Today's Hourly Sales", fontsize=14, fontweight='bold', pad=15)
            hourly_ax.set_ylabel("Revenue", fontsize=12, fontweight='medium')
            hourly_ax.tick_params(axis='both', which='major', labelsize=10)
            hourly_ax.tick_params(axis='x', rotation=45, pad=8)
            hourly_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            
            for bar, revenue in zip(bars, revenues):
                height = bar.get_height()
                if height > 0:
                    hourly_ax.text(bar.get_x() + bar.get_width()/2., height + max(revenues) * 0.02,
                                  f'{currency} {revenue:.2f}', ha='center', va='bottom', 
                                  fontsize=9, fontweight='bold', color='#E55A2B')
            
            hourly_figure.tight_layout(rect=[0.08, 0.15, 0.95, 0.9])
            hourly_canvas.draw()
        else:
            hourly_ax.text(0.5, 0.5, "No sales data yet\n🕐", ha='center', va='center', 
                          fontsize=16, color='#666666', fontweight='medium')
            hourly_ax.set_xlim(0, 1)
            hourly_ax.set_ylim(0, 1)
            hourly_ax.axis('off')
            hourly_figure.tight_layout(rect=[0.05, 0.25, 0.95, 0.95])
            hourly_canvas.draw()

    def _show_trend_chart_window(self):
        """Open a window with the 7-day sales trend chart."""
        window = tk.Toplevel(self)
        window.title("📈 7-Day Sales Trend Chart")
        window.geometry("1000x700")
        window.resizable(True, True)
        
        # Set custom icon
        try:
            window.iconbitmap("assets/app_icon.ico")
        except:
            pass  # Fallback to default icon

        # Create main frame
        main_frame = ttk.Frame(window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 7-Day Trend Chart
        trend_frame = ttk.LabelFrame(main_frame, text="📈 7-Day Sales Trend", padding=10)
        trend_frame.pack(fill=tk.BOTH, expand=True)

        trend_figure = plt.Figure(figsize=(10, 6), dpi=100, facecolor='#ffffff')
        trend_ax = trend_figure.add_subplot(111)
        trend_ax.set_facecolor('#ffffff')
        trend_canvas = FigureCanvasTkAgg(trend_figure, master=trend_frame)
        trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Draw trend chart
        data = dashboard.get_sales_trend_data(7)
        currency = get_currency_code()
        if data:
            dates = [datetime.strptime(d["date"], "%Y-%m-%d").strftime("%m/%d") for d in data]
            revenues = [d["revenue"] for d in data]
            
            bars = trend_ax.bar(dates, revenues, color='#1976D2', edgecolor='#0D47A1', width=0.6, alpha=0.8)
            trend_ax.set_title("7-Day Sales Trend", fontsize=14, fontweight='bold', pad=15)
            trend_ax.set_ylabel("Revenue", fontsize=12, fontweight='medium')
            trend_ax.tick_params(axis='both', which='major', labelsize=10)
            trend_ax.tick_params(axis='x', rotation=45, pad=8)
            trend_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            
            for bar, revenue in zip(bars, revenues):
                height = bar.get_height()
                if height > 0:
                    trend_ax.text(bar.get_x() + bar.get_width()/2., height + max(revenues) * 0.02,
                                 f'{currency} {revenue:.2f}', ha='center', va='bottom', 
                                 fontsize=9, fontweight='bold', color='#0D47A1')
            
            trend_figure.tight_layout(rect=[0.08, 0.15, 0.95, 0.9])
            trend_canvas.draw()
        else:
            trend_ax.text(0.5, 0.5, "No sales data yet\n📊", ha='center', va='center', 
                         fontsize=16, color='#666666', fontweight='medium')
            trend_ax.set_xlim(0, 1)
            trend_ax.set_ylim(0, 1)
            trend_ax.axis('off')
            trend_figure.tight_layout(rect=[0.05, 0.25, 0.95, 0.95])
            trend_canvas.draw()

    def _show_hourly_chart_window(self):
        """Open a window with today's hourly sales chart."""
        window = tk.Toplevel(self)
        window.title("🕒 Today's Hourly Sales Chart")
        window.geometry("1000x700")
        window.resizable(True, True)
        
        # Set custom icon
        try:
            window.iconbitmap("assets/app_icon.ico")
        except:
            pass  # Fallback to default icon

        # Create main frame
        main_frame = ttk.Frame(window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Hourly Sales Chart
        hourly_frame = ttk.LabelFrame(main_frame, text="🕒 Today's Hourly Sales", padding=10)
        hourly_frame.pack(fill=tk.BOTH, expand=True)

        hourly_figure = plt.Figure(figsize=(10, 6), dpi=100, facecolor='#ffffff')
        hourly_ax = hourly_figure.add_subplot(111)
        hourly_ax.set_facecolor('#ffffff')
        hourly_canvas = FigureCanvasTkAgg(hourly_figure, master=hourly_frame)
        hourly_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Draw hourly chart
        today = datetime.now().strftime("%Y-%m-%d")
        data = dashboard.get_hourly_sales_data(today)
        currency = get_currency_code()
        if data:
            hours = [f"{int(d['hour']):02d}:00" for d in data]
            revenues = [d["revenue"] for d in data]
            
            bars = hourly_ax.bar(hours, revenues, color='#FF6B35', edgecolor='#E55A2B', width=0.6, alpha=0.8)
            hourly_ax.set_title("Today's Hourly Sales", fontsize=14, fontweight='bold', pad=15)
            hourly_ax.set_ylabel("Revenue", fontsize=12, fontweight='medium')
            hourly_ax.tick_params(axis='both', which='major', labelsize=10)
            hourly_ax.tick_params(axis='x', rotation=45, pad=8)
            hourly_ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            
            for bar, revenue in zip(bars, revenues):
                height = bar.get_height()
                if height > 0:
                    hourly_ax.text(bar.get_x() + bar.get_width()/2., height + max(revenues) * 0.02,
                                  f'{currency} {revenue:.2f}', ha='center', va='bottom', 
                                  fontsize=9, fontweight='bold', color='#E55A2B')
            
            hourly_figure.tight_layout(rect=[0.08, 0.15, 0.95, 0.9])
            hourly_canvas.draw()
        else:
            hourly_ax.text(0.5, 0.5, "No sales data yet\n🕐", ha='center', va='center', 
                          fontsize=16, color='#666666', fontweight='medium')
            hourly_ax.set_xlim(0, 1)
            hourly_ax.set_ylim(0, 1)
            hourly_ax.axis('off')
            hourly_figure.tight_layout(rect=[0.05, 0.25, 0.95, 0.95])
            hourly_canvas.draw()

    def _show_expenses_chart_window(self):
        """Open a window with expenses pie chart."""
        window = tk.Toplevel(self)
        window.title("💰 Expenses by Category - Last 30 Days")
        window.geometry("1000x700")
        window.resizable(True, True)
        
        # Set custom icon
        try:
            window.iconbitmap("assets/app_icon.ico")
        except:
            pass  # Fallback to default icon

        # Create main frame
        main_frame = ttk.Frame(window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Expenses Pie Chart
        expenses_frame = ttk.LabelFrame(main_frame, text="💰 Expenses by Category (Last 30 Days)", padding=10)
        expenses_frame.pack(fill=tk.BOTH, expand=True)

        expenses_figure = plt.Figure(figsize=(10, 8), dpi=100, facecolor='#ffffff')
        expenses_ax = expenses_figure.add_subplot(111)
        expenses_ax.set_facecolor('#ffffff')
        expenses_canvas = FigureCanvasTkAgg(expenses_figure, master=expenses_frame)
        expenses_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Draw expenses pie chart
        data = dashboard.get_expenses_by_category(30)
        currency = get_currency_code()
        if data and any(d['total_amount'] > 0 for d in data):
            # Filter out zero amounts and prepare data
            filtered_data = [d for d in data if d['total_amount'] > 0]
            categories = [d['category'] for d in filtered_data]
            amounts = [d['total_amount'] for d in filtered_data]
            
            # Create a colorful pie chart
            colors = ['#FF6B35', '#F7931E', '#FFD23F', '#06FFA5', '#4ECDC4', 
                     '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF']
            
            # Explode the largest slice slightly
            explode = [0.1 if amt == max(amounts) else 0 for amt in amounts]
            
            wedges, texts, autotexts = expenses_ax.pie(
                amounts, 
                labels=categories, 
                autopct=lambda pct: f'{pct:.1f}%\n({currency} {pct/100*sum(amounts):.2f})',
                startangle=90,
                colors=colors[:len(amounts)],
                explode=explode,
                shadow=True,
                textprops={'fontsize': 10, 'fontweight': 'bold'}
            )
            
            expenses_ax.set_title("Expenses by Category", fontsize=16, fontweight='bold', pad=20)
            
            # Add legend with amounts
            legend_labels = [f"{cat}\n{currency} {amt:.2f}" for cat, amt in zip(categories, amounts)]
            expenses_ax.legend(wedges, legend_labels, title="Categories", 
                             loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)
            
            expenses_figure.tight_layout(rect=[0.1, 0.1, 0.75, 0.9])
            expenses_canvas.draw()
        else:
            expenses_ax.text(0.5, 0.5, "No expense data yet\n💰", ha='center', va='center', 
                           fontsize=16, color='#666666', fontweight='medium')
            expenses_ax.set_xlim(0, 1)
            expenses_ax.set_ylim(0, 1)
            expenses_ax.axis('off')
            expenses_figure.tight_layout(rect=[0.05, 0.25, 0.95, 0.95])
            expenses_canvas.draw()

    def _show_top_products_window(self):
        """Open a window with full top products list."""
        window = tk.Toplevel(self)
        window.title("🏆 Top Products - Full List")
        window.geometry("900x700")
        window.resizable(True, True)
        
        # Set custom icon
        try:
            window.iconbitmap("assets/app_icon.ico")
        except:
            pass  # Fallback to default icon

        frame = ttk.Frame(window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        ttk.Label(frame, text="Top Products Today", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        # Treeview
        tree = ttk.Treeview(frame, columns=("name", "qty", "revenue"), show="headings", height=20)
        tree.heading("name", text="Product")
        tree.heading("qty", text="Qty Sold")
        tree.heading("revenue", text="Revenue")
        tree.column("name", width=400, minwidth=200, stretch=True)
        tree.column("qty", width=150, minwidth=100, stretch=True)
        tree.column("revenue", width=200, minwidth=150, stretch=True)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate data
        currency = get_currency_code()
        top_products = dashboard.get_top_products(50)
        for i, product in enumerate(top_products):
            qty_display = product.get("qty_display", str(product.get("quantity_sold", 0)))
            tree.insert("", tk.END, values=(
                product["name"],
                qty_display,
                f"{currency} {product['revenue']:.2f}"
            ))
            tags = "even" if i % 2 == 0 else "odd"
            tree.item(tree.get_children()[-1], tags=(tags,))

        tree.tag_configure("even", background="#F8F9FA")
        tree.tag_configure("odd", background="#FFFFFF")

    def _show_alerts_window(self):
        """Open a window with full low stock alerts."""
        window = tk.Toplevel(self)
        window.title("⚠️ Low Stock Alerts - Full List")
        window.geometry("900x700")
        window.resizable(True, True)
        
        # Set custom icon
        try:
            window.iconbitmap("assets/app_icon.ico")
        except:
            pass  # Fallback to default icon

        frame = ttk.Frame(window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        ttk.Label(frame, text="Low Stock Alerts", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        # Treeview
        tree = ttk.Treeview(frame, columns=("name", "qty", "threshold"), show="headings", height=20)
        tree.heading("name", text="Item")
        tree.heading("qty", text="Current Stock")
        tree.heading("threshold", text="Threshold")
        tree.column("name", width=400, minwidth=200, stretch=True)
        tree.column("qty", width=200, minwidth=150, stretch=True)
        tree.column("threshold", width=200, minwidth=150, stretch=True)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate data
        low_stock_items = dashboard.get_low_stock_items(50)
        for i, item in enumerate(low_stock_items):
            actual = item.get("actual_volume", item["quantity"])
            threshold_val = item.get("threshold", 10)
            display_unit = item.get("display_unit", "units")
            
            if item.get("is_special_volume"):
                qty_display = f"{actual:.1f} {display_unit}"
                threshold_display = f"{threshold_val} {display_unit}"
            else:
                qty_display = f"{int(actual)}"
                threshold_display = f"{threshold_val}"
            
            tags = ["critical" if actual <= threshold_val / 2 else "warning"]
            if i % 2 == 0:
                tags.append("even")
            else:
                tags.append("odd")
            
            tree.insert("", tk.END, values=(
                item["name"],
                qty_display,
                threshold_display
            ), tags=tuple(tags))

        tree.tag_configure("critical", foreground="red", background="#FFEBEE")
        tree.tag_configure("warning", foreground="orange", background="#FFF3E0")
        tree.tag_configure("even", background="#F8F9FA")
        tree.tag_configure("odd", background="#FFFFFF")

    def _show_recent_transactions_window(self):
        """Open a window with full recent transactions."""
        window = tk.Toplevel(self)
        window.title("🕐 Recent Transactions - Full List")
        window.geometry("1000x700")
        window.resizable(True, True)
        
        # Set custom icon
        try:
            window.iconbitmap("assets/app_icon.ico")
        except:
            pass  # Fallback to default icon

        frame = ttk.Frame(window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        ttk.Label(frame, text="Recent Transactions", font=("Segoe UI", 14, "bold")).pack(pady=(0, 10))

        # Treeview
        tree = ttk.Treeview(frame, columns=("id", "time", "items", "total"), show="headings", height=20)
        tree.heading("id", text="Receipt #")
        tree.heading("time", text="Time")
        tree.heading("items", text="Items")
        tree.heading("total", text="Total")
        tree.column("id", width=150, minwidth=120, stretch=True)
        tree.column("time", width=150, minwidth=120, stretch=True)
        tree.column("items", width=200, minwidth=150, stretch=True)
        tree.column("total", width=150, minwidth=120, stretch=True)

        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate data
        currency = get_currency_code()
        recent_sales = dashboard.get_recent_sales(50)
        for i, txn in enumerate(recent_sales):
            tags = []
            if txn["type"] == "refund":
                tags.append("refund")
            if i % 2 == 0:
                tags.append("even")
            else:
                tags.append("odd")
            
            code = txn.get("code", f"#{txn['id']}")
            if txn["type"] == "refund":
                code = f"🔄 {code} (← {txn.get('original_receipt', '')})"
            
            tree.insert("", tk.END, values=(
                code,
                txn["time"],
                txn["items"],
                f"{currency} {abs(txn['amount']):.2f}"
            ), tags=tuple(tags))

        tree.tag_configure("refund", foreground="#D32F2F", background="#FFEBEE")
        tree.tag_configure("even", background="#F8F9FA")
        tree.tag_configure("odd", background="#FFFFFF")
