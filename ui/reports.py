"""Sales reporting UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from modules import reports


class ReportsFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_home=None, **kwargs):
        super().__init__(master, padding=(12, 12, 12, 20), **kwargs)
        self.on_home = on_home
        self.report_type = tk.StringVar(value="daily")
        self.start_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.end_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="Sales Reports", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="← Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)

        # Controls
        controls = ttk.Frame(self)
        controls.grid(row=1, column=0, sticky=tk.EW, pady=(0, 8))
        
        ttk.Label(controls, text="Report Type:").grid(row=0, column=0, padx=4, sticky=tk.W)
        ttk.Radiobutton(controls, text="Daily", variable=self.report_type, value="daily").grid(row=0, column=1, padx=4)
        ttk.Radiobutton(controls, text="Date Range", variable=self.report_type, value="range").grid(row=0, column=2, padx=4)
        ttk.Radiobutton(controls, text="Best Sellers", variable=self.report_type, value="bestsellers").grid(row=0, column=3, padx=4)
        ttk.Radiobutton(controls, text="Profit Analysis", variable=self.report_type, value="profit").grid(row=0, column=4, padx=4)
        ttk.Radiobutton(controls, text="By Category", variable=self.report_type, value="category").grid(row=0, column=5, padx=4)

        ttk.Label(controls, text="Start Date:").grid(row=1, column=0, padx=4, pady=(8, 0), sticky=tk.W)
        ttk.Entry(controls, textvariable=self.start_date, width=12).grid(row=1, column=1, padx=4, pady=(8, 0))
        
        ttk.Label(controls, text="End Date:").grid(row=1, column=2, padx=4, pady=(8, 0), sticky=tk.W)
        ttk.Entry(controls, textvariable=self.end_date, width=12).grid(row=1, column=3, padx=4, pady=(8, 0))
        
        ttk.Button(controls, text="Today", command=self._set_today).grid(row=1, column=4, padx=4, pady=(8, 0))
        ttk.Button(controls, text="This Week", command=self._set_this_week).grid(row=1, column=5, padx=4, pady=(8, 0))
        ttk.Button(controls, text="This Month", command=self._set_this_month).grid(row=1, column=6, padx=4, pady=(8, 0))
        ttk.Button(controls, text="Generate Report", command=self._generate_report).grid(row=1, column=7, padx=4, pady=(8, 0))

        # Report display area
        report_frame = ttk.Frame(self)
        report_frame.grid(row=2, column=0, sticky=tk.NSEW)
        report_frame.columnconfigure(0, weight=1)
        report_frame.rowconfigure(0, weight=1)

        self.report_text = tk.Text(report_frame, wrap=tk.WORD, font=("Courier", 10))
        self.report_text.grid(row=0, column=0, sticky=tk.NSEW)

        scroll = ttk.Scrollbar(report_frame, orient=tk.VERTICAL, command=self.report_text.yview)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        self.report_text.configure(yscroll=scroll.set)

    def _set_today(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        self.start_date.set(today)
        self.end_date.set(today)

    def _set_this_week(self) -> None:
        today = datetime.now()
        start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        self.start_date.set(start)
        self.end_date.set(end)

    def _set_this_month(self) -> None:
        today = datetime.now()
        start = today.replace(day=1).strftime("%Y-%m-%d")
        end = today.strftime("%Y-%m-%d")
        self.start_date.set(start)
        self.end_date.set(end)

    def _generate_report(self) -> None:
        self.report_text.delete("1.0", tk.END)
        
        report_type = self.report_type.get()
        start = self.start_date.get()
        end = self.end_date.get()

        try:
            if report_type == "daily":
                self._show_daily_report(start)
            elif report_type == "range":
                self._show_range_report(start, end)
            elif report_type == "bestsellers":
                self._show_bestsellers_report(start, end)
            elif report_type == "profit":
                self._show_profit_report(start, end)
            elif report_type == "category":
                self._show_category_report(start, end)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")

    def _show_daily_report(self, date: str) -> None:
        sales = reports.get_daily_sales(date)
        summary = reports.get_sales_summary(date, date)
        
        output = f"DAILY SALES REPORT - {date}\n"
        output += "=" * 60 + "\n\n"
        output += f"Total Transactions: {summary.get('total_transactions', 0) or 0}\n"
        output += f"Total Sales: {summary.get('total_sales', 0) or 0:.2f}\n"
        output += f"Average Transaction: {summary.get('avg_transaction', 0) or 0:.2f}\n"
        output += "\n" + "-" * 60 + "\n"
        output += f"{'Time':<12} {'Sale ID':<10} {'Items':<8} {'Total':<12}\n"
        output += "-" * 60 + "\n"
        
        for sale in sales:
            output += f"{sale['time']:<12} #{sale['sale_id']:<9} {sale['item_count']:<8} {sale['total']:<12.2f}\n"
        
        self.report_text.insert("1.0", output)

    def _show_range_report(self, start: str, end: str) -> None:
        daily_sales = reports.get_date_range_sales(start, end)
        summary = reports.get_sales_summary(start, end)
        
        output = f"DATE RANGE SALES REPORT\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 60 + "\n\n"
        output += f"Total Transactions: {summary.get('total_transactions', 0) or 0}\n"
        output += f"Total Sales: {summary.get('total_sales', 0) or 0:.2f}\n"
        output += f"Average Transaction: {summary.get('avg_transaction', 0) or 0:.2f}\n"
        output += "\n" + "-" * 60 + "\n"
        output += f"{'Date':<12} {'Trans.':<10} {'Total Sales':<15} {'Avg Sale':<12}\n"
        output += "-" * 60 + "\n"
        
        for day in daily_sales:
            output += f"{day['date']:<12} {day['transactions']:<10} {day['total_sales']:<15.2f} {day['avg_sale']:<12.2f}\n"
        
        self.report_text.insert("1.0", output)

    def _show_bestsellers_report(self, start: str, end: str) -> None:
        items = reports.get_best_selling_items(start, end, limit=20)
        
        output = f"BEST-SELLING ITEMS REPORT\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 80 + "\n\n"
        output += f"{'Rank':<6} {'Item Name':<25} {'Category':<15} {'Qty Sold':<10} {'Revenue':<12} {'Profit':<12}\n"
        output += "-" * 80 + "\n"
        
        for idx, item in enumerate(items, 1):
            cat = item.get('category') or 'N/A'
            output += f"{idx:<6} {item['name']:<25} {cat:<15} {item['total_sold']:<10} {item['revenue']:<12.2f} {item.get('profit', 0) or 0:<12.2f}\n"
        
        self.report_text.insert("1.0", output)

    def _show_profit_report(self, start: str, end: str) -> None:
        analysis = reports.get_profit_analysis(start, end)
        
        output = f"PROFIT & LOSS ANALYSIS\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 60 + "\n\n"
        output += f"Total Revenue:        {analysis.get('total_revenue', 0) or 0:>15.2f}\n"
        output += f"Cost of Goods Sold:   {analysis.get('total_cost', 0) or 0:>15.2f}\n"
        output += f"                      {'─' * 15}\n"
        output += f"Gross Profit:         {analysis.get('gross_profit', 0) or 0:>15.2f}\n\n"
        output += f"Total Expenses:       {analysis.get('total_expenses', 0) or 0:>15.2f}\n"
        output += f"                      {'─' * 15}\n"
        output += f"Net Profit:           {analysis.get('net_profit', 0) or 0:>15.2f}\n\n"
        output += f"Profit Margin:        {analysis.get('profit_margin', 0) or 0:>14.2f}%\n"
        
        self.report_text.insert("1.0", output)

    def _show_category_report(self, start: str, end: str) -> None:
        categories = reports.get_category_sales(start, end)
        
        output = f"SALES BY CATEGORY REPORT\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 70 + "\n\n"
        output += f"{'Category':<20} {'Quantity':<12} {'Revenue':<15} {'Transactions':<12}\n"
        output += "-" * 70 + "\n"
        
        for cat in categories:
            output += f"{cat['category']:<20} {cat['total_quantity']:<12} {cat['total_revenue']:<15.2f} {cat['transactions']:<12}\n"
        
        self.report_text.insert("1.0", output)
