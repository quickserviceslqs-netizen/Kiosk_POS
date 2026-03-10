"""Purchase Order (LPO/PO) management module."""
from __future__ import annotations

import sqlite3
from datetime import date
from typing import List, Optional, Dict, Any

from database.init_db import get_connection
from utils.date_utils import format_date


def ensure_po_tables() -> None:
    """Create purchase order tables if they don't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS purchase_orders (
                po_id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number TEXT NOT NULL UNIQUE,
                supplier TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                notes TEXT,
                created_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                total_amount REAL NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS purchase_order_items (
                poi_id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_id INTEGER NOT NULL,
                item_id INTEGER,
                item_name TEXT NOT NULL,
                quantity_ordered REAL NOT NULL,
                unit_cost REAL NOT NULL DEFAULT 0,
                quantity_received REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def generate_po_number() -> str:
    """Generate unique PO number like PO-20260307-001."""
    today = date.today().strftime("%Y%m%d")
    with get_connection() as conn:
        row = conn.execute(
            "SELECT po_number FROM purchase_orders WHERE po_number LIKE ? ORDER BY po_id DESC LIMIT 1",
            (f"PO-{today}-%",)
        ).fetchone()
        if row:
            try:
                seq = int(row[0].split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
    return f"PO-{today}-{seq:03d}"


def create_po(
    items: List[Dict[str, Any]],
    supplier: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: Optional[str] = None,
) -> int:
    """Create a new purchase order. Returns the po_id."""
    ensure_po_tables()
    po_number = generate_po_number()
    total = sum(float(i.get("quantity_ordered", 0)) * float(i.get("unit_cost", 0)) for i in items)
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO purchase_orders (po_number, supplier, status, notes, created_by, total_amount)
               VALUES (?, ?, 'draft', ?, ?, ?)""",
            (po_number, supplier, notes, created_by, total)
        )
        po_id = cursor.lastrowid
        for item in items:
            conn.execute(
                """INSERT INTO purchase_order_items (po_id, item_id, item_name, quantity_ordered, unit_cost)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    po_id,
                    item.get("item_id"),
                    item["item_name"],
                    float(item["quantity_ordered"]),
                    float(item["unit_cost"]),
                )
            )
        conn.commit()
    return po_id


def list_pos(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all purchase orders, optionally filtered by status."""
    ensure_po_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if status:
            rows = conn.execute(
                "SELECT * FROM purchase_orders WHERE status = ? ORDER BY po_id DESC",
                (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM purchase_orders ORDER BY po_id DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def list_pos_with_item_count(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List purchase orders with the number of line items per PO."""
    ensure_po_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        if status:
            rows = conn.execute(
                """SELECT po.*, COUNT(poi.poi_id) as item_count
                   FROM purchase_orders po
                   LEFT JOIN purchase_order_items poi ON po.po_id = poi.po_id
                   WHERE po.status = ?
                   GROUP BY po.po_id
                   ORDER BY po.po_id DESC""",
                (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT po.*, COUNT(poi.poi_id) as item_count
                   FROM purchase_orders po
                   LEFT JOIN purchase_order_items poi ON po.po_id = poi.po_id
                   GROUP BY po.po_id
                   ORDER BY po.po_id DESC"""
            ).fetchall()
        return [dict(r) for r in rows]


def get_po(po_id: int) -> Optional[Dict[str, Any]]:
    """Get a single PO with its line items."""
    ensure_po_tables()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        po = conn.execute(
            "SELECT * FROM purchase_orders WHERE po_id = ?", (po_id,)
        ).fetchone()
        if not po:
            return None
        po_dict = dict(po)
        items = conn.execute(
            "SELECT * FROM purchase_order_items WHERE po_id = ? ORDER BY poi_id",
            (po_id,)
        ).fetchall()
        po_dict["items"] = [dict(i) for i in items]
        return po_dict


def update_po_status(po_id: int, status: str) -> None:
    """Update the status of a purchase order."""
    ensure_po_tables()
    with get_connection() as conn:
        conn.execute(
            "UPDATE purchase_orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE po_id = ?",
            (status, po_id)
        )
        conn.commit()


def delete_po(po_id: int) -> None:
    """Delete a draft purchase order (and its items via CASCADE)."""
    ensure_po_tables()
    with get_connection() as conn:
        conn.execute("DELETE FROM purchase_orders WHERE po_id = ?", (po_id,))
        conn.commit()


def get_low_stock_suggestions() -> List[Dict[str, Any]]:
    """Return items at or below their low-stock threshold with suggested reorder quantities."""
    from database.init_db import get_connection
    import sqlite3
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT item_id, name, COALESCE(category, 'Uncategorized') AS category,
                   quantity AS current_stock,
                   COALESCE(low_stock_threshold, 0) AS low_stock_threshold,
                   COALESCE(cost_price, 0) AS average_cost
            FROM items
            WHERE quantity <= COALESCE(low_stock_threshold, 0)
              AND low_stock_threshold IS NOT NULL
              AND low_stock_threshold > 0
            ORDER BY category, name
            """
        ).fetchall()
    result = []
    for r in rows:
        threshold = int(r["low_stock_threshold"])
        current   = float(r["current_stock"])
        suggested = max(1, threshold - int(current))
        result.append({
            "item_id":            r["item_id"],
            "name":               r["name"],
            "category":           r["category"],
            "current_stock":      current,
            "low_stock_threshold": threshold,
            "suggested_quantity": suggested,
            "average_cost":       float(r["average_cost"]),
            "estimated_cost":     suggested * float(r["average_cost"]),
        })
    return result


def format_po_text(po: Dict[str, Any], company_name: str = "", currency: str = "") -> str:
    """Format a PO as a printable text document (LPO layout)."""
    cur = currency or ""
    sep = "=" * 64
    thin = "-" * 64

    lines = [sep]
    if company_name:
        pad = (64 - len(company_name)) // 2
        lines.append(" " * pad + company_name)
        lines.append(thin)
    lines.append("          LOCAL PURCHASE ORDER (LPO)")
    lines.append(sep)
    lines.append(f"  PO Number  : {po.get('po_number', '')}")
    _txt_date = format_date(str(po.get('created_at', ''))[:10]) if po.get('created_at') else ''
    lines.append(f"  Date       : {_txt_date}")
    lines.append(f"  Supplier   : {po.get('supplier') or 'N/A'}")
    lines.append(f"  Status     : {str(po.get('status', '')).upper()}")
    if po.get("notes"):
        lines.append(f"  Notes      : {po['notes']}")
    lines.append(thin)
    lines.append(f"  {'#':<4} {'Item':<28} {'Qty':>8}  {'Unit Cost':>11}  {'Line Total':>11}")
    lines.append(thin)
    for idx, item in enumerate(po.get("items", []), 1):
        qty = float(item.get("quantity_ordered", 0))
        cost = float(item.get("unit_cost", 0))
        total = qty * cost
        name = str(item.get("item_name", ""))[:28]
        lines.append(
            f"  {idx:<4} {name:<28} {qty:>8.0f}  {cur}{cost:>10.2f}  {cur}{total:>10.2f}"
        )
    lines.append(thin)
    grand = float(po.get("total_amount", 0))
    lines.append(f"  {'GRAND TOTAL':<42}  {cur}{grand:>10.2f}")
    lines.append(sep)
    lines.append(f"  Prepared by : {po.get('created_by') or ''}")
    lines.append("")
    lines.append(f"  Authorized Signature : ____________________________")
    lines.append(sep)
    return "\n".join(lines)


def export_po_csv(po: Dict[str, Any], file_path: str, currency: str = "") -> None:
    """Export a PO to a CSV file."""
    import csv
    cur = currency or ""
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header metadata
        writer.writerow(["PO Number", po.get("po_number", "")])
        writer.writerow(["Date", format_date(str(po.get("created_at", ""))[:10]) if po.get("created_at") else ""])
        writer.writerow(["Supplier", po.get("supplier") or ""])
        writer.writerow(["Status", str(po.get("status", "")).upper()])
        writer.writerow(["Notes", po.get("notes") or ""])
        writer.writerow(["Prepared By", po.get("created_by") or ""])
        writer.writerow([])
        # Item columns
        writer.writerow(["#", "Item Name", "Qty Ordered", "Unit Cost", "Line Total"])
        for idx, item in enumerate(po.get("items", []), 1):
            qty = float(item.get("quantity_ordered", 0))
            cost = float(item.get("unit_cost", 0))
            writer.writerow([idx, item.get("item_name", ""), qty, f"{cur}{cost:.2f}", f"{cur}{qty * cost:.2f}"])
        writer.writerow([])
        writer.writerow(["", "", "", "GRAND TOTAL", f"{cur}{float(po.get('total_amount', 0)):.2f}"])


def export_po_pdf(po: Dict[str, Any], file_path: str, company_name: str = "", currency: str = "") -> None:
    """Export a PO to a branded PDF using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.colors import HexColor

    C_PRIMARY  = HexColor("#2563eb")
    C_DARK     = HexColor("#1e3a5f")
    C_ALT_ROW  = HexColor("#eff6ff")
    C_BORDER   = HexColor("#bfdbfe")
    C_TXT_DARK = HexColor("#1f2937")
    C_TXT_MID  = HexColor("#6b7280")
    C_WHITE    = colors.white

    cur = currency or ""
    PAGE_W, PAGE_H = A4
    MARGIN = 1.8 * cm
    po_number = po.get("po_number", "PO")
    now_str = format_date(str(po.get("created_at", ""))[:10]) if po.get("created_at") else ""
    biz = company_name or "Kiosk POS"

    class _PageDeco:
        def __call__(self_, canv, doc):
            canv.saveState()
            canv.setFillColor(C_PRIMARY)
            canv.rect(0, PAGE_H - 1.2 * cm, PAGE_W, 1.2 * cm, fill=True, stroke=False)
            canv.setFillColor(C_WHITE)
            canv.setFont("Helvetica-Bold", 10)
            canv.drawString(MARGIN, PAGE_H - 0.85 * cm, biz)
            canv.setFont("Helvetica", 9)
            canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.85 * cm, "LOCAL PURCHASE ORDER")
            canv.setFillColor(C_DARK)
            canv.rect(0, 0, PAGE_W, 1.0 * cm, fill=True, stroke=False)
            canv.setFillColor(C_WHITE)
            canv.setFont("Helvetica", 8)
            canv.drawString(MARGIN, 0.35 * cm, f"Generated {now_str}")
            canv.drawRightString(PAGE_W - MARGIN, 0.35 * cm, f"Page {doc.page}")
            canv.restoreState()

    doc = SimpleDocTemplate(
        file_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.8 * cm, bottomMargin=1.6 * cm,
        title=f"{biz} – {po_number}",
    )

    styles = getSampleStyleSheet()
    content_w = PAGE_W - 2 * MARGIN

    s_title = ParagraphStyle("poTitle", fontName="Helvetica-Bold", fontSize=20,
                             textColor=C_PRIMARY, spaceAfter=4)
    s_sub   = ParagraphStyle("poSub",   fontName="Helvetica",      fontSize=10,
                             textColor=C_TXT_MID, spaceAfter=10)
    s_label = ParagraphStyle("poLabel", fontName="Helvetica-Bold", fontSize=9,
                             textColor=C_TXT_MID)
    s_value = ParagraphStyle("poValue", fontName="Helvetica",      fontSize=9,
                             textColor=C_TXT_DARK)
    s_thdr  = ParagraphStyle("poThdr",  fontName="Helvetica-Bold", fontSize=9,
                             textColor=C_WHITE,   alignment=TA_CENTER)
    s_cell  = ParagraphStyle("poCell",  fontName="Helvetica",      fontSize=9,
                             textColor=C_TXT_DARK)
    s_cell_r = ParagraphStyle("poCellR", fontName="Helvetica",     fontSize=9,
                              textColor=C_TXT_DARK, alignment=TA_RIGHT)
    s_total  = ParagraphStyle("poTotal", fontName="Helvetica-Bold", fontSize=10,
                              textColor=C_PRIMARY,  alignment=TA_RIGHT)
    s_sig    = ParagraphStyle("poSig",   fontName="Helvetica",      fontSize=9,
                              textColor=C_TXT_MID)

    story = []
    story.append(Paragraph("LOCAL PURCHASE ORDER", s_title))
    story.append(Paragraph(f"PO Number: <b>{po.get('po_number', '')}</b>", s_sub))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=4))
    story.append(Spacer(1, 14))

    # Meta table
    _po_date_fmt = format_date(str(po.get("created_at", ""))[:10]) if po.get("created_at") else ""
    meta_data = [
        [Paragraph("Date:",        s_label), Paragraph(_po_date_fmt, s_value),
         Paragraph("Supplier:",    s_label), Paragraph(po.get("supplier") or "N/A",        s_value)],
        [Paragraph("Status:",      s_label), Paragraph(str(po.get("status", "")).upper(),  s_value),
         Paragraph("Prepared By:", s_label), Paragraph(po.get("created_by") or "",         s_value)],
    ]
    if po.get("notes"):
        meta_data.append([Paragraph("Notes:", s_label), Paragraph(po["notes"], s_value), Paragraph("", s_label), Paragraph("", s_value)])

    col_w = content_w / 4
    meta_tbl = Table(meta_data, colWidths=[col_w * 0.45, col_w * 1.05, col_w * 0.45, col_w * 1.05])
    meta_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=6))

    # Items table header
    col_widths = [content_w * 0.06, content_w * 0.42, content_w * 0.14, content_w * 0.19, content_w * 0.19]
    tbl_data = [[
        Paragraph("#",          s_thdr),
        Paragraph("Item Name",  s_thdr),
        Paragraph("Qty",        s_thdr),
        Paragraph("Unit Cost",  s_thdr),
        Paragraph("Line Total", s_thdr),
    ]]
    for idx, item in enumerate(po.get("items", []), 1):
        qty  = float(item.get("quantity_ordered", 0))
        cost = float(item.get("unit_cost", 0))
        line = qty * cost
        bg = C_ALT_ROW if idx % 2 == 0 else C_WHITE
        tbl_data.append([
            Paragraph(str(idx),                  s_cell),
            Paragraph(item.get("item_name", ""), s_cell),
            Paragraph(f"{qty:.0f}",              s_cell_r),
            Paragraph(f"{cur}{cost:.2f}",        s_cell_r),
            Paragraph(f"{cur}{line:.2f}",        s_cell_r),
        ])

    grand = float(po.get("total_amount", 0))
    tbl_data.append([
        Paragraph("", s_cell), Paragraph("", s_cell), Paragraph("", s_cell),
        Paragraph("TOTAL", ParagraphStyle("tot_lbl", fontName="Helvetica-Bold", fontSize=9,
                                          textColor=C_TXT_DARK, alignment=TA_RIGHT)),
        Paragraph(f"{cur}{grand:.2f}", s_total),
    ])

    items_tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
    n_items = len(po.get("items", []))
    alt_rows = [(i + 1, i + 1) for i in range(n_items) if (i + 1) % 2 == 1]
    row_style = [
        ("BACKGROUND",   (0, 0), (-1, 0),  C_PRIMARY),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  C_WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, n_items), [C_WHITE, C_ALT_ROW]),
        ("BACKGROUND",   (0, n_items + 1), (-1, n_items + 1), C_ALT_ROW),
        ("LINEBELOW",    (0, 0),  (-1, 0),  0.5, C_BORDER),
        ("LINEABOVE",    (0, n_items + 1), (-1, n_items + 1), 0.5, C_BORDER),
        ("GRID",         (0, 0), (-1, n_items), 0.25, C_BORDER),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]
    items_tbl.setStyle(TableStyle(row_style))
    story.append(items_tbl)
    story.append(Spacer(1, 0.8 * cm))

    # Signature block
    sig_data = [[
        Paragraph("Prepared by: __________________________", s_sig),
        Paragraph("Authorized Signature: __________________________", s_sig),
    ]]
    sig_tbl = Table(sig_data, colWidths=[content_w / 2, content_w / 2])
    sig_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(sig_tbl)

    doc.build(story, onFirstPage=_PageDeco(), onLaterPages=_PageDeco())
