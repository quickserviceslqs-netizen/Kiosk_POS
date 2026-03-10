"""Export manager for handling report exports."""

from typing import Dict, List, Any, Optional, Callable
import csv
import logging
from datetime import datetime

from utils.date_utils import format_date
# ReportData and CSVReportFormatter imported lazily in functions to avoid circular imports
from .reports_constants import FILE_EXTENSIONS, REPORT_LIMITS

logger = logging.getLogger(__name__)

# ── Brand / palette ──────────────────────────────────────────────────────────
# Static hex values so exports look clean even if no GUI is running
_BRAND_PRIMARY   = "#2563eb"
_BRAND_DARK      = "#1e40af"
_BRAND_LIGHT     = "#dbeafe"
_BRAND_ALT_ROW   = "#f0f6ff"
_TEXT_DARK       = "#1f2937"
_TEXT_MID        = "#6b7280"
_SUCCESS         = "#059669"
_WARNING         = "#d97706"
_DANGER          = "#dc2626"
_BORDER          = "#e5e7eb"
_WHITE           = "#ffffff"

def _hex_to_rgb(hex_color: str):
    """Convert #rrggbb to (r, g, b) 0-1 tuple for ReportLab."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))

def _get_business_name() -> str:
    """Read business name from DB settings."""
    try:
        from database.init_db import get_setting
        name = get_setting('business_name')
        return name if name else "Kiosk POS"
    except Exception:
        return "Kiosk POS"

def _get_app_version() -> str:
    try:
        from main import APP_VERSION
        return APP_VERSION
    except Exception:
        return ""


class ExportManager:
    """Manager for exporting reports to various formats."""

    def __init__(self):
        self.formatters = self._initialize_formatters()

    def _initialize_formatters(self) -> Dict[str, Callable]:
        """Initialize export formatters."""
        return {
            'csv': self._export_csv,
            'txt': self._export_text,
            'xlsx': self._export_excel,
            'pdf': self._export_pdf
        }

    def export_report(self, report_data, file_path: str,
                     format_type: Optional[str] = None) -> bool:
        from .reports_base import ReportData  # local to avoid circular import
        """Export a report to the specified file."""
        try:
            # Determine format from file extension if not specified
            if not format_type:
                if file_path.lower().endswith(FILE_EXTENSIONS['csv']):
                    format_type = 'csv'
                elif file_path.lower().endswith(FILE_EXTENSIONS['txt']):
                    format_type = 'txt'
                elif file_path.lower().endswith(('.xlsx', '.xls')):
                    format_type = 'xlsx'
                elif file_path.lower().endswith('.pdf'):
                    format_type = 'pdf'
                else:
                    format_type = 'csv'  # Default to CSV

            if format_type not in self.formatters:
                logger.error(f"Unsupported export format: {format_type}")
                return False

            formatter = self.formatters[format_type]
            return formatter(report_data, file_path)

        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return False

    def _export_csv(self, report_data, file_path: str) -> bool:
        from .reports_base import ReportData, CSVReportFormatter
        """Export report as CSV with metadata header."""
        try:
            formatter = self._get_csv_formatter(report_data)
            if formatter:
                rows = formatter.get_csv_rows()
            else:
                data = report_data.data or []
                if not data:
                    return False
                cols = list(data[0].keys())
                rows = [cols]
                for r in data:
                    rows.append([r.get(c) for c in cols])

            if not rows:
                return False

            business = _get_business_name()
            report_title = report_data.report_type.replace('_', ' ').title()
            _now = datetime.now()
            now_str = f"{format_date(_now)} {_now.strftime('%H:%M:%S')}"
            start = format_date(report_data.start_date) if report_data.start_date else ''
            end   = format_date(report_data.end_date)   if report_data.end_date   else ''

            # Write UTF-8 BOM so Excel opens it correctly
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                # Metadata block (commented out so it doesn't break imports)
                writer.writerow([f"# {business} – {report_title} Report"])
                writer.writerow([f"# Period: {start} to {end}"])
                writer.writerow([f"# Generated: {now_str}"])
                writer.writerow([f"# Records: {report_data.record_count}"])
                writer.writerow([])   # blank separator
                writer.writerows(rows)

            return True

        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return False

    def _export_text(self, report_data, file_path: str) -> bool:
        from .reports_base import ReportData
        """Export report as formatted text."""
        try:
            formatter = report_data.get_formatter(report_data)
            content = formatter.format_report()

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True

        except Exception as e:
            logger.error(f"Error exporting text: {e}")
            return False

    def _get_csv_formatter(self, report_data, ) -> Optional['CSVReportFormatter']:
        from .reports_base import CSVReportFormatter
        """Get the appropriate CSV formatter for the report type."""
        # Import here to avoid circular imports
        from .reports_csv_formatters import (
            SalesCSVFormatter, ProfitCSVFormatter, CategoryCSVFormatter,
            PaymentMethodsCSVFormatter, VoidedSalesCSVFormatter,
            ReconciliationCSVFormatter, InventoryStockLevelsCSVFormatter,
            InventoryLowStockCSVFormatter, InventoryValueCSVFormatter
        )

        from .reports_csv_formatters import (
            POSummaryCSVFormatter, POBySupplierCSVFormatter, POItemsDetailCSVFormatter
        )

        formatters = {
            'daily': SalesCSVFormatter,
            'range': SalesCSVFormatter,
            'bestsellers': SalesCSVFormatter,
            'profit': ProfitCSVFormatter,
            'category': CategoryCSVFormatter,
            'payment_methods': PaymentMethodsCSVFormatter,
            'voided': VoidedSalesCSVFormatter,
            'sales_log': SalesCSVFormatter,
            'transactions': SalesCSVFormatter,
            'trends': SalesCSVFormatter,
            'reconciliation_summary': ReconciliationCSVFormatter,
            'reconciliation_details': ReconciliationCSVFormatter,
            'inventory_stock_levels': InventoryStockLevelsCSVFormatter,
            'inventory_low_stock': InventoryLowStockCSVFormatter,
            'inventory_value': InventoryValueCSVFormatter,
            'po_summary': POSummaryCSVFormatter,
            'po_by_supplier': POBySupplierCSVFormatter,
            'po_items_detail': POItemsDetailCSVFormatter,
        }

        formatter_class = formatters.get(report_data.report_type)
        if formatter_class:
            return formatter_class(report_data)

        return None

    def export_report_streaming(self, report_type: str, start_date: str, end_date: str,
                                file_path: str, format_type: str = 'csv', page_size: int = 1000,
                                use_keyset: bool = False, status_filter: str = 'all') -> bool:
        """Stream a large report directly to disk in CSV format without materializing the full dataset.

        Currently supports 'sales_log' and 'reconciliation_details' (others will fall back to full export).
        """
        try:
            # Only CSV supported for streaming
            if format_type != 'csv':
                logger.error('Streaming export currently only supports CSV')
                return False

            from .reports_controller import ReportController as ReportService
            service = ReportService()

            # Open file and write rows per page
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # Sales log streaming
                if report_type == 'sales_log':
                    # write header
                    writer.writerow(['transaction_id', 'receipt_number', 'date', 'time', 'amount', 'payment_method', 'items_summary'])
                    cursor = None
                    while True:
                        rows, next_cursor, meta = service.generate_report_page('sales_log', start_date, end_date, page_size=page_size, cursor=cursor, use_keyset=use_keyset)
                        if not rows:
                            break
                        for r in rows:
                            writer.writerow([r.get('transaction_id'), r.get('receipt_number'), format_date(r.get('date')), r.get('time'), r.get('amount'), r.get('payment_method'), r.get('items_summary')])
                        if not next_cursor:
                            break
                        cursor = next_cursor
                    return True

                # Reconciliation details streaming
                if report_type == 'reconciliation_details':
                    writer.writerow(['session_id', 'reconciliation_date', 'status', 'total_system_sales', 'total_actual_cash', 'total_variance'])
                    cursor = None
                    while True:
                        rows, next_cursor, meta = service.generate_report_page('reconciliation_details', start_date, end_date, page_size=page_size, cursor=cursor, use_keyset=use_keyset)
                        if not rows:
                            break
                        for r in rows:
                            # r may be dict or object
                            if isinstance(r, dict):
                                writer.writerow([r.get('session_id'), format_date(r.get('reconciliation_date')), r.get('status'), r.get('total_system_sales'), r.get('total_actual_cash'), r.get('total_variance')])
                            else:
                                writer.writerow([r.session_id, format_date(r.reconciliation_date), r.status, r.total_system_sales, r.total_actual_cash, r.total_variance])
                        if not next_cursor:
                            break
                        cursor = next_cursor
                    return True

                # Inventory stock levels streaming
                if report_type == 'inventory_stock_levels':
                    writer.writerow(['item_id', 'name', 'category', 'quantity', 'unit', 'inventory_value', 'is_low_stock'])
                    cursor = None
                    while True:
                        rows, next_cursor, meta = service.generate_report_page('inventory_stock_levels', start_date, end_date, page_size=page_size, cursor=cursor, use_keyset=use_keyset)
                        if not rows:
                            break
                        for r in rows:
                            # row expected to be dict
                            writer.writerow([r.get('item_id'), r.get('name'), r.get('category'), r.get('quantity'), r.get('unit'), r.get('inventory_value'), r.get('is_low_stock')])
                        if not next_cursor:
                            break
                        cursor = next_cursor
                    return True

            # Fallback: unsupported report types - return False
            logger.error(f"Streaming not implemented for report type: {report_type}")
            return False

        except Exception as e:
            logger.error(f"Error streaming export: {e}")
            return False

    def _export_excel(self, report_data, file_path: str) -> bool:
        from .reports_base import ReportData
        """Export report as styled Excel file using openpyxl."""
        try:
            import openpyxl
            from openpyxl.styles import (
                Font, PatternFill, Alignment, Border, Side, GradientFill
            )
            from openpyxl.utils import get_column_letter

            formatter = self._get_csv_formatter(report_data)
            if not formatter:
                return False

            csv_rows = formatter.get_csv_rows()
            if not csv_rows:
                return False

            # ── Colours (openpyxl uses ARGB without #) ──────────────────────
            def _c(hex_color):
                return hex_color.lstrip('#').upper()

            primary_fill = PatternFill("solid", fgColor=_c(_BRAND_PRIMARY))
            dark_fill    = PatternFill("solid", fgColor=_c(_BRAND_DARK))
            alt_fill     = PatternFill("solid", fgColor=_c(_BRAND_ALT_ROW))
            white_fill   = PatternFill("solid", fgColor="FFFFFF")
            meta_fill    = PatternFill("solid", fgColor=_c(_BRAND_LIGHT))
            warn_fill    = PatternFill("solid", fgColor="FEF9C3")

            thin_border_side = Side(style='thin', color=_c(_BORDER))
            cell_border = Border(
                left=thin_border_side, right=thin_border_side,
                top=thin_border_side,  bottom=thin_border_side
            )
            thick_bottom = Border(
                left=thin_border_side, right=thin_border_side,
                top=thin_border_side,  bottom=Side(style='medium', color=_c(_BRAND_PRIMARY))
            )

            wb = openpyxl.Workbook()
            ws = wb.active

            business = _get_business_name()
            report_title = report_data.report_type.replace('_', ' ').title()
            version = _get_app_version()
            _now = datetime.now()
            now_str = f"{format_date(_now)} {_now.strftime('%H:%M:%S')}"
            start = format_date(report_data.start_date) if report_data.start_date else 'N/A'
            end   = format_date(report_data.end_date)   if report_data.end_date   else 'N/A'
            num_cols = len(csv_rows[0]) if csv_rows else 1

            ws.title = report_title[:31]  # Excel sheet name limit

            # ── Banner row ────────────────────────────────────────────────────
            ws.row_dimensions[1].height = 36
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(num_cols, 4))
            banner_cell = ws.cell(row=1, column=1,
                                  value=f"  {business}  •  {report_title} Report")
            banner_cell.font = Font(name='Calibri', bold=True, size=16, color="FFFFFF")
            banner_cell.fill = primary_fill
            banner_cell.alignment = Alignment(horizontal='left', vertical='center')

            # ── Metadata rows ─────────────────────────────────────────────────
            meta_info = [
                ("Period:", f"{start}  →  {end}"),
                ("Generated:", now_str),
                ("Records:", str(report_data.record_count)),
                ("App Version:", f"Kiosk POS v{version}" if version else "Kiosk POS"),
            ]
            for offset, (label, value) in enumerate(meta_info, start=2):
                ws.row_dimensions[offset].height = 18
                lc = ws.cell(row=offset, column=1, value=label)
                lc.font = Font(name='Calibri', bold=True, size=10, color=_c(_TEXT_MID))
                lc.fill = meta_fill
                vc = ws.cell(row=offset, column=2, value=value)
                vc.font = Font(name='Calibri', size=10, color=_c(_TEXT_DARK))
                vc.fill = meta_fill
                # Merge remaining columns
                if num_cols > 2:
                    ws.merge_cells(start_row=offset, start_column=2,
                                   end_row=offset, end_column=num_cols)

            separator_row = 2 + len(meta_info) + 1  # blank gap
            header_row = separator_row + 1

            # ── Header row ────────────────────────────────────────────────────
            ws.row_dimensions[header_row].height = 22
            headers = csv_rows[0]
            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=header_row, column=col_idx, value=str(header))
                cell.font = Font(name='Calibri', bold=True, size=11, color="FFFFFF")
                cell.fill = dark_fill
                cell.alignment = Alignment(horizontal='center', vertical='center',
                                           wrap_text=False)
                cell.border = thick_bottom

            ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

            # ── Data rows ──────────────────────────────────────────────────────
            for row_offset, row_data in enumerate(csv_rows[1:], start=0):
                excel_row = header_row + 1 + row_offset
                ws.row_dimensions[excel_row].height = 17
                fill = alt_fill if row_offset % 2 == 0 else white_fill
                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=excel_row, column=col_idx, value=value)
                    cell.fill = fill
                    cell.border = cell_border
                    cell.font = Font(name='Calibri', size=10, color=_c(_TEXT_DARK))

                    # Right-align numeric columns
                    if isinstance(value, (int, float)):
                        cell.alignment = Alignment(horizontal='right', vertical='center')
                        if isinstance(value, float):
                            cell.number_format = '#,##0.00'
                        else:
                            cell.number_format = '#,##0'
                    else:
                        cell.alignment = Alignment(horizontal='left', vertical='center',
                                                   wrap_text=False)

            # ── Auto column widths ─────────────────────────────────────────────
            for col_idx, header in enumerate(headers, start=1):
                col_letter = get_column_letter(col_idx)
                max_len = max(
                    len(str(header)),
                    *(len(str(row[col_idx - 1])) for row in csv_rows[1:]
                      if col_idx - 1 < len(row))
                ) if len(csv_rows) > 1 else len(str(header))
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

            # ── Metadata sheet ─────────────────────────────────────────────────
            ws_meta = wb.create_sheet(title="Report Info")
            ws_meta.column_dimensions['A'].width = 20
            ws_meta.column_dimensions['B'].width = 40
            meta_rows = [
                ("Report Type",  report_title),
                ("Business",     business),
                ("Period Start",  start),
                ("Period End",    end),
                ("Generated At", now_str),
                ("Records",      report_data.record_count),
                ("App Version",  f"Kiosk POS v{version}" if version else "Kiosk POS"),
            ]
            for r_idx, (k, v) in enumerate(meta_rows, start=1):
                kc = ws_meta.cell(row=r_idx, column=1, value=k)
                kc.font = Font(bold=True, color=_c(_TEXT_MID))
                kc.fill = meta_fill
                vc = ws_meta.cell(row=r_idx, column=2, value=v)
                vc.font = Font(color=_c(_TEXT_DARK))

            wb.save(file_path)
            return True

        except ImportError:
            logger.error("openpyxl required for Excel export")
            return False
        except Exception as e:
            logger.error(f"Error exporting Excel: {e}")
            return False

    def _export_pdf(self, report_data, file_path: str) -> bool:
        from .reports_base import ReportData
        """Export report as a polished branded PDF."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph,
                Spacer, HRFlowable
            )
            from reportlab.lib.colors import HexColor

            # ── Colour palette ────────────────────────────────────────────────
            C_PRIMARY  = HexColor(_BRAND_PRIMARY)
            C_DARK     = HexColor(_BRAND_DARK)
            C_LIGHT    = HexColor(_BRAND_LIGHT)
            C_ALT_ROW  = HexColor(_BRAND_ALT_ROW)
            C_BORDER   = HexColor(_BORDER)
            C_TXT_DARK = HexColor(_TEXT_DARK)
            C_TXT_MID  = HexColor(_TEXT_MID)
            C_WHITE    = colors.white

            formatter = self._get_csv_formatter(report_data)
            if not formatter:
                return False

            csv_rows = formatter.get_csv_rows()
            if not csv_rows:
                return False

            business     = _get_business_name()
            version      = _get_app_version()
            report_title = report_data.report_type.replace('_', ' ').title()
            _now         = datetime.now()
            now_str      = f"{format_date(_now)} {_now.strftime('%H:%M:%S')}"
            start        = format_date(report_data.start_date) if report_data.start_date else 'N/A'
            end          = format_date(report_data.end_date)   if report_data.end_date   else 'N/A'

            PAGE_W, PAGE_H = A4
            MARGIN = 1.8 * cm

            # ── Page decoration callback (header + footer) ────────────────────
            class _PageDeco:
                def __call__(self_, canv, doc):
                    canv.saveState()
                    # Header stripe
                    canv.setFillColor(C_PRIMARY)
                    canv.rect(0, PAGE_H - 1.2 * cm, PAGE_W, 1.2 * cm,
                              fill=True, stroke=False)
                    canv.setFillColor(C_WHITE)
                    canv.setFont('Helvetica-Bold', 10)
                    canv.drawString(MARGIN, PAGE_H - 0.85 * cm, business)
                    canv.setFont('Helvetica', 9)
                    canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.85 * cm,
                                         f"{report_title}  Report")
                    # Footer stripe
                    canv.setFillColor(C_DARK)
                    canv.rect(0, 0, PAGE_W, 1.0 * cm, fill=True, stroke=False)
                    canv.setFillColor(C_WHITE)
                    canv.setFont('Helvetica', 8)
                    canv.drawString(MARGIN, 0.35 * cm, f"Generated {now_str}")
                    ver_str = f"Kiosk POS v{version}" if version else "Kiosk POS"
                    canv.drawCentredString(PAGE_W / 2, 0.35 * cm, ver_str)
                    canv.drawRightString(PAGE_W - MARGIN, 0.35 * cm,
                                         f"Page {doc.page}")
                    canv.restoreState()

            deco = _PageDeco()

            doc = SimpleDocTemplate(
                file_path, pagesize=A4,
                leftMargin=MARGIN, rightMargin=MARGIN,
                topMargin=2.8 * cm, bottomMargin=1.6 * cm,
                title=f"{business} \u2013 {report_title} Report",
                author=business, subject=report_title,
                creator=f"Kiosk POS v{version}" if version else "Kiosk POS",
            )

            styles   = getSampleStyleSheet()
            content_w = PAGE_W - 2 * MARGIN

            style_title = ParagraphStyle(
                'rptTitle', parent=styles['Normal'],
                fontName='Helvetica-Bold', fontSize=22,
                textColor=C_PRIMARY, spaceAfter=4)
            style_sub = ParagraphStyle(
                'rptSub', parent=styles['Normal'],
                fontName='Helvetica', fontSize=11,
                textColor=C_TXT_MID, spaceAfter=8)
            style_section = ParagraphStyle(
                'rptSection', parent=styles['Normal'],
                fontName='Helvetica-Bold', fontSize=11,
                textColor=C_PRIMARY, spaceBefore=10, spaceAfter=4)
            style_metaL = ParagraphStyle(
                'metaL', parent=styles['Normal'],
                fontName='Helvetica-Bold', fontSize=9, textColor=C_TXT_MID)
            style_metaV = ParagraphStyle(
                'metaV', parent=styles['Normal'],
                fontName='Helvetica', fontSize=9, textColor=C_TXT_DARK)
            style_note = ParagraphStyle(
                'note', parent=styles['Normal'],
                fontName='Helvetica-Oblique', fontSize=8,
                textColor=C_TXT_MID, spaceAfter=6)
            style_thdr = ParagraphStyle(
                'thdr', parent=styles['Normal'],
                fontName='Helvetica-Bold', fontSize=9,
                textColor=C_WHITE, alignment=TA_CENTER)
            style_tcell = ParagraphStyle(
                'tcell', parent=styles['Normal'],
                fontName='Helvetica', fontSize=8,
                textColor=C_TXT_DARK, leading=11)
            style_tcell_r = ParagraphStyle(
                'tcell_r', parent=style_tcell, alignment=TA_RIGHT)

            elements = []

            # ── Hero block ────────────────────────────────────────────────────
            elements.append(Paragraph(f"{report_title} Report", style_title))
            elements.append(Paragraph(
                f"{business}  \u2022  Period: <b>{start}</b> to <b>{end}</b>",
                style_sub))
            elements.append(HRFlowable(
                width="100%", thickness=2, color=C_PRIMARY,
                spaceAfter=4, spaceBefore=0))
            elements.append(Spacer(1, 14))

            # ── Metadata grid ─────────────────────────────────────────────────
            meta_pairs = [
                ("Report Type", report_title),
                ("Date Range",  f"{start}  \u2013  {end}"),
                ("Records",     str(report_data.record_count)),
                ("Generated",   now_str),
            ]
            meta_rows = []
            for i in range(0, len(meta_pairs), 2):
                row = []
                for label, value in meta_pairs[i:i+2]:
                    row += [Paragraph(f"<b>{label}</b>", style_metaL),
                            Paragraph(value, style_metaV)]
                while len(row) < 4:
                    row += [Paragraph('', style_metaL), Paragraph('', style_metaV)]
                meta_rows.append(row)

            half = content_w / 2
            meta_tbl = Table(meta_rows,
                             colWidths=[2.5*cm, half-2.5*cm, 2.5*cm, half-2.5*cm])
            meta_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), C_LIGHT),
                ('BOX',        (0, 0), (-1, -1), 0.5, C_BORDER),
                ('INNERGRID',  (0, 0), (-1, -1), 0.25, C_BORDER),
                ('TOPPADDING',    (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING',   (0, 0), (-1, -1), 7),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 7),
            ]))
            elements.append(meta_tbl)
            elements.append(Spacer(1, 14))

            # ── Summary block ─────────────────────────────────────────────────
            summary_items = self._build_pdf_summary(report_data)
            if summary_items:
                elements.append(Paragraph("Summary", style_section))
                sum_rows = [[Paragraph(f"<b>{lbl}</b>", style_metaL),
                             Paragraph(str(val), style_metaV)]
                            for lbl, val in summary_items]
                sum_tbl = Table(sum_rows, colWidths=[5*cm, content_w-5*cm])
                sum_tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), C_LIGHT),
                    ('BACKGROUND', (1, 0), (1, -1), C_WHITE),
                    ('BOX',        (0, 0), (-1, -1), 0.5, C_BORDER),
                    ('INNERGRID',  (0, 0), (-1, -1), 0.25, C_BORDER),
                    ('TOPPADDING',    (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING',   (0, 0), (-1, -1), 7),
                    ('RIGHTPADDING',  (0, 0), (-1, -1), 7),
                ]))
                elements.append(sum_tbl)
                elements.append(Spacer(1, 14))

            # ── Data table ────────────────────────────────────────────────────
            elements.append(Paragraph("Data", style_section))

            def _is_numeric(val):
                try:
                    float(str(val).replace(',', '').replace('%', ''))
                    return True
                except (ValueError, TypeError):
                    return False

            headers = csv_rows[0]
            num_cols = set()
            if len(csv_rows) > 1:
                for ci, v in enumerate(csv_rows[1]):
                    if _is_numeric(v) and str(headers[ci]).lower() not in ('id', 'receipt', 'barcode'):
                        num_cols.add(ci)

            # Proportional column widths
            col_max = []
            for ci in range(len(headers)):
                max_len = len(str(headers[ci]))
                for row in csv_rows[1:]:
                    if ci < len(row):
                        max_len = max(max_len, len(str(row[ci])))
                col_max.append(max(max_len * 0.22 * cm, 1.5 * cm))
            total_w = sum(col_max) or 1
            col_widths = [w / total_w * content_w for w in col_max]

            tbl_data = [[Paragraph(str(h), style_thdr) for h in headers]]
            for row in csv_rows[1:]:
                trow = []
                for ci, val in enumerate(row):
                    st = style_tcell_r if ci in num_cols else style_tcell
                    trow.append(Paragraph(str(val) if val is not None else '', st))
                tbl_data.append(trow)

            data_tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
            data_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0), C_PRIMARY),
                ('ROWBACKGROUNDS',(0, 1), (-1, -1), [C_WHITE, C_ALT_ROW]),
                ('BOX',     (0, 0), (-1, -1), 0.5, C_BORDER),
                ('LINEBELOW',(0, 0), (-1, 0), 1.5, C_DARK),
                ('INNERGRID',(0, 1), (-1, -1), 0.25, C_BORDER),
                ('TOPPADDING',    (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING',   (0, 0), (-1, -1), 6),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

            elements.append(data_tbl)
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(
                f"Total records: {report_data.record_count}  \u2022  "
                f"Exported on {now_str}  \u2022  Confidential",
                style_note))

            doc.build(elements, onFirstPage=deco, onLaterPages=deco)
            return True

        except ImportError:
            logger.error("reportlab required for PDF export")
            return False
        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            return False

    def _build_pdf_summary(self, report_data) -> list:
        """Return a list of (label, value) pairs for the PDF summary block."""
        try:
            from utils.i18n import get_currency_symbol
            cur = get_currency_symbol()
        except Exception:
            cur = "$"
        try:
            rt   = report_data.report_type
            meta = report_data.metadata or {}
            data = report_data.data or []
            items: list = []

            if rt in ('daily', 'range', 'bestsellers', 'sales_log', 'transactions'):
                total = sum(float(r.get('total', 0) or 0) for r in data)
                items = [
                    ("Total Revenue", f"{cur}{total:,.2f}"),
                    ("Transactions",  str(report_data.record_count)),
                ]
            elif rt == 'profit':
                analysis = meta.get('analysis', {})
                if analysis:
                    items = [
                        ("Total Revenue", f"{cur}{analysis.get('total_revenue', 0):,.2f}"),
                        ("Total Cost",    f"{cur}{analysis.get('total_cost', 0):,.2f}"),
                        ("Gross Profit",  f"{cur}{analysis.get('gross_profit', 0):,.2f}"),
                        ("Profit Margin", f"{analysis.get('profit_margin', 0):.1f}%"),
                    ]
            elif rt == 'category':
                total = meta.get('total_revenue', 0)
                items = [
                    ("Total Revenue", f"{cur}{total:,.2f}"),
                    ("Categories",    str(len(data))),
                ]
            elif rt == 'payment_methods':
                total = sum(float(r.get('total_amount', 0) or 0) for r in data)
                items = [
                    ("Total Revenue",   f"{cur}{total:,.2f}"),
                    ("Payment Methods", str(len(data))),
                ]
            elif rt in ('reconciliation_summary', 'reconciliation_details'):
                items = [
                    ("Total System Sales", f"{cur}{meta.get('total_system', 0):,.2f}"),
                    ("Total Actual Cash",  f"{cur}{meta.get('total_actual', 0):,.2f}"),
                    ("Net Variance",       f"{cur}{meta.get('total_variance', 0):,.2f}"),
                ]
            elif rt in ('inventory_stock_levels', 'inventory_low_stock', 'inventory_value'):
                total_val = sum(
                    float(r.get('inventory_value',
                           float(r.get('quantity', 0) or 0) *
                           float(r.get('cost_price', 0) or 0)) or 0)
                    for r in data
                )
                items = [
                    ("Total Items",      str(len(data))),
                    ("Total Inv. Value", f"{cur}{total_val:,.2f}"),
                ]
            return items
        except Exception:
            return []