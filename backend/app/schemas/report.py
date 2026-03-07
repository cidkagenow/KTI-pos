from pydantic import BaseModel


class DashboardStats(BaseModel):
    today_sales: int
    today_total: float
    week_sales: int
    week_total: float
    month_sales: int
    month_total: float
    low_stock_count: int


class SalesByPeriod(BaseModel):
    period: str
    count: int
    total: float


class TopProduct(BaseModel):
    product_name: str
    quantity_sold: int
    total_revenue: float


class ProfitReport(BaseModel):
    product_code: str
    product_name: str
    brand_name: str | None
    quantity_sold: int
    total_revenue: float
    total_cost: float
    profit: float
    profit_margin: float
