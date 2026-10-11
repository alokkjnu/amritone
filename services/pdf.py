"""PDF generation for invoices and packing slips using ReportLab."""

from __future__ import annotations
import io
from decimal import Decimal
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)

from config.settings import settings
from models.order import Order


class InvoicePDFService:
    """Generate invoice PDF for an order."""

    PRIMARY_COLOR = colors.HexColor("#8B6914")
    DARK_COLOR = colors.HexColor("#1a1a1a")

    def generate_invoice(self, order: Order) -> bytes:
        """Return PDF bytes for the given order."""
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
        story = []

        # Header
        header_style = ParagraphStyle(
            "Header",
            fontSize=22,
            textColor=self.PRIMARY_COLOR,
            fontName="Helvetica-Bold",
        )
        sub_style = ParagraphStyle("Sub", fontSize=9, textColor=colors.grey)
        normal_style = ParagraphStyle("Normal", fontSize=9)
        bold_style = ParagraphStyle("Bold", fontSize=9, fontName="Helvetica-Bold")

        story.append(Paragraph(settings.APP_NAME, header_style))
        story.append(Paragraph(settings.APP_TAGLINE, sub_style))
        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", thickness=1, color=self.PRIMARY_COLOR))
        story.append(Spacer(1, 4 * mm))

        # Invoice meta
        meta_data = [
            ["TAX INVOICE", "", f"Invoice #: {order.order_number}"],
            ["", "", f"Date: {order.created_at.strftime('%d %b %Y')}"],
            ["", "", f"Order Status: {order.status.value.upper()}"],
        ]
        meta_table = Table(meta_data, colWidths=[60 * mm, 60 * mm, 60 * mm])
        meta_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (0, 0), 14),
            ("TEXTCOLOR", (0, 0), (0, 0), self.PRIMARY_COLOR),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 6 * mm))

        # Addresses
        addr_data = [
            [
                Paragraph("<b>Bill To:</b>", bold_style),
                Paragraph("<b>Ship To:</b>", bold_style),
            ],
            [
                Paragraph(f"{order.billing_name}<br/>{order.billing_address}<br/>{order.billing_city}, {order.billing_state} - {order.billing_pincode}<br/>Ph: {order.billing_phone}", normal_style),
                Paragraph(f"{order.shipping_name}<br/>{order.shipping_address}<br/>{order.shipping_city}, {order.shipping_state} - {order.shipping_pincode}<br/>Ph: {order.shipping_phone}", normal_style),
            ],
        ]
        addr_table = Table(addr_data, colWidths=[90 * mm, 90 * mm])
        addr_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F0E8")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(addr_table)
        story.append(Spacer(1, 6 * mm))

        # Items table
        item_headers = ["#", "Product", "Size", "Qty", "MRP", "Price", "GST%", "Total"]
        item_rows = [item_headers]
        for idx, item in enumerate(order.items, start=1):
            gst_val = float(item.unit_price) * float(item.gst_percent) / 100 * item.quantity
            item_rows.append([
                str(idx),
                item.product_name,
                item.variant_size,
                str(item.quantity),
                f"₹{item.mrp:.2f}",
                f"₹{item.unit_price:.2f}",
                f"{item.gst_percent}%",
                f"₹{item.total_price:.2f}",
            ])

        col_widths = [8 * mm, 55 * mm, 18 * mm, 10 * mm, 20 * mm, 20 * mm, 14 * mm, 20 * mm]
        items_table = Table(item_rows, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAF8")]),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 6 * mm))

        # Totals
        totals_data = [
            ["Subtotal:", f"₹{order.subtotal:.2f}"],
            ["Shipping:", f"₹{order.shipping_charge:.2f}"],
            ["GST:", f"₹{order.gst_amount:.2f}"],
            ["Discount:", f"-₹{order.discount_amount:.2f}"],
            ["TOTAL:", f"₹{order.total_amount:.2f}"],
        ]
        totals_table = Table(totals_data, colWidths=[130 * mm, 35 * mm])
        totals_table.setStyle(TableStyle([
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 11),
            ("TEXTCOLOR", (0, -1), (-1, -1), self.PRIMARY_COLOR),
            ("LINEABOVE", (0, -1), (-1, -1), 1, self.PRIMARY_COLOR),
            ("TOPPADDING", (0, -1), (-1, -1), 4),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 8 * mm))

        # Footer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"Thank you for shopping with {settings.APP_NAME}! | {settings.COMPANY_EMAIL} | {settings.COMPANY_PHONE}",
            ParagraphStyle("Footer", fontSize=8, textColor=colors.grey, alignment=1),
        ))

        doc.build(story)
        return buffer.getvalue()
