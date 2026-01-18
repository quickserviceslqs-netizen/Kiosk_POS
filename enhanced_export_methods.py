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
        progress_window.resizable(False, False)
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

                    writer.writerow(["Detailed Sales Transactions"])
                    writer.writerow([f"Period: {start} to {end}"])
                    writer.writerow([])
                    writer.writerow(["Receipt", "Date", "Time", "Item Name", "Category", "Quantity", "Price", "Line Total", "Sale Total", "Payment Method"])

                    while True:
                        update_status(f"Processing transactions batch {offset // batch_size + 1}...")
                        transactions = reports.get_detailed_sales_transactions(start, end, limit=batch_size, offset=offset)
                        if not transactions:
                            break

                        for transaction in transactions:
                            writer.writerow([
                                transaction["receipt_number"],
                                transaction["date"],
                                transaction["time"],
                                transaction["item_name"],
                                transaction["category"],
                                transaction["quantity"],
                                transaction["price"],
                                transaction["line_total"],
                                transaction["total"],
                                transaction.get("payment_method", "Cash")
                            ])

                        offset += batch_size
                        if len(transactions) < batch_size:
                            break

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

                transactions_df = pd.DataFrame(all_transactions)
                transactions_df.to_excel(filename, index=False)

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