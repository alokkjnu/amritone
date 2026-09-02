"""
Amrit One — PDF Generation Utilities
Generates invoices, packing slips, and shipping labels using ReportLab.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config.settings import settings

GOLD = colors.HexColor("#C9A84C")
BLACK = colors.HexColor("#1A1A1A")
LIGHT_GREY = colors.HexColor("#F5F5F5")
DARK_GREY = colors.HexColor("#555555")


def generate_invoice_pdf(order: Dict[str, Any]) -> bytes:
    """Generate a GST-compliant invoice PDF for an order."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    elements = []

    # ── Header ────────────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph(f"<b>{settings.APP_NAME}</b><br/>Pure. Natural. Authentic.", styles["Title"]),
            Paragraph(
                f"<b>TAX INVOICE</b><br/>Invoice No: {order.get('invoice_number', order['order_number'])}<br/>"
                f"Date: {order['created_at']}<br/>GSTIN: {settings.GSTIN}",
                styles["Normal"],
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[90 * mm, 90 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), GOLD),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 5 * mm))

    # ── Addresses ─────────────────────────────────────────────────────────────
    billing = order.get("billing_address", {})
    shipping = order.get("shipping_address", {})

    addr_data = [
        [
            Paragraph(
                f"<b>Bill To:</b><br/>{billing.get('first_name', '')} {billing.get('last_name', '')}<br/>"
                f"{billing.get('address_line1', '')}<br/>{billing.get('city', '')}, {billing.get('state', '')} - {billing.get('pincode', '')}<br/>"
                f"Phone: {billing.get('phone', '')}",
                styles["Normal"],
            ),
            Paragraph(
                f"<b>Ship To:</b><br/>{shipping.get('first_name', '')} {shipping.get('last_name', '')}<br/>"
                f"{shipping.get('address_line1', '')}<br/>{shipping.get('city', '')}, {shipping.get('state', '')} - {shipping.get('pincode', '')}<br/>"
                f"Phone: {shipping.get('phone', '')}",
                styles["Normal"],
            ),
        ]
    ]
    addr_table = Table(addr_data, colWidths=[90 * mm, 90 * mm])
    addr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, DARK_GREY),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, DARK_GREY),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(addr_table)
    elements.append(Spacer(1, 5 * mm))

    # ── Order Items ───────────────────────────────────────────────────────────
    item_headers = ["#", "Product", "SKU", "Qty", "MRP", "Price", "GST%", "GST Amt", "Total"]
    item_rows = [item_headers]
    for idx, item in enumerate(order.get("items", []), 1):
        item_rows.append([
            str(idx),
            item["product_name"],
            item["sku"],
            str(item["quantity"]),
            f"₹{item['mrp']:.2f}",
            f"₹{item['unit_price']:.2f}",
            f"{item['gst_rate']}%",
            f"₹{item['gst_amount']:.2f}",
            f"₹{item['line_total']:.2f}",
        ])

    items_table = Table(
        item_rows,
        colWidths=[8 * mm, 45 * mm, 22 * mm, 12 * mm, 18 * mm, 18 * mm, 12 * mm, 18 * mm, 20 * mm],
    )
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GOLD),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.3, DARK_GREY),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 5 * mm))

    # ── Totals ────────────────────────────────────────────────────────────────
    totals_data = [
        ["Subtotal:", f"₹{order['subtotal']:.2f}"],
        ["GST:", f"₹{order.get('gst_amount', 0):.2f}"],
        ["Shipping:", f"₹{order.get('shipping_amount', 0):.2f}"],
        ["Discount:", f"-₹{order.get('discount_amount', 0):.2f}"],
        ["", ""],
        ["TOTAL PAYABLE:", f"₹{order['total_amount']:.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[130 * mm, 50 * mm])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("BACKGROUND", (0, -1), (-1, -1), GOLD),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, -1), (-1, -1), 1, GOLD),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 8 * mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(Paragraph(
        f"Thank you for shopping with {settings.APP_NAME}! For support contact us at support@amritone.com",
        styles["Normal"],
    ))
    elements.append(Paragraph(
        "This is a computer-generated invoice and does not require a physical signature.",
        ParagraphStyle("footer", parent=styles["Normal"], textColor=DARK_GREY, fontSize=8),
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_packing_slip_pdf(order: Dict[str, Any]) -> bytes:
    """Generate a simple packing slip PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>PACKING SLIP — {settings.APP_NAME}</b>", styles["Title"]))
    elements.append(Paragraph(f"Order: {order['order_number']} | Date: {order['created_at']}", styles["Normal"]))
    elements.append(Spacer(1, 5 * mm))

    shipping = order.get("shipping_address", {})
    elements.append(Paragraph(
        f"<b>Deliver To:</b><br/>{shipping.get('first_name', '')} {shipping.get('last_name', '')}<br/>"
        f"{shipping.get('address_line1', '')}<br/>{shipping.get('city', '')}, {shipping.get('state', '')} - {shipping.get('pincode', '')}<br/>"
        f"Phone: {shipping.get('phone', '')}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 5 * mm))

    rows = [["Product", "SKU", "Qty"]]
    for item in order.get("items", []):
        rows.append([item["product_name"], item["sku"], str(item["quantity"])])

    t = Table(rows, colWidths=[100 * mm, 50 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GOLD),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, DARK_GREY),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()


def generate_shipping_label_pdf(order: Dict[str, Any]) -> bytes:
    """Generate a shipping label PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(100 * mm, 150 * mm),
                            rightMargin=5 * mm, leftMargin=5 * mm,
                            topMargin=5 * mm, bottomMargin=5 * mm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>{settings.APP_NAME}</b>", styles["Title"]))
    elements.append(Spacer(1, 3 * mm))

    shipping = order.get("shipping_address", {})
    elements.append(Paragraph("<b>TO:</b>", styles["Normal"]))
    elements.append(Paragraph(
        f"{shipping.get('first_name', '')} {shipping.get('last_name', '')}<br/>"
        f"{shipping.get('address_line1', '')}, {shipping.get('address_line2', '')}<br/>"
        f"{shipping.get('city', '')}, {shipping.get('state', '')} - {shipping.get('pincode', '')}<br/>"
        f"📞 {shipping.get('phone', '')}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph(f"<b>Order:</b> {order['order_number']}", styles["Normal"]))
    if order.get("tracking_number"):
        elements.append(Paragraph(f"<b>Tracking:</b> {order['tracking_number']}", styles["Normal"]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        f"<b>FROM:</b><br/>{settings.APP_NAME}<br/>Pure. Natural. Authentic.",
        styles["Normal"],
    ))

    doc.build(elements)
    return buffer.getvalue()
