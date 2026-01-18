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
        ttk.Radiobutton(controls, text="Voided Sales & Refunds", variable=self.report_type, value="voided").grid(row=0, column=9, padx=4)
        ttk.Radiobutton(controls, text="Sales Log", variable=self.report_type, value="sales_log").grid(row=0, column=10, padx=4)

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
            elif report_type == "voided":
                self._show_voided_report(start, end)
            elif report_type == "sales_log":
                self._show_sales_log_report(start, end)
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
        """Show detailed sales transactions with line items, including voided sales and refunds."""
        currency_code = get_currency_code()
        transactions = reports.get_detailed_sales_transactions(start, end)

        output = f"DETAILED SALES TRANSACTIONS (Including Voids & Refunds)\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 100 + "\n\n"

        current_sale_id = None
        current_transaction_type = None

        for transaction in transactions:
            transaction_type = transaction.get('transaction_type', 'sale')

            # Start new transaction block
            if transaction['sale_id'] != current_sale_id or transaction_type != current_transaction_type:
                if current_sale_id is not None:
                    output += "\n"

                # Determine transaction type label
                type_label = ""
                if transaction_type == 'void':
                    type_label = "[VOIDED] "
                elif transaction_type == 'refund':
                    type_label = "[REFUND] "

                output += f"{type_label}Receipt: {transaction['receipt_number']} | Date: {transaction['date']} {transaction['time']} | Total: {currency_code} {transaction['total']:.2f}\n"

                # Payment info (only for sales and voids)
                if transaction_type in ['sale', 'void']:
                    payment = transaction.get('payment')
                    payment_method = transaction.get('payment_method', 'Cash')
                    if payment is not None:
                        output += f"Payment: {currency_code} {payment:.2f} ({payment_method})\n"
                    else:
                        output += f"Payment: Not recorded ({payment_method})\n"

                # Void/refund reason
                if transaction_type == 'void' and transaction.get('void_reason'):
                    output += f"Void Reason: {transaction['void_reason']}\n"
                elif transaction_type == 'refund' and transaction.get('refund_reason'):
                    output += f"Refund Reason: {transaction['refund_reason']}\n"

                output += "-" * 80 + "\n"
                current_sale_id = transaction['sale_id']
                current_transaction_type = transaction_type

            # Item line (skip for refunds as they don't have detailed line items)
            if transaction_type != 'refund':
                output += f"  {transaction['item_name']:<30} {transaction['category']:<15} Qty:{transaction['quantity']:<8} Price:{currency_code} {transaction['price']:<8.2f} Total:{currency_code} {transaction['line_total']:<8.2f}\n"
            else:
                # For refunds, show the refund amount as a single line
                output += f"  Refund Amount: {currency_code} {transaction['refund_amount']:.2f}\n"

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

    def _show_voided_report(self, start: str, end: str) -> None:
        """Show comprehensive voided sales and refunds report."""
        currency_code = get_currency_code()
        comprehensive = reports.get_comprehensive_sales_summary(start, end)
        voided_sales = reports.get_voided_sales(start, end)
        voided_by_reason = reports.get_voided_sales_by_reason(start, end)
        refunds_by_reason = reports.get_refunds_by_reason(start, end)
        daily_voided = reports.get_daily_voided_and_refunds(start, end)
        
        output = f"VOIDED SALES & REFUNDS REPORT\n"
        output += f"Period: {start} to {end}\n"
        output += "=" * 80 + "\n\n"
        
        # Summary metrics
        output += "SUMMARY METRICS\n"
        output += "-" * 40 + "\n"
        output += f"Valid Transactions: {comprehensive.get('valid_transactions', 0)}\n"
        output += f"Valid Sales Amount: {currency_code} {comprehensive.get('valid_sales_amount', 0):.2f}\n"
        output += f"Avg Valid Transaction: {currency_code} {comprehensive.get('avg_valid_transaction', 0):.2f}\n"
        output += f"Voided Transactions: {comprehensive.get('voided_transactions', 0)}\n"
        output += f"Voided Amount: {currency_code} {comprehensive.get('voided_amount', 0):.2f}\n"
        output += f"Refund Count: {comprehensive.get('refund_count', 0)}\n"
        output += f"Total Refunded: {currency_code} {comprehensive.get('total_refunded', 0):.2f}\n"
        output += f"Net Sales: {currency_code} {comprehensive.get('net_sales', 0):.2f}\n"
        output += f"Total Gross Sales: {currency_code} {comprehensive.get('total_gross_sales', 0):.2f}\n\n"
        
        # Voided sales by reason
        if voided_by_reason:
            output += "VOIDED SALES BY REASON\n"
            output += "-" * 40 + "\n"
            output += f"{'Reason':<20} {'Count':<8} {'Total Amount':<15}\n"
            output += "-" * 40 + "\n"
            for reason in voided_by_reason:
                output += f"{reason['reason']:<20} {reason['count']:<8} {currency_code} {reason['total_amount']:<14.2f}\n"
            output += "\n"
        
        # Refunds by reason
        if refunds_by_reason:
            output += "REFUNDS BY REASON\n"
            output += "-" * 40 + "\n"
            output += f"{'Reason':<20} {'Count':<8} {'Total Amount':<15}\n"
            output += "-" * 40 + "\n"
            for reason in refunds_by_reason:
                output += f"{reason['reason']:<20} {reason['count']:<8} {currency_code} {reason['total_amount']:<14.2f}\n"
            output += "\n"
        
        # Daily breakdown
        if daily_voided:
            output += "DAILY BREAKDOWN\n"
            output += "-" * 40 + "\n"
            output += f"{'Date':<12} {'Voided':<8} {'Void Amt':<12} {'Refunds':<8} {'Ref Amt':<12}\n"
            output += "-" * 40 + "\n"
            for day in daily_voided:
                if day['voided_count'] > 0 or day['refund_count'] > 0:
                    output += f"{day['date']:<12} {day['voided_count']:<8} {currency_code} {day['voided_amount']:<11.2f} {day['refund_count']:<8} {currency_code} {day['refunded_amount']:<11.2f}\n"
            output += "\n"
        
        # Detailed voided sales
        if voided_sales:
            output += "DETAILED VOIDED SALES\n"
            output += "-" * 80 + "\n"
            output += f"{'Date':<12} {'Time':<10} {'Receipt #':<15} {'Items':<6} {'Amount':<12} {'Voided By':<15} {'Reason':<15}\n"
            output += "-" * 80 + "\n"
            for sale in voided_sales[:50]:  # Limit to 50 for readability
                receipt = sale.get('receipt_number', f"#{sale['sale_id']}")[:14]
                voided_by = sale.get('voided_by_username', 'Unknown')[:14]
                reason = sale.get('void_reason', 'N/A')[:14]
                output += f"{sale['date']:<12} {sale['time']:<10} {receipt:<15} {sale['item_count']:<6} {currency_code} {sale['total']:<11.2f} {voided_by:<15} {reason:<15}\n"
            
            if len(voided_sales) > 50:
                output += f"\n... and {len(voided_sales) - 50} more voided sales\n"
        
        if not voided_sales and not voided_by_reason and not refunds_by_reason:
            output += "No voided sales or refunds found in this period.\n"
        
        self.report_text.insert("1.0", output)

    def _show_sales_log_report(self, start: str, end: str) -> None:
        """Show comprehensive sales log with all transactions, refunds, and voids."""
        currency_code = get_currency_code()

        # Get total count for pagination info
        total_count = reports.get_sales_log_count(start, end)

        # Get paginated results (limit to reasonable amount for display)
        transactions = reports.get_comprehensive_sales_log(start, end, limit=200, offset=0)

        output = f"COMPREHENSIVE SALES LOG\n"
        output += f"Period: {start} to {end}\n"
        output += f"Total Transactions: {total_count}\n"
        output += "=" * 140 + "\n\n"

        output += f"{'Date':<12} {'Time':<10} {'Type':<8} {'Receipt/ID':<15} {'Amount':<12} {'Payment':<12} {'Change':<10} {'Method':<12} {'User':<15} {'Description':<30}\n"
        output += "-" * 140 + "\n"

        for transaction in transactions:
            date = transaction.get('date', '')[:10]  # Extract date part
            time_display = transaction.get('time_display', transaction.get('time', ''))[:8]  # Extract time part
            trans_type = (transaction.get('transaction_type') or 'unknown')[:7].upper()  # SALE, VOID, REFUND
            receipt_id = str(transaction.get('receipt_number', transaction.get('transaction_id', '')))[:14]
            amount = f"{currency_code} {transaction.get('amount', 0):.2f}"
            payment = f"{currency_code} {transaction.get('payment', 0):.2f}" if transaction.get('payment') else '-'
            change = f"{currency_code} {transaction.get('change', 0):.2f}" if transaction.get('change') else '-'
            method = (transaction.get('payment_method') or '-')[:11]
            user = (transaction.get('user_name') or 'Unknown')[:14]
            description = transaction.get('description', '')[:29]

            output += f"{date:<12} {time_display:<10} {trans_type:<8} {receipt_id:<15} {amount:<12} {payment:<12} {change:<10} {method:<12} {user:<15} {description:<30}\n"

            # Add additional details for sales transactions
            if transaction.get('transaction_type') == 'sale' and transaction.get('items_summary'):
                items = transaction['items_summary']
                if len(items) > 60:  # Truncate long item lists
                    items = items[:57] + "..."
                output += f"{'':<12} {'':<10} {'':<8} {'Items:':<15} {items}\n"

        if len(transactions) < total_count:
            output += f"\n... and {total_count - len(transactions)} more transactions (showing first 200)\n"

        if not transactions:
            output += "No transactions found in this period.\n"

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
            elif report_type == "voided":
                self._show_voided_report(start, end)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")

    def _download_report(self) -> None:
        """Download the current report as a text or CSV file with progress feedback for large datasets."""
        content = self.report_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("No Report", "Please generate a report first")
            return

        # Determine report type from current selection
        report_type = self.report_type.get()
        start = self.start_date.get()
        end = self.end_date.get()

        filetypes = [("CSV files", "*.csv"), ("Text files", "*.txt"), ("Excel files", "*.xlsx"), ("All files", "*.*")]

        filename = filedialog.asksaveasfilename(
            title="Download Report",
            defaultextension=".csv",
            filetypes=filetypes,
        )
        if not filename:
            return

        try:
            # Check if this is a potentially large dataset
            is_large_dataset = self._is_large_dataset(report_type, start, end)

            if is_large_dataset:
                # Show progress dialog for large exports
                progress_result = self._show_export_progress_dialog(report_type, start, end, filename)
                if progress_result:
                    messagebox.showinfo("Download", f"Report downloaded to {filename}")
                return

            # For smaller datasets, use the original method
            if filename.endswith(".csv"):
                # Generate CSV from data
                csv_content = self._generate_csv_data(report_type, start, end)
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_content)
            elif filename.endswith(".xlsx"):
                self._generate_excel_data(report_type, start, end, filename)
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

                writer.writerow(["Detailed Sales Transactions (Including Voids & Refunds)"])
                writer.writerow([f"Period: {start} to {end}"])
                writer.writerow([])

                # Create a single table with Sale Type column
                writer.writerow(["Sale Type", "Receipt", "Date", "Time", "Item Name", "Category", "Quantity", "Price", "Line Total", "Sale Total", "Payment", "Payment Method", "Void Reason", "Refund Reason"])

                for transaction in transactions:
                    # Determine sale type label
                    transaction_type = transaction.get('transaction_type', 'sale')
                    if transaction_type == 'sale':
                        sale_type = 'Regular Sale'
                    elif transaction_type == 'void':
                        sale_type = 'Voided Sale'
                    elif transaction_type == 'refund':
                        sale_type = 'Refund'
                    else:
                        sale_type = 'Unknown'

                    writer.writerow([
                        sale_type,
                        transaction['receipt_number'],
                        transaction['date'],
                        transaction['time'],
                        transaction['item_name'],
                        transaction['category'],
                        transaction['quantity'],
                        transaction['price'],
                        transaction['line_total'],
                        transaction['total'],
                        transaction.get('payment', ''),
                        transaction.get('payment_method', ''),
                        transaction.get('void_reason', ''),
                        transaction.get('refund_reason', '')
                    ])
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
        top.resizable(True, True)
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
        top.resizable(True, True)
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

    def _is_large_dataset(self, report_type: str, start: str, end: str) -> bool:
        """Determine if a dataset is large enough to warrant progress feedback."""
        try:
            # Check based on report type and date range
            if report_type in ["transactions", "voided"]:
                # For detailed transaction reports, check the estimated row count
                from datetime import datetime
                start_date = datetime.strptime(start, "%Y-%m-%d")
                end_date = datetime.strptime(end, "%Y-%m-%d")
                days_diff = (end_date - start_date).days + 1

                # Estimate based on historical data - assume 50 transactions per day as threshold
                if days_diff > 30:  # More than a month
                    return True
                elif days_diff > 7 and report_type == "transactions":  # More than a week for detailed transactions
                    return True

            elif report_type == "daily" and start != end:
                # Daily reports spanning multiple days
                from datetime import datetime
                start_date = datetime.strptime(start, "%Y-%m-%d")
                end_date = datetime.strptime(end, "%Y-%m-%d")
                days_diff = (end_date - start_date).days + 1
                if days_diff > 30:
                    return True

            return False
        except:
            return False

    def _show_export_progress_dialog(self, report_type: str, start: str, end: str, filename: str) -> bool:
        """Show a progress dialog for large dataset exports."""
        import threading
        import queue

        # Create progress dialog
        progress_window = tk.Toplevel(self)
        progress_window.title("Exporting Report")
        progress_window.geometry("400x150")
        progress_window.resizable(True, True)
        progress_window.transient(self.winfo_toplevel())
        progress_window.grab_set()
        set_window_icon(progress_window)

        # Center the dialog
        progress_window.geometry("+{}+{}".format(
            self.winfo_rootx() + self.winfo_width() // 2 - 200,
            self.winfo_rooty() + self.winfo_height() // 2 - 75
        ))

        ttk.Label(progress_window, text="Exporting report data...", font=("Segoe UI", 10)).pack(pady=(20, 10))
        progress_bar = ttk.Progressbar(progress_window, mode="indeterminate", length=300)
        progress_bar.pack(pady=(0, 10))
        progress_bar.start(10)

        status_label = ttk.Label(progress_window, text="Preparing export...")
        status_label.pack(pady=(0, 20))

        # Queue for communication between threads
        result_queue = queue.Queue()

        def export_worker():
            try:
                if filename.endswith(".xlsx"):
                    self._generate_excel_data_streaming(report_type, start, end, filename, status_label)
                else:
                    self._generate_csv_data_streaming(report_type, start, end, filename, status_label)
                result_queue.put(True)
            except Exception as e:
                result_queue.put(e)

        # Start export in background thread
        export_thread = threading.Thread(target=export_worker, daemon=True)
        export_thread.start()

        def check_result():
            try:
                result = result_queue.get_nowait()
                progress_window.destroy()
                if isinstance(result, Exception):
                    raise result
                return True
            except queue.Empty:
                # Still running, check again
                self.after(100, check_result)

        # Start checking for completion
        self.after(100, check_result)

        # Handle window close
        def on_close():
            if messagebox.askyesno("Cancel Export", "Are you sure you want to cancel the export?"):
                progress_window.destroy()

        progress_window.protocol("WM_DELETE_WINDOW", on_close)

        return True

    def _generate_csv_data_streaming(self, report_type: str, start: str, end: str, filename: str, status_label=None) -> None:
        """Generate CSV data with streaming for large datasets."""
        import csv

        def update_status(message: str):
            if status_label:
                status_label.config(text=message)
                status_label.update()

        update_status("Initializing export...")

        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            try:
                if report_type == "daily":
                    update_status("Fetching daily sales data...")
                    sales = reports.get_daily_sales(start)
                    summary = reports.get_sales_summary(start, start)
                    refunds = reports.get_refunds(start, start)
                    voided_sales = reports.get_voided_sales(start, start)

                    # Write summary
                    writer.writerow(["Daily Sales Report", start])
                    writer.writerow([])
                    writer.writerow(["Total Transactions", summary.get("total_transactions", 0) or 0])
                    writer.writerow(["Total Sales", summary.get("total_sales", 0) or 0])
                    writer.writerow(["Voided Sales", len(voided_sales)])
                    writer.writerow(["Voided Amount", sum(v["total"] for v in voided_sales)])
                    writer.writerow(["Refunds Issued", len(refunds)])
                    writer.writerow(["Refund Amount", sum(r["refund_amount"] for r in refunds)])
                    writer.writerow(["Net Sales", (summary.get("total_sales", 0) or 0) - sum(r["refund_amount"] for r in refunds)])
                    writer.writerow(["Average Transaction", summary.get("avg_transaction", 0) or 0])
                    writer.writerow([])

                    # Write sales table
                    writer.writerow(["Time", "Receipt Number", "Items", "Total"])
                    for sale in sales:
                        receipt = sale.get("receipt_number", f"#{sale['sale_id']}")
                        writer.writerow([sale["time"], receipt, sale["item_count"], sale["total"]])

                    # Write refunds
                    if refunds:
                        writer.writerow([])
                        writer.writerow(["Refunds"])
                        writer.writerow(["Time", "Refund Code", "Original Receipt", "Refund Amount"])
                        for r in refunds:
                            receipt = r.get("receipt_number", f"#{r['original_sale_id']}")
                            time_part = r["created_at"].split()[1] if " " in r["created_at"] else r["created_at"]
                            writer.writerow([time_part, r.get("refund_code",""), receipt, r["refund_amount"]])

                elif report_type == "range":
                    update_status("Fetching date range sales data...")
                    daily_sales = reports.get_date_range_sales(start, end)
                    summary = reports.get_sales_summary(start, end)
                    refunds = reports.get_refunds(start, end)
                    voided_sales = reports.get_voided_sales(start, end)

                    writer.writerow(["Date Range Sales Report"])
                    writer.writerow([f"Period: {start} to {end}"])
                    writer.writerow([])
                    writer.writerow(["Total Transactions", summary.get("total_transactions", 0) or 0])
                    writer.writerow(["Total Sales", summary.get("total_sales", 0) or 0])
                    writer.writerow(["Voided Sales", len(voided_sales)])
                    writer.writerow(["Voided Amount", sum(v["total"] for v in voided_sales)])
                    writer.writerow(["Refunds Issued", len(refunds)])
                    writer.writerow(["Refund Amount", sum(r["refund_amount"] for r in refunds)])
                    writer.writerow(["Net Sales", (summary.get("total_sales", 0) or 0) - sum(r["refund_amount"] for r in refunds)])
                    writer.writerow(["Average Transaction", summary.get("avg_transaction", 0) or 0])
                    writer.writerow([])

                    writer.writerow(["Date", "Transactions", "Total Sales", "Average Sale"])
                    for day in daily_sales:
                        writer.writerow([day["date"], day["transactions"], day["total_sales"], day["avg_sale"]])

                    if refunds:
                        writer.writerow([])
                        writer.writerow(["Refunds"])
                        writer.writerow(["Date", "Refund Code", "Original Receipt", "Refund Amount"])
                        for r in refunds:
                            date_part = r["created_at"].split()[0] if " " in r["created_at"] else r["created_at"]
                            receipt = r.get("receipt_number", f"#{r['original_sale_id']}")
                            writer.writerow([date_part, r.get("refund_code",""), receipt, r["refund_amount"]])

                elif report_type == "transactions":
                    update_status("Fetching detailed transactions...")
                    # Use batching for large transaction datasets
                    batch_size = 1000
                    offset = 0

                    writer.writerow(["Detailed Sales Transactions (Including Voids & Refunds)"])
                    writer.writerow([f"Period: {start} to {end}"])
                    writer.writerow([])

                    # Collect all transactions first
                    update_status("Collecting all transactions...")
                    all_transactions = []
                    temp_offset = 0
                    while True:
                        batch = reports.get_detailed_sales_transactions(start, end, limit=batch_size, offset=temp_offset)
                        if not batch:
                            break
                        all_transactions.extend(batch)
                        temp_offset += batch_size
                        if len(batch) < batch_size:
                            break

                    # Create a single table with Sale Type column
                    writer.writerow(["Sale Type", "Receipt", "Date", "Time", "Item Name", "Category", "Quantity", "Price", "Line Total", "Sale Total", "Payment", "Payment Method", "Void Reason", "Refund Reason"])

                    for transaction in all_transactions:
                        # Determine sale type label
                        transaction_type = transaction.get('transaction_type', 'sale')
                        if transaction_type == 'sale':
                            sale_type = 'Regular Sale'
                        elif transaction_type == 'void':
                            sale_type = 'Voided Sale'
                        elif transaction_type == 'refund':
                            sale_type = 'Refund'
                        else:
                            sale_type = 'Unknown'

                        writer.writerow([
                            sale_type,
                            transaction["receipt_number"],
                            transaction["date"],
                            transaction["time"],
                            transaction["item_name"],
                            transaction["category"],
                            transaction["quantity"],
                            transaction["price"],
                            transaction["line_total"],
                            transaction["total"],
                            transaction.get("payment", ""),
                            transaction.get("payment_method", ""),
                            transaction.get("void_reason", ""),
                            transaction.get("refund_reason", "")
                        ])

                elif report_type == "voided":
                    update_status("Fetching voided sales data...")
                    comprehensive = reports.get_comprehensive_sales_summary(start, end)
                    voided_sales = reports.get_voided_sales(start, end)
                    voided_by_reason = reports.get_voided_sales_by_reason(start, end)
                    refunds_by_reason = reports.get_refunds_by_reason(start, end)
                    daily_voided = reports.get_daily_voided_and_refunds(start, end)

                    writer.writerow(["Voided Sales & Refunds Report"])
                    writer.writerow([f"Period: {start} to {end}"])
                    writer.writerow([])

                    # Summary
                    writer.writerow(["Summary Metrics"])
                    writer.writerow(["Valid Transactions", comprehensive.get("valid_transactions", 0)])
                    writer.writerow(["Valid Sales Amount", comprehensive.get("valid_sales_amount", 0)])
                    writer.writerow(["Avg Valid Transaction", comprehensive.get("avg_valid_transaction", 0)])
                    writer.writerow(["Voided Transactions", comprehensive.get("voided_transactions", 0)])
                    writer.writerow(["Voided Amount", comprehensive.get("voided_amount", 0)])
                    writer.writerow(["Refund Count", comprehensive.get("refund_count", 0)])
                    writer.writerow(["Total Refunded", comprehensive.get("total_refunded", 0)])
                    writer.writerow(["Net Sales", comprehensive.get("net_sales", 0)])
                    writer.writerow(["Total Gross Sales", comprehensive.get("total_gross_sales", 0)])
                    writer.writerow([])

                    # Voided sales by reason
                    if voided_by_reason:
                        writer.writerow(["Voided Sales by Reason"])
                        writer.writerow(["Reason", "Count", "Total Amount"])
                        for reason in voided_by_reason:
                            writer.writerow([reason["reason"], reason["count"], reason["total_amount"]])
                        writer.writerow([])

                    # Refunds by reason
                    if refunds_by_reason:
                        writer.writerow(["Refunds by Reason"])
                        writer.writerow(["Reason", "Count", "Total Amount"])
                        for reason in refunds_by_reason:
                            writer.writerow([reason["reason"], reason["count"], reason["total_amount"]])
                        writer.writerow([])

                    # Daily breakdown
                    if daily_voided:
                        writer.writerow(["Daily Breakdown"])
                        writer.writerow(["Date", "Voided Count", "Voided Amount", "Refund Count", "Refunded Amount"])
                        for day in daily_voided:
                            if day["voided_count"] > 0 or day["refund_count"] > 0:
                                writer.writerow([
                                    day["date"],
                                    day["voided_count"],
                                    day["voided_amount"],
                                    day["refund_count"],
                                    day["refunded_amount"]
                                ])
                        writer.writerow([])

                    # Detailed voided sales (batched)
                    if voided_sales:
                        writer.writerow(["Detailed Voided Sales"])
                        writer.writerow(["Date", "Time", "Receipt Number", "Items", "Amount", "Voided By", "Reason"])

                        batch_size = 500
                        for i in range(0, len(voided_sales), batch_size):
                            update_status(f"Processing voided sales batch {(i // batch_size) + 1}...")
                            batch = voided_sales[i:i + batch_size]
                            for sale in batch:
                                receipt = sale.get("receipt_number", f"#{sale['sale_id']}")
                                voided_by = sale.get("voided_by_username", "Unknown")
                                reason = sale.get("void_reason", "N/A")
                                writer.writerow([
                                    sale["date"],
                                    sale["time"],
                                    receipt,
                                    sale["item_count"],
                                    sale["total"],
                                    voided_by,
                                    reason
                                ])

                update_status("Finalizing export...")

            except Exception as e:
                update_status(f"Error: {str(e)}")
                raise

    def _generate_excel_data(self, report_type: str, start: str, end: str, filename: str) -> None:
        """Generate Excel file for reports."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel export. Install with: pip install pandas openpyxl")

        try:
            if report_type == "daily":
                sales = reports.get_daily_sales(start)
                summary = reports.get_sales_summary(start, start)
                refunds = reports.get_refunds(start, start)
                voided_sales = reports.get_voided_sales(start, start)

                # Create summary DataFrame
                summary_data = {
                    "Metric": ["Total Transactions", "Total Sales", "Voided Sales", "Voided Amount", "Refunds Issued", "Refund Amount", "Net Sales", "Average Transaction"],
                    "Value": [
                        summary.get("total_transactions", 0) or 0,
                        summary.get("total_sales", 0) or 0,
                        len(voided_sales),
                        sum(v["total"] for v in voided_sales),
                        len(refunds),
                        sum(r["refund_amount"] for r in refunds),
                        (summary.get("total_sales", 0) or 0) - sum(r["refund_amount"] for r in refunds),
                        summary.get("avg_transaction", 0) or 0
                    ]
                }
                summary_df = pd.DataFrame(summary_data)

                # Create sales DataFrame
                sales_data = []
                for sale in sales:
                    receipt = sale.get("receipt_number", f"#{sale['sale_id']}")
                    sales_data.append({
                        "Time": sale["time"],
                        "Receipt Number": receipt,
                        "Items": sale["item_count"],
                        "Total": sale["total"]
                    })
                sales_df = pd.DataFrame(sales_data)

                with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                    summary_df.to_excel(writer, sheet_name="Summary", index=False)
                    sales_df.to_excel(writer, sheet_name="Sales", index=False)

                    if refunds:
                        refunds_data = []
                        for r in refunds:
                            receipt = r.get("receipt_number", f"#{r['original_sale_id']}")
                            time_part = r["created_at"].split()[1] if " " in r["created_at"] else r["created_at"]
                            refunds_data.append({
                                "Time": time_part,
                                "Refund Code": r.get("refund_code", ""),
                                "Original Receipt": receipt,
                                "Refund Amount": r["refund_amount"]
                            })
                        refunds_df = pd.DataFrame(refunds_data)
                        refunds_df.to_excel(writer, sheet_name="Refunds", index=False)

            elif report_type == "transactions":
                # For large transaction datasets, use chunked processing
                batch_size = 50000  # Excel can handle large datasets but we'll be conservative
                offset = 0
                all_transactions = []

                while True:
                    transactions = reports.get_detailed_sales_transactions(start, end, limit=batch_size, offset=offset)
                    if not transactions:
                        break
                    all_transactions.extend(transactions)
                    offset += batch_size
                    if len(transactions) < batch_size:
                        break

                # Create a single DataFrame with Sale Type column
                if all_transactions:
                    transactions_df = pd.DataFrame(all_transactions)

                    # Add Sale Type column
                    def get_sale_type(row):
                        transaction_type = row.get('transaction_type', 'sale')
                        if transaction_type == 'sale':
                            return 'Regular Sale'
                        elif transaction_type == 'void':
                            return 'Voided Sale'
                        elif transaction_type == 'refund':
                            return 'Refund'
                        else:
                            return 'Unknown'

                    transactions_df['Sale Type'] = transactions_df.apply(get_sale_type, axis=1)

                    # Reorder columns to put Sale Type first
                    cols = ['Sale Type', 'receipt_number', 'date', 'time', 'item_name', 'category', 'quantity', 'price', 'line_total', 'total', 'payment', 'payment_method', 'void_reason', 'refund_reason']
                    transactions_df = transactions_df[cols]

                    # Rename columns for better readability
                    transactions_df.columns = ['Sale Type', 'Receipt', 'Date', 'Time', 'Item Name', 'Category', 'Quantity', 'Price', 'Line Total', 'Sale Total', 'Payment', 'Payment Method', 'Void Reason', 'Refund Reason']

                    transactions_df.to_excel(filename, sheet_name="All Transactions", index=False)

            else:
                # For other report types, fall back to CSV-like approach
                csv_content = self._generate_csv_data(report_type, start, end)
                # Convert CSV to Excel
                from io import StringIO
                csv_io = StringIO(csv_content)
                df = pd.read_csv(csv_io)
                df.to_excel(filename, index=False)

        except ImportError:
            raise ImportError("Excel export requires pandas and openpyxl. Install with: pip install pandas openpyxl")

    def _generate_excel_data_streaming(self, report_type: str, start: str, end: str, filename: str, status_label=None) -> None:
        """Generate Excel data with streaming for very large datasets."""
        try:
            import pandas as pd
        except ImportError:
            # Fall back to CSV if pandas not available
            return self._generate_csv_data_streaming(report_type, start, end, filename, status_label)

        def update_status(message: str):
            if status_label:
                status_label.config(text=message)
                status_label.update()

        update_status("Preparing Excel export...")

        try:
            if report_type == "transactions":
                # For very large transaction datasets, process in chunks
                batch_size = 100000  # Large chunks for Excel
                offset = 0

                with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                    first_batch = True

                    while True:
                        update_status(f"Processing transaction batch {offset // batch_size + 1}...")
                        transactions = reports.get_detailed_sales_transactions(start, end, limit=batch_size, offset=offset)

                        if not transactions:
                            break

                        df = pd.DataFrame(transactions)

                        if first_batch:
                            df.to_excel(writer, sheet_name="Transactions", index=False)
                            first_batch = False
                        else:
                            # Append to existing sheet (this will create multiple sheets if very large)
                            sheet_name = f"Transactions_{offset // batch_size + 1}"
                            df.to_excel(writer, sheet_name=sheet_name, index=False)

                        offset += batch_size
                        if len(transactions) < batch_size:
                            break

            else:
                # For other reports, use regular Excel generation
                self._generate_excel_data(report_type, start, end, filename)

            update_status("Excel export completed")

        except Exception as e:
            update_status(f"Excel export failed: {str(e)}")
            raise
