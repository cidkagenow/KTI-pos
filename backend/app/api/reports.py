from datetime import date, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func, case, literal_column

from app.config import settings
from app.database import get_db
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.user import User
from app.schemas.report import DashboardStats, SalesByPeriod, TopProduct, ProfitReport
from app.api.deps import get_current_user
from app.services.registro_ventas import (
    build_filename as registro_ventas_filename,
    generate_registro_ventas_xlsx,
    get_monthly_sales,
)
from app.services.email_service import send_registro_ventas_email

router = APIRouter()

# Convert UTC timestamps to Lima time for correct date grouping
_lima = func.timezone("America/Lima", Sale.created_at)

# Statuses that count as actual sales for reporting
SALE_STATUSES = ("FACTURADO",)


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    def _count_and_total(from_date: date) -> tuple[int, float]:
        result = (
            db.query(
                func.count(case((Sale.doc_type != "NOTA_CREDITO", Sale.id))),
                func.coalesce(func.sum(
                    case((Sale.doc_type == "NOTA_CREDITO", -Sale.total), else_=Sale.total)
                ), 0),
            )
            .filter(
                Sale.status.in_(SALE_STATUSES),
                Sale.doc_type != "PROFORMA",
                func.date(_lima) >= from_date,
            )
            .first()
        )
        return int(result[0]), float(result[1])

    today_sales, today_total = _count_and_total(today)
    week_sales, week_total = _count_and_total(start_of_week)
    month_sales, month_total = _count_and_total(start_of_month)

    low_stock_count = (
        db.query(func.count(Inventory.id))
        .join(Product, Inventory.product_id == Product.id)
        .filter(Inventory.quantity <= Product.min_stock)
        .scalar()
    ) or 0

    return DashboardStats(
        today_sales=today_sales,
        today_total=today_total,
        week_sales=week_sales,
        week_total=week_total,
        month_sales=month_sales,
        month_total=month_total,
        low_stock_count=low_stock_count,
    )


@router.get("/sales-by-period", response_model=list[SalesByPeriod])
def sales_by_period(
    from_date: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    to_date: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    group_by: str = Query("day", description="Agrupar por: day, week, month"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    base_query = db.query(Sale).filter(
        Sale.status.in_(SALE_STATUSES),
        func.date(_lima) >= from_date,
        func.date(_lima) <= to_date,
    )

    if group_by == "month":
        period_expr = func.to_char(_lima, "YYYY-MM")
    elif group_by == "week":
        period_expr = func.concat(func.to_char(_lima, "IYYY"), literal_column("'-W'"), func.to_char(_lima, "IW"))
    else:  # day
        period_expr = func.to_char(_lima, "YYYY-MM-DD")

    results = (
        db.query(
            period_expr.label("period"),
            func.count(case((Sale.doc_type != "NOTA_CREDITO", Sale.id))).label("count"),
            func.coalesce(func.sum(
                case((Sale.doc_type == "NOTA_CREDITO", -Sale.total), else_=Sale.total)
            ), 0).label("total"),
        )
        .filter(
            Sale.status.in_(SALE_STATUSES),
            Sale.doc_type != "PROFORMA",
            func.date(_lima) >= from_date,
            func.date(_lima) <= to_date,
        )
        .group_by(period_expr)
        .order_by(period_expr)
        .all()
    )

    return [
        SalesByPeriod(period=r.period, count=r.count, total=float(r.total))
        for r in results
    ]


@router.get("/top-products", response_model=list[TopProduct])
def top_products(
    from_date: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    to_date: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    nc_qty = case((Sale.doc_type == "NOTA_CREDITO", -SaleItem.quantity), else_=SaleItem.quantity)
    nc_rev = case((Sale.doc_type == "NOTA_CREDITO", -SaleItem.line_total), else_=SaleItem.line_total)
    results = (
        db.query(
            SaleItem.product_name.label("product_name"),
            func.sum(nc_qty).label("quantity_sold"),
            func.sum(nc_rev).label("total_revenue"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.status.in_(SALE_STATUSES),
            Sale.doc_type != "PROFORMA",
            func.date(_lima) >= from_date,
            func.date(_lima) <= to_date,
        )
        .group_by(SaleItem.product_name)
        .order_by(func.sum(nc_rev).desc())
        .limit(limit)
        .all()
    )

    return [
        TopProduct(
            product_name=r.product_name or "Sin nombre",
            quantity_sold=int(r.quantity_sold),
            total_revenue=float(r.total_revenue),
        )
        for r in results
    ]


@router.get("/profit-report", response_model=list[ProfitReport])
def profit_report(
    from_date: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    to_date: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Reporte de Utilidades - per-product profitability."""
    nc_qty = case((Sale.doc_type == "NOTA_CREDITO", -SaleItem.quantity), else_=SaleItem.quantity)
    nc_rev = case((Sale.doc_type == "NOTA_CREDITO", -SaleItem.line_total), else_=SaleItem.line_total)
    results = (
        db.query(
            SaleItem.product_code.label("product_code"),
            SaleItem.product_name.label("product_name"),
            SaleItem.brand_name.label("brand_name"),
            func.sum(nc_qty).label("quantity_sold"),
            func.sum(nc_rev).label("total_revenue"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.status.in_(SALE_STATUSES),
            Sale.doc_type != "PROFORMA",
            func.date(_lima) >= from_date,
            func.date(_lima) <= to_date,
        )
        .group_by(SaleItem.product_code, SaleItem.product_name, SaleItem.brand_name)
        .order_by(func.sum(nc_rev).desc())
        .all()
    )

    report = []
    for r in results:
        revenue = float(r.total_revenue)
        # Get cost price from product table
        product = db.query(Product).filter(Product.code == r.product_code).first()
        cost_per_unit = float(product.cost_price) if product and product.cost_price else 0
        qty = int(r.quantity_sold)
        total_cost = cost_per_unit * qty
        profit = revenue - total_cost
        margin = (profit / revenue * 100) if revenue > 0 else 0

        report.append(ProfitReport(
            product_code=r.product_code or "",
            product_name=r.product_name or "Sin nombre",
            brand_name=r.brand_name,
            quantity_sold=qty,
            total_revenue=round(revenue, 2),
            total_cost=round(total_cost, 2),
            profit=round(profit, 2),
            profit_margin=round(margin, 2),
        ))

    return report


# ───────────────────────────────────────────────────────────
# Registro de Ventas — monthly export for accountant
# ───────────────────────────────────────────────────────────


def _validate_period(year: int, month: int) -> None:
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Mes inválido (1-12).")
    if year < 2020 or year > 2100:
        raise HTTPException(status_code=400, detail="Año inválido.")

    # Block current and future months — only completed months allowed
    today = datetime.now().date()
    if year > today.year or (year == today.year and month >= today.month):
        raise HTTPException(
            status_code=400,
            detail="El período aún no ha terminado. Solo puedes enviar meses completos.",
        )


MONTHS_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


@router.get("/registro-ventas/config")
def registro_ventas_config(
    user: User = Depends(get_current_user),
):
    """Return the default accountant email configured in .env (ADMIN only)."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo ADMIN.")
    return {"accountant_email": settings.ACCOUNTANT_EMAIL or ""}


@router.get("/registro-ventas/download")
def download_registro_ventas(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download the monthly Registro de Ventas as XLSX (ADMIN only)."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo ADMIN puede descargar este reporte.")
    _validate_period(year, month)

    sales = get_monthly_sales(db, year, month)
    if not sales:
        raise HTTPException(
            status_code=404,
            detail=f"No hay ventas registradas en {MONTHS_ES[month]} {year}.",
        )

    xlsx_bytes = generate_registro_ventas_xlsx(db, year, month)
    filename = registro_ventas_filename(year, month)

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/registro-ventas/send-email")
def send_registro_ventas(
    year: int = Body(...),
    month: int = Body(...),
    email: str | None = Body(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate the Registro de Ventas and email it to the accountant (ADMIN only)."""
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Solo ADMIN puede enviar este reporte.")
    _validate_period(year, month)

    to_email = (email or settings.ACCOUNTANT_EMAIL or "").strip()
    if not to_email:
        raise HTTPException(
            status_code=400,
            detail="No se configuró el correo de la contadora. Indique el correo o configure ACCOUNTANT_EMAIL.",
        )

    sales = get_monthly_sales(db, year, month)
    if not sales:
        raise HTTPException(
            status_code=404,
            detail=f"No hay ventas registradas en {MONTHS_ES[month]} {year}. No se envió el correo.",
        )

    xlsx_bytes = generate_registro_ventas_xlsx(db, year, month)
    filename = registro_ventas_filename(year, month)

    success, error = send_registro_ventas_email(to_email, year, month, xlsx_bytes, filename)
    if not success:
        raise HTTPException(status_code=500, detail=error or "Error al enviar el correo.")

    return {"ok": True, "email": to_email, "filename": filename, "sale_count": len(sales)}
