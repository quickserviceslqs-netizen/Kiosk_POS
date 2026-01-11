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
        ttk.Radiobutton(controls, text="Transactions", variable=self.report_type, value="transactions").grid(row=0, column=6, padx=4)
        ttk.Radiobutton(controls, text="Payment Methods", variable=self.report_type, value="payment_methods").grid(row=0, column=7, padx=4)
        ttk.Radiobutton(controls, text="Trends", variable=self.report_type, value="trends").grid(row=0, column=8, padx=4)

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
            elif report_type == "transactions":
                self._show_transactions_report(start, end)
            elif report_type == "payment_methods":
                self._show_payment_methods_report(start, end)
            elif report_type == "trends":
                self._show_trends_report(start, end)
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

    def _show_transactions_report(self, start: str, end: str) -> None:
        """Show detailed sales transactions with line items."""
        currency_code = get_currency_code()
        transactions = reports.get_detailed_sales_transactions(start, end)
        
        output = f"DETAILED SALES TRANSACTIONS\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 100 + "\n\n"
        
        current_sale_id = None
        for transaction in transactions:
            if transaction['sale_id'] != current_sale_id:
                if current_sale_id is not None:
                    output += "\n"
                output += f"Receipt: {transaction['receipt_number']} | Date: {transaction['date']} {transaction['time']} | Total: {currency_code} {transaction['total']:.2f}\n"
                output += f"Payment: {currency_code} {transaction['payment']:.2f} ({transaction.get('payment_method', 'Cash')})\n"
                output += "-" * 80 + "\n"
                current_sale_id = transaction['sale_id']
            
            output += f"  {transaction['item_name']:<30} {transaction['category']:<15} Qty:{transaction['quantity']:<8} Price:{currency_code} {transaction['price']:<8.2f} Total:{currency_code} {transaction['line_total']:<8.2f}\n"
        
        if not transactions:
            output += "No transactions found in this period.\n"
        
        self.report_text.insert("1.0", output)

    def _show_payment_methods_report(self, start: str, end: str) -> None:
        """Show sales breakdown by payment method."""
        currency_code = get_currency_code()
        payment_data = reports.get_sales_by_payment_method(start, end)
        
        output = f"SALES BY PAYMENT METHOD\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 80 + "\n\n"
        output += f"{'Payment Method':<15} {'Transactions':<12} {'Total Sales':<15} {'Avg Sale':<12} {'Min Sale':<12} {'Max Sale':<12}\n"
        output += "-" * 80 + "\n"
        
        total_transactions = 0
        total_sales = 0
        
        for payment in payment_data:
            method = payment['payment_method']
            transactions = payment['transaction_count']
            sales = payment['total_sales']
            avg = payment['avg_transaction']
            min_sale = payment['min_transaction']
            max_sale = payment['max_transaction']
            
            output += f"{method:<15} {transactions:<12} {currency_code} {sales:<14.2f} {currency_code} {avg:<11.2f} {currency_code} {min_sale:<11.2f} {currency_code} {max_sale:<11.2f}\n"
            
            total_transactions += transactions
            total_sales += sales
        
        output += "-" * 80 + "\n"
        output += f"{'TOTAL':<15} {total_transactions:<12} {currency_code} {total_sales:<14.2f}\n"
        
        self.report_text.insert("1.0", output)

    def _show_trends_report(self, start: str, end: str) -> None:
        """Show sales performance trends over time."""
        currency_code = get_currency_code()
        trends = reports.get_sales_performance_trends(start, end, 'day')
        
        output = f"SALES PERFORMANCE TRENDS\n"
        output += f"Period: {start} to {end} (Daily)\n"
        output += "=" * 90 + "\n\n"
        output += f"{'Date':<12} {'Trans.':<8} {'Sales':<12} {'Avg Sale':<12} {'Subtotal':<12} {'VAT':<10} {'Discounts':<10}\n"
        output += "-" * 90 + "\n"
        
        for trend in trends:
            date = trend['period_label']
            transactions = trend['transactions']
            sales = trend['total_sales']
            avg_sale = trend['avg_sale']
            subtotal = trend['subtotal']
            vat = trend['total_vat']
            discounts = trend['total_discounts']
            
            output += f"{date:<12} {transactions:<8} {currency_code} {sales:<11.2f} {currency_code} {avg_sale:<11.2f} {currency_code} {subtotal:<11.2f} {currency_code} {vat:<9.2f} {currency_code} {discounts:<9.2f}\n"
        
        if not trends:
            output += "No sales data found in this period.\n"
        
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
            elif report_type == "transactions":
                self._show_transactions_report(start, end)
            elif report_type == "payment_methods":
                self._show_payment_methods_report(start, end)
            elif report_type == "trends":
                self._show_trends_report(start, end)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")

    def _download_report(self) -> None:
        """Download the current report as a text or CSV file."""
        content = self.report_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("No Report", "Please generate a report first")
            return
        
        # Determine report type from current selection
        report_type = self.report_type.get()
        start = self.start_date.get()
        end = self.end_date.get()
        
        filetypes = [("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        
        filename = filedialog.asksaveasfilename(
            title="Download Report",
            defaultextension=".csv",
            filetypes=filetypes,
        )
        if not filename:
            return
        
        try:
            if filename.endswith(".csv"):
                # Generate CSV from data
                csv_content = self._generate_csv_data(report_type, start, end)
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_content)
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
            messagebox.showinfo("Download", f"Report downloaded to {filename}")
        except Exception as exc:
            messagebox.showerror("Download Error", str(exc))

    def _generate_csv_data(self, report_type: str, start: str, end: str) -> str:
        """Generate CSV data from report data structures."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        try:
            if report_type == "daily":
                sales = reports.get_daily_sales(start)
                summary = reports.get_sales_summary(start, start)
                refunds = reports.get_refunds(start, start)
                
                # Write summary
                writer.writerow(["Daily Sales Report", start])
                writer.writerow([])
                writer.writerow(["Total Transactions", summary.get('total_transactions', 0) or 0])
                writer.writerow(["Total Sales", summary.get('total_sales', 0) or 0])
                writer.writerow(["Refunds Issued", len(refunds)])
                writer.writerow(["Refund Amount", sum(r['refund_amount'] for r in refunds)])
                writer.writerow(["Average Transaction", summary.get('avg_transaction', 0) or 0])
                writer.writerow([])
                
                # Write sales table
                writer.writerow(["Time", "Receipt Number", "Items", "Total"])
                for sale in sales:
                    receipt = sale.get('receipt_number', f"#{sale['sale_id']}")
                    writer.writerow([sale['time'], receipt, sale['item_count'], sale['total']])
                
                # Write refunds
                if refunds:
                    writer.writerow([])
                    writer.writerow(["Refunds"])
                    writer.writerow(["Time", "Refund Code", "Original Receipt", "Refund Amount"])
                    for r in refunds:
                        receipt = r.get('receipt_number', f"#{r['original_sale_id']}")
                        time_part = r['created_at'].split()[1] if ' ' in r['created_at'] else r['created_at']
                        writer.writerow([time_part, r.get('refund_code',''), receipt, r['refund_amount']])
                        
            elif report_type == "range":
                daily_sales = reports.get_date_range_sales(start, end)
                summary = reports.get_sales_summary(start, end)
                refunds = reports.get_refunds(start, end)
                
                writer.writerow(["Date Range Sales Report"])
                writer.writerow([f"Period: {start} to {end}"])
                writer.writerow([])
                writer.writerow(["Total Transactions", summary.get('total_transactions', 0) or 0])
                writer.writerow(["Total Sales", summary.get('total_sales', 0) or 0])
                writer.writerow(["Refunds Issued", len(refunds)])
                writer.writerow(["Refund Amount", sum(r['refund_amount'] for r in refunds)])
                writer.writerow(["Average Transaction", summary.get('avg_transaction', 0) or 0])
                writer.writerow([])
                
                writer.writerow(["Date", "Transactions", "Total Sales", "Average Sale"])
                for day in daily_sales:
                    writer.writerow([day['date'], day['transactions'], day['total_sales'], day['avg_sale']])
                
                if refunds:
                    writer.writerow([])
                    writer.writerow(["Refunds"])
                    writer.writerow(["Date", "Refund Code", "Original Receipt", "Refund Amount"])
                    for r in refunds:
                        date_part = r['created_at'].split()[0] if ' ' in r['created_at'] else r['created_at']
                        receipt = r.get('receipt_number', f"#{r['original_sale_id']}")
                        writer.writerow([date_part, r.get('refund_code',''), receipt, r['refund_amount']])
                        
            elif report_type == "bestsellers":
                items = reports.get_best_selling_items(start, end, limit=50)
                
                writer.writerow(["Best-Selling Items Report"])
                writer.writerow([f"Period: {start} to {end}"])
                writer.writerow([])
                writer.writerow(["Rank", "Item Name", "Category", "Quantity Sold", "Revenue", "Profit"])
                
                for idx, item in enumerate(items, 1):
                    cat = item.get('category') or 'N/A'
                    qty_display = item.get('qty_display', str(item.get('total_sold', 0)))
                    writer.writerow([idx, item['name'], cat, qty_display, item['revenue'], item.get('profit', 0) or 0])
                    
            elif report_type == "profit":
                analysis = reports.get_profit_analysis(start, end)
                
                writer.writerow(["Profit & Loss Analysis"])
                writer.writerow([f"Period: {start} to {end}"])
                writer.writerow([])
                writer.writerow(["Total Revenue", analysis.get('total_revenue', 0) or 0])
                writer.writerow(["Cost of Goods Sold", analysis.get('total_cost', 0) or 0])
                writer.writerow(["Gross Profit", analysis.get('gross_profit', 0) or 0])
                writer.writerow(["Total Expenses", analysis.get('total_expenses', 0) or 0])
                writer.writerow(["Net Profit", analysis.get('net_profit', 0) or 0])
                writer.writerow(["Profit Margin (%)", analysis.get('profit_margin', 0) or 0])
                
            elif report_type == "category":
                categories = reports.get_category_sales(start, end)
                
                writer.writerow(["Sales by Category Report"])
                writer.writerow([f"Period: {start} to {end}"])
                writer.writerow([])
                writer.writerow(["Category", "Items Sold", "Revenue", "Transactions"])
                
                for cat in categories:
                    writer.writerow([cat['category'], cat['total_quantity'], cat['total_revenue'], cat['transactions']])
                    
            elif report_type == "transactions":
                transactions = reports.get_detailed_sales_transactions(start, end)
                
                writer.writerow(["Detailed Sales Transactions"])
                writer.writerow([f"Period: {start} to {end}"])
                writer.writerow([])
                writer.writerow(["Receipt", "Date", "Time", "Item Name", "Category", "Quantity", "Price", "Line Total", "Sale Total", "Payment Method"])
                
                for transaction in transactions:
                    writer.writerow([
                        transaction['receipt_number'],
                        transaction['date'],
                        transaction['time'],
                        transaction['item_name'],
                        transaction['category'],
                        transaction['quantity'],
                        transaction['price'],
                        transaction['line_total'],
                        transaction['total'],
                        transaction.get('payment_method', 'Cash')
                    ])
                    
            elif report_type == "payment_methods":
                payment_data = reports.get_sales_by_payment_method(start, end)
                
                writer.writerow(["Sales by Payment Method"])
                writer.writerow([f"Period: {start} to {end}"])
                writer.writerow([])
                writer.writerow(["Payment Method", "Transactions", "Total Sales", "Avg Transaction", "Min Transaction", "Max Transaction"])
                
                for payment in payment_data:
                    writer.writerow([
                        payment['payment_method'],
                        payment['transaction_count'],
                        payment['total_sales'],
                        payment['avg_transaction'],
                        payment['min_transaction'],
                        payment['max_transaction']
                    ])
                    
            elif report_type == "trends":
                trends = reports.get_sales_performance_trends(start, end, 'day')
                
                writer.writerow(["Sales Performance Trends"])
                writer.writerow([f"Period: {start} to {end}"])
                writer.writerow([])
                writer.writerow(["Date", "Transactions", "Total Sales", "Avg Sale", "Subtotal", "VAT", "Discounts"])
                
                for trend in trends:
                    writer.writerow([
                        trend['period_label'],
                        trend['transactions'],
                        trend['total_sales'],
                        trend['avg_sale'],
                        trend['subtotal'],
                        trend['total_vat'],
                        trend['total_discounts']
                    ])
                    
        except Exception as e:
            writer.writerow(["Error generating CSV", str(e)])
        
        return output.getvalue()

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
