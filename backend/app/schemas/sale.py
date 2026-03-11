from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DocumentSeriesOut(BaseModel):
    id: int
    doc_type: str
    series: str
    next_number: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class DocumentSeriesCreate(BaseModel):
    doc_type: str
    series: str


class SaleItemIn(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    discount_pct: float = 0


class SaleItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    discount_pct: float
    line_total: float
    product_code: str
    product_name: str
    brand_name: str | None
    presentation: str | None

    model_config = ConfigDict(from_attributes=True)


class SaleCreate(BaseModel):
    doc_type: str
    series: str
    client_id: int
    warehouse_id: int
    seller_id: int | None = None
    trabajador_id: int | None = None
    payment_cond: str = "CONTADO"
    payment_method: str = "EFECTIVO"
    cash_received: float | None = None
    cash_change: float | None = None
    max_discount_pct: float = 0
    issue_date: date | None = None
    items: list[SaleItemIn]
    notes: str | None = None


class NotaCreditoItemIn(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    discount_pct: float = 0


class NotaCreditoCreate(BaseModel):
    ref_sale_id: int
    nc_motivo_code: str
    nc_motivo_text: str
    items: list[NotaCreditoItemIn]


class SaleOut(BaseModel):
    id: int
    doc_type: str
    series: str
    doc_number: int | None = None
    client_id: int
    client_name: str
    client_doc_type: str | None = None
    client_doc_number: str | None = None
    client_address: str | None = None
    warehouse_id: int
    seller_id: int | None = None
    trabajador_id: int | None = None
    seller_name: str
    payment_cond: str
    payment_method: str | None
    cash_received: float | None
    cash_change: float | None
    max_discount_pct: float | None
    subtotal: float
    igv_amount: float
    total: float
    status: str
    notes: str | None
    issue_date: date
    created_at: datetime
    items: list[SaleItemOut]
    ref_sale_id: int | None = None
    nc_motivo_code: str | None = None
    nc_motivo_text: str | None = None
    sunat_hash: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SaleListOut(BaseModel):
    id: int
    doc_type: str
    series: str
    doc_number: int | None = None
    client_id: int
    client_name: str
    warehouse_id: int
    seller_id: int | None = None
    trabajador_id: int | None = None
    seller_name: str
    payment_cond: str
    payment_method: str | None
    cash_received: float | None = None
    subtotal: float
    igv_amount: float
    total: float
    status: str
    notes: str | None
    issue_date: date
    created_at: datetime
    sunat_status: str | None = None
    ref_sale_id: int | None = None
    nc_motivo_code: str | None = None

    model_config = ConfigDict(from_attributes=True)


class VoidRequest(BaseModel):
    reason: str


class ConvertirRequest(BaseModel):
    target_doc_type: str  # "BOLETA" or "FACTURA"
    target_series: str    # e.g. "B001" or "F001"
