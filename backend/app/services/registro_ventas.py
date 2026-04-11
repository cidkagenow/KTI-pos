"""
Registro de Ventas — genera un Excel mensual para enviar a la contadora.

Formato estándar de Registro de Ventas e Ingresos para SUNAT PLE:
período, CUO, fecha emisión, tipo comprobante, serie, número,
tipo/número doc cliente, razón social, base imponible, IGV, total,
moneda, estado (anotado/anulado), y referencia para notas de crédito.
"""
from __future__ import annotations

import io
from calendar import monthrange
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.client import Client
from app.models.sale import Sale

# SUNAT document type codes (Catálogo 10)
DOC_TYPE_SUNAT = {
    "FACTURA": "01",
    "BOLETA": "03",
    "NOTA_CREDITO": "07",
    "NOTA_DEBITO": "08",
    "NOTA_VENTA": "00",  # Internal, not fiscal
}

# SUNAT client doc type codes (Catálogo 06)
CLIENT_DOC_SUNAT = {
    "RUC": "6",
    "DNI": "1",
    "NONE": "0",
    "CE": "4",
    "PASAPORTE": "7",
}

MONTH_NAMES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def get_monthly_sales(db: Session, year: int, month: int) -> list[Sale]:
    """Retrieve all FACTURADO and ANULADO sales for the given month (Lima time)."""
    last_day = monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)

    lima_date = func.date(func.timezone("America/Lima", Sale.created_at))

    return (
        db.query(Sale)
        .options(joinedload(Sale.client), joinedload(Sale.ref_sale))
        .filter(
            Sale.status.in_(["FACTURADO", "ANULADO"]),
            Sale.doc_type.in_(["FACTURA", "BOLETA", "NOTA_CREDITO"]),
            lima_date >= start,
            lima_date <= end,
        )
        .order_by(Sale.doc_type, Sale.series, Sale.doc_number)
        .all()
    )


def generate_registro_ventas_xlsx(db: Session, year: int, month: int) -> bytes:
    """Generate the Registro de Ventas XLSX for the given month.

    Returns the XLSX file as bytes.
    """
    sales = get_monthly_sales(db, year, month)
    period = f"{year}{month:02d}"

    wb = Workbook()
    ws = wb.active
    ws.title = f"Registro {period}"

    # ─── Header block ───
    ws["A1"] = "REGISTRO DE VENTAS E INGRESOS"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:P1")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws["A2"] = f"PERÍODO: {MONTH_NAMES_ES[month]} {year}"
    ws["A2"].font = Font(bold=True)
    ws.merge_cells("A2:P2")
    ws["A2"].alignment = Alignment(horizontal="center")

    ws["A3"] = f"RUC: {settings.EMPRESA_RUC}"
    ws.merge_cells("A3:H3")
    ws["I3"] = f"RAZÓN SOCIAL: {settings.EMPRESA_RAZON_SOCIAL}"
    ws.merge_cells("I3:P3")

    # ─── Column headers (row 5) ───
    headers = [
        "N°",
        "Fecha Emisión",
        "Fecha Vcto.",
        "Tipo Cbte.",
        "Serie",
        "Número",
        "Tipo Doc.",
        "N° Doc. Cliente",
        "Razón Social / Nombre",
        "Base Imponible",
        "IGV (18%)",
        "Importe Total",
        "Moneda",
        "T. Cambio",
        "Estado",
        "Referencia (NC)",
    ]

    header_fill = PatternFill(start_color="1a3a8f", end_color="1a3a8f", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    thin = Side(border_style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=5, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border

    # ─── Data rows ───
    total_base = 0.0
    total_igv = 0.0
    total_importe = 0.0

    row = 6
    for idx, sale in enumerate(sales, start=1):
        issue_date = sale.issue_date or (
            sale.created_at.date() if sale.created_at else None
        )

        doc_tipo_sunat = DOC_TYPE_SUNAT.get(sale.doc_type, "")
        client = sale.client
        client_doc_type = CLIENT_DOC_SUNAT.get(client.doc_type if client else "", "0")
        client_doc_num = client.doc_number if client else ""
        client_name = client.business_name if client else ""

        # NC stores amounts as positive — show negative in the registry
        is_nc = sale.doc_type == "NOTA_CREDITO"
        sign = -1 if is_nc else 1

        base = float(sale.subtotal) * sign
        igv = float(sale.igv_amount) * sign
        total = float(sale.total) * sign

        estado = "2 - Anulado" if sale.status == "ANULADO" else "1 - Anotado"

        ref = ""
        if is_nc and sale.ref_sale:
            ref_doc = DOC_TYPE_SUNAT.get(sale.ref_sale.doc_type, "")
            ref = f"{ref_doc} | {sale.ref_sale.series}-{sale.ref_sale.doc_number or ''}"

        doc_num_str = str(sale.doc_number).zfill(8) if sale.doc_number else "-"

        values = [
            idx,
            issue_date.strftime("%d/%m/%Y") if issue_date else "",
            "",  # Fecha vencimiento (no aplicamos crédito fiscal aquí)
            doc_tipo_sunat,
            sale.series,
            doc_num_str,
            client_doc_type,
            client_doc_num,
            client_name,
            round(base, 2),
            round(igv, 2),
            round(total, 2),
            "PEN",
            "1.000",
            estado,
            ref,
        ]

        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.border = border
            if col_idx in (10, 11, 12):
                cell.number_format = '#,##0.00;[Red]-#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif col_idx in (1, 4, 7, 13, 14):
                cell.alignment = Alignment(horizontal="center")
            elif col_idx == 9:
                cell.alignment = Alignment(horizontal="left")

        # Accumulate totals only for non-voided
        if sale.status != "ANULADO":
            total_base += base
            total_igv += igv
            total_importe += total

        row += 1

    # ─── Totals row ───
    total_row = row + 1
    tot_label = ws.cell(row=total_row, column=9, value="TOTALES")
    tot_label.font = Font(bold=True)
    tot_label.alignment = Alignment(horizontal="right")
    tot_label.fill = PatternFill(start_color="E8ECF2", end_color="E8ECF2", fill_type="solid")

    for col_idx, val in zip((10, 11, 12), (total_base, total_igv, total_importe)):
        c = ws.cell(row=total_row, column=col_idx, value=round(val, 2))
        c.font = Font(bold=True)
        c.number_format = '#,##0.00;[Red]-#,##0.00'
        c.alignment = Alignment(horizontal="right")
        c.fill = PatternFill(start_color="E8ECF2", end_color="E8ECF2", fill_type="solid")
        c.border = border

    # ─── Column widths ───
    widths = [5, 12, 12, 10, 8, 12, 10, 14, 40, 14, 12, 14, 9, 11, 14, 22]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.row_dimensions[5].height = 32
    ws.freeze_panes = "A6"

    # ─── Save to bytes ───
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()


def build_filename(year: int, month: int) -> str:
    """Standard filename for the monthly registry."""
    return f"Registro_Ventas_{settings.EMPRESA_RUC}_{year}{month:02d}.xlsx"
