import sys
import os
import tempfile
import traceback

sys.path.append('.')
from datetime import datetime, timedelta
import tkinter as tk
import tkinter.filedialog as fd

from ui.reports import ModernReportsFrame
from ui.reports_service import ReportService


def run_test():
    root = tk.Tk()
    root.withdraw()

    # Prevent the frame's initial async generation from updating UI (no mainloop in tests)
    from ui.reports_service import ReportService as _ReportService
    _orig_async = _ReportService.generate_report_async
    _ReportService.generate_report_async = lambda self, *a, **k: ""

    try:
        frame = ModernReportsFrame(root)
    finally:
        # restore async method so subsequent calls behave normally
        _ReportService.generate_report_async = _orig_async

    service = ReportService()

    start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end = datetime.now().strftime('%Y-%m-%d')

    tests = [
        # (report_type, expects_streaming)
        ('transactions', False),
        ('inventory_stock_levels', True),
        ('reconciliation_details', True),
    ]

    with tempfile.TemporaryDirectory() as td:
        for report_type, expects_streaming in tests:
            try:
                print(f"Testing report: {report_type} (streaming={expects_streaming})")

                # Set per-report local dates and, if reconciliation, status
                frame._local_date_vars[report_type] = (tk.StringVar(value=start), tk.StringVar(value=end))
                if 'reconciliation' in report_type:
                    frame._local_status_vars[report_type] = tk.StringVar(value='all')

                # Use the service directly to ensure dates respected
                rd = service.generate_report_sync(report_type, start, end, frame._local_status_vars.get(report_type, tk.StringVar(value='all')).get())
                assert rd.report_type == report_type, f"Expected report type {report_type}, got {rd.report_type}"
                print(f"  Generated {len(rd.data)} rows")

                # Simulate regeneration via per-report generation helper using a synchronous stubbed async to avoid threads
                orig_async = frame.service.generate_report_async
                def sync_async(report_type_arg, start_arg, end_arg, callback, status_arg='all'):
                    # Immediately call callback with synchronous result
                    result = frame.service.generate_report_sync(report_type_arg, start_arg, end_arg, status_arg)
                    if callback:
                        callback(result)
                    return "sync"

                frame.service.generate_report_async = sync_async
                try:
                    frame._generate_report_with_params(report_type, start, end, frame._local_status_vars.get(report_type, tk.StringVar(value='all')).get())
                    print(f"  Regenerated {report_type} synchronously")
                finally:
                    frame.service.generate_report_async = orig_async

                # Prepare file path and monkeypatch filedialog
                out_path = os.path.join(td, f"{report_type}.csv")
                orig = fd.asksaveasfilename
                fd.asksaveasfilename = lambda **kwargs: out_path

                try:
                    frame.report_type.set(report_type)
                    # Trigger download (will call export manager with local dates)
                    frame._download_report()
                finally:
                    fd.asksaveasfilename = orig

                # Validate file created
                assert os.path.exists(out_path), f"Export did not create file: {out_path}"
                size = os.path.getsize(out_path)
                assert size > 0, f"Export file empty: {out_path}"
                print(f"  Export succeeded, file size: {size} bytes")

            except Exception as e:
                print(f"Test failed for {report_type}: {e}")
                traceback.print_exc()

    root.destroy()


if __name__ == '__main__':
    run_test()
