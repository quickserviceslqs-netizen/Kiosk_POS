from __future__ import annotations
from utils.security import get_currency_code
from utils import set_window_icon
"""Sales reporting UI."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import tkcalendar

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
        self.grid_propagate(True)  # Allow frame to expand

        # Top bar
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        ttk.Label(top, text="Sales Reports", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        if self.on_home:
            ttk.Button(top, text="🏠 Home", command=self.on_home).pack(side=tk.RIGHT, padx=4)

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
        start_frame = ttk.Frame(controls)
        start_frame.grid(row=1, column=1, padx=4, pady=(8, 0), sticky=tk.W)
        ttk.Entry(start_frame, textvariable=self.start_date, width=12).pack(side=tk.LEFT)
        ttk.Button(start_frame, text="📅", width=2, command=self._pick_start_date).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(controls, text="End Date:").grid(row=1, column=2, padx=4, pady=(8, 0), sticky=tk.W)
        end_frame = ttk.Frame(controls)
        end_frame.grid(row=1, column=3, padx=4, pady=(8, 0), sticky=tk.W)
        ttk.Entry(end_frame, textvariable=self.end_date, width=12).pack(side=tk.LEFT)
        ttk.Button(end_frame, text="📅", width=2, command=self._pick_end_date).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(controls, text="Today", command=self._set_today).grid(row=1, column=4, padx=4, pady=(8, 0))
        ttk.Button(controls, text="This Week", command=self._set_this_week).grid(row=1, column=5, padx=4, pady=(8, 0))
        ttk.Button(controls, text="This Month", command=self._set_this_month).grid(row=1, column=6, padx=4, pady=(8, 0))
        ttk.Button(controls, text="Generate Report", command=self._generate_report).grid(row=1, column=7, padx=4, pady=(8, 0))
        ttk.Button(controls, text="📥 Download Report", command=self._download_report).grid(row=1, column=8, padx=4, pady=(8, 0))

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
        refunds = reports.get_refunds(date, date)
        currency_code = get_currency_code()

        output = f"DAILY SALES REPORT - {date}\n"
        output += "=" * 70 + "\n\n"
        output += f"Total Transactions: {summary.get('total_transactions', 0) or 0}\n"
        output += f"Total Sales: {currency_code} {summary.get('total_sales', 0) or 0:.2f}\n"
        output += f"Refunds Issued: {len(refunds)} | Amount: {currency_code} {sum(r['refund_amount'] for r in refunds):.2f}\n"
        output += f"Average Transaction: {summary.get('avg_transaction', 0) or 0:.2f}\n"
        output += "\n" + "-" * 70 + "\n"
        output += f"{'Time':<12} {'Receipt #':<20} {'Items':<8} {'Total':<12}".replace('Total', f'Total ({currency_code})') + "\n"
        output += "-" * 70 + "\n"
        
        for sale in sales:
            receipt = sale.get('receipt_number', f"#{sale['sale_id']}")
            output += f"{sale['time']:<12} {receipt:<20} {sale['item_count']:<8} {currency_code} {sale['total']:<12.2f}\n"

        # Refunds section
        output += "\n" + "REFUNDS" + "\n"
        output += "-" * 70 + "\n"
        if not refunds:
            output += "No refunds for this date.\n"
        else:
            output += f"{'Time':<12} {'Refund #':<20} {'Orig Receipt':<20} {'Refunded':<12}".replace('Refunded', f'Refunded ({currency_code})') + "\n"
            output += "-" * 70 + "\n"
            for r in refunds:
                receipt = r.get('receipt_number', f"#{r['original_sale_id']}")
                time_part = r['created_at'].split()[1] if ' ' in r['created_at'] else r['created_at']
                output += f"{time_part:<12} {r.get('refund_code',''):<20} {receipt:<20} {currency_code} {r['refund_amount']:<12.2f}\n"
        
        self.report_text.insert("1.0", output)

    def _show_range_report(self, start: str, end: str) -> None:
        currency_code = get_currency_code()
        daily_sales = reports.get_date_range_sales(start, end)
        summary = reports.get_sales_summary(start, end)
        refunds = reports.get_refunds(start, end)
        
        output = f"DATE RANGE SALES REPORT\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 60 + "\n\n"
        output += f"Total Transactions: {summary.get('total_transactions', 0) or 0}\n"
        output += f"Total Sales: {currency_code} {summary.get('total_sales', 0) or 0:.2f}\n"
        output += f"Refunds Issued: {len(refunds)} | Amount: {currency_code} {sum(r['refund_amount'] for r in refunds):.2f}\n"
        output += f"Average Transaction: {summary.get('avg_transaction', 0) or 0:.2f}\n"
        output += "\n" + "-" * 60 + "\n"
        output += f"{'Date':<12} {'Trans.':<10} {'Total Sales':<15} {'Avg Sale':<12}".replace('Total Sales', f'Total Sales ({currency_code})').replace('Avg Sale', f'Avg Sale ({currency_code})') + "\n"
        output += "-" * 60 + "\n"
        
        for day in daily_sales:
            output += f"{day['date']:<12} {day['transactions']:<10} {currency_code} {day['total_sales']:<15.2f} {currency_code} {day['avg_sale']:<12.2f}\n"

        # Refunds section
        output += "\n" + "REFUNDS" + "\n"
        output += "-" * 60 + "\n"
        if not refunds:
            output += "No refunds in this period.\n"
        else:
            output += f"{'Date':<12} {'Refund #':<18} {'Orig Receipt':<18} {'Refunded':<12}".replace('Refunded', f'Refunded ({currency_code})') + "\n"
            output += "-" * 60 + "\n"
            for r in refunds:
                date_part = r['created_at'].split()[0] if ' ' in r['created_at'] else r['created_at']
                receipt = r.get('receipt_number', f"#{r['original_sale_id']}")
                output += f"{date_part:<12} {r.get('refund_code',''):<18} {receipt:<18} {currency_code} {r['refund_amount']:<12.2f}\n"
        
        self.report_text.insert("1.0", output)

    def _show_bestsellers_report(self, start: str, end: str) -> None:
        currency_code = get_currency_code()
        items = reports.get_best_selling_items(start, end, limit=20)
        
        output = f"BEST-SELLING ITEMS REPORT\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 80 + "\n\n"
        output += f"{'Rank':<6} {'Item Name':<25} {'Category':<15} {'Qty Sold':<12} {'Revenue':<12} {'Profit':<12}\n"
        output += "-" * 80 + "\n"
        
        for idx, item in enumerate(items, 1):
            cat = item.get('category') or 'N/A'
            # Use qty_display for proper unit formatting (e.g., "2.5 L" or "10")
            qty_display = item.get('qty_display', str(item.get('total_sold', 0)))
            output += f"{idx:<6} {item['name']:<25} {cat:<15} {qty_display:<12} {currency_code} {item['revenue']:<12.2f} {currency_code} {item.get('profit', 0) or 0:<12.2f}\n"
        
        self.report_text.insert("1.0", output)

    def _show_profit_report(self, start: str, end: str) -> None:
        currency_code = get_currency_code()
        analysis = reports.get_profit_analysis(start, end)
        
        output = f"PROFIT & LOSS ANALYSIS\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 60 + "\n\n"
        output += f"Total Revenue:        {currency_code} {analysis.get('total_revenue', 0) or 0:>15.2f}\n"
        output += f"Cost of Goods Sold:   {currency_code} {analysis.get('total_cost', 0) or 0:>15.2f}\n"
        output += "\n"
        output += f"Gross Profit:         {currency_code} {analysis.get('gross_profit', 0) or 0:>15.2f}\n\n"
        output += f"Total Expenses:       {currency_code} {analysis.get('total_expenses', 0) or 0:>15.2f}\n"
        output += "\n"
        output += f"Net Profit:           {currency_code} {analysis.get('net_profit', 0) or 0:>15.2f}\n\n"
        output += f"Profit Margin:        {analysis.get('profit_margin', 0) or 0:>14.2f}%\n"
        
        self.report_text.insert("1.0", output)

    def _show_category_report(self, start: str, end: str) -> None:
        currency_code = get_currency_code()
        categories = reports.get_category_sales(start, end)
        
        output = f"SALES BY CATEGORY REPORT\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 70 + "\n\n"
        output += f"{'Category':<20} {'Items Sold':<12} {'Revenue':<15} {'Transactions':<12}\n"
        output += "-" * 70 + "\n"
        
        for cat in categories:
            qty = int(cat['total_quantity'])
            output += f"{cat['category']:<20} {qty:<12} {currency_code} {cat['total_revenue']:<15.2f} {cat['transactions']:<12}\n"
        
        self.report_text.insert("1.0", output)

    def refresh(self) -> None:
        currency_code = get_currency_code()
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

    def _download_report(self) -> None:
        """Download the current report as a text or CSV file."""
        content = self.report_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("No Report", "Please generate a report first")
            return
        
        # Determine if it's a tabular report (has headers like "Rank" or "Date")
        is_tabular = "Rank" in content or "Date" in content or "Item Name" in content
        
        filetypes = [("Text files", "*.txt")]
        defaultextension = ".txt"
        if is_tabular:
            filetypes.insert(0, ("CSV files", "*.csv"))
            defaultextension = ".csv"
        filetypes.append(("All files", "*.*"))
        
        filename = filedialog.asksaveasfilename(
            title="Download Report",
            defaultextension=defaultextension,
            filetypes=filetypes,
        )
        if not filename:
            return
        
        try:
            if filename.endswith(".csv") and is_tabular:
                # Convert text report to CSV
                csv_content = self._convert_to_csv(content)
                with open(filename, 'w', newline='') as f:
                    f.write(csv_content)
            else:
                with open(filename, 'w') as f:
                    f.write(content)
            messagebox.showinfo("Download", f"Report downloaded to {filename}")
        except Exception as exc:
            messagebox.showerror("Download Error", str(exc))

    def _convert_to_csv(self, text_content: str) -> str:
        """Convert text report to CSV format."""
        lines = text_content.split('\n')
        csv_lines = []
        in_table = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('=') or line.startswith('-'):
                continue
            if '|' in line or '\t' in line:
                # Assume table row
                parts = [p.strip() for p in line.replace('|', '\t').split('\t') if p.strip()]
                csv_lines.append(','.join(f'"{p}"' for p in parts))
                in_table = True
            elif in_table and line:
                # Header or data
                parts = line.split()
                if len(parts) > 1:
                    csv_lines.append(','.join(f'"{p}"' for p in parts))
        return '\n'.join(csv_lines)

    def _pick_start_date(self) -> None:
        """Open calendar picker for start date."""
        try:
            current = datetime.strptime(self.start_date.get(), "%Y-%m-%d")
        except ValueError:
            current = datetime.now()
        
        # Create a proper parent window instead of None
        root = self.winfo_toplevel()
        top = tk.Toplevel(root)
        top.title("Select Start Date")
        set_window_icon(top)
        top.geometry("350x350")
        top.resizable(False, False)
        # Make it modal - block interaction with main window until closed
        top.transient(root)
        top.grab_set()
        
        cal = tkcalendar.Calendar(
            top, 
            year=current.year, 
            month=current.month, 
            day=current.day,
            date_pattern="yyyy-mm-dd"
        )
        cal.pack(fill="both", expand=True, padx=10, pady=10)
        
        def on_select():
            selected = cal.get_date()
            self.start_date.set(selected)
            top.destroy()
        
        button_frame = ttk.Frame(top)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="OK", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=5)

    def _pick_end_date(self) -> None:
        """Open calendar picker for end date."""
        try:
            current = datetime.strptime(self.end_date.get(), "%Y-%m-%d")
        except ValueError:
            current = datetime.now()
        
        # Create a proper parent window instead of None
        root = self.winfo_toplevel()
        top = tk.Toplevel(root)
        set_window_icon(top)
        top.title("Select End Date")
        top.geometry("350x350")
        top.resizable(False, False)
        # Make it modal - block interaction with main window until closed
        top.transient(root)
        top.grab_set()
        
        cal = tkcalendar.Calendar(
            top, 
            year=current.year, 
            month=current.month, 
            day=current.day,
            date_pattern="yyyy-mm-dd"
        )
        cal.pack(fill="both", expand=True, padx=10, pady=10)
        
        def on_select():
            selected = cal.get_date()
            self.end_date.set(selected)
            top.destroy()
        
        button_frame = ttk.Frame(top)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="OK", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=top.destroy).pack(side=tk.LEFT, padx=5)
