from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case

from app.database import get_db
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.user import User
from app.schemas.report import DashboardStats, SalesByPeriod, TopProduct, ProfitReport
from app.api.deps import get_current_user

router = APIRouter()

# Statuses that count as actual sales for reporting
SALE_STATUSES = ("FACTURADO", "PREVENTA")


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
                func.count(Sale.id),
                func.coalesce(func.sum(Sale.total), 0),
            )
            .filter(
                Sale.status.in_(SALE_STATUSES),
                func.date(Sale.created_at) >= from_date,
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
        func.date(Sale.created_at) >= from_date,
        func.date(Sale.created_at) <= to_date,
    )

    if group_by == "month":
        period_expr = func.to_char(Sale.created_at, "YYYY-MM")
    elif group_by == "week":
        period_expr = func.to_char(Sale.created_at, "IYYY-IW")
    else:  # day
        period_expr = func.to_char(Sale.created_at, "YYYY-MM-DD")

    results = (
        db.query(
            period_expr.label("period"),
            func.count(Sale.id).label("count"),
            func.coalesce(func.sum(Sale.total), 0).label("total"),
        )
        .filter(
            Sale.status.in_(SALE_STATUSES),
            func.date(Sale.created_at) >= from_date,
            func.date(Sale.created_at) <= to_date,
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
    results = (
        db.query(
            SaleItem.product_name.label("product_name"),
            func.sum(SaleItem.quantity).label("quantity_sold"),
            func.sum(SaleItem.line_total).label("total_revenue"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.status.in_(SALE_STATUSES),
            func.date(Sale.created_at) >= from_date,
            func.date(Sale.created_at) <= to_date,
        )
        .group_by(SaleItem.product_name)
        .order_by(func.sum(SaleItem.line_total).desc())
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
    results = (
        db.query(
            SaleItem.product_code.label("product_code"),
            SaleItem.product_name.label("product_name"),
            SaleItem.brand_name.label("brand_name"),
            func.sum(SaleItem.quantity).label("quantity_sold"),
            func.sum(SaleItem.line_total).label("total_revenue"),
        )
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.status.in_(SALE_STATUSES),
            func.date(Sale.created_at) >= from_date,
            func.date(Sale.created_at) <= to_date,
        )
        .group_by(SaleItem.product_code, SaleItem.product_name, SaleItem.brand_name)
        .order_by(func.sum(SaleItem.line_total).desc())
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
