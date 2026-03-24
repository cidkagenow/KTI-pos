from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SupplierOut(BaseModel):
    id: int
    ruc: str | None
    business_name: str
    city: str | None
    phone: str | None
    email: str | None
    address: str | None
    credit_days: int = 30

    model_config = ConfigDict(from_attributes=True)


class SupplierCreate(BaseModel):
    ruc: str | None = None
    business_name: str
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    credit_days: int = 30


class PurchaseOrderItemIn(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float
    discount_pct1: float = 0
    discount_pct2: float = 0
    discount_pct3: float = 0
    flete_unit: float = 0


class PurchaseOrderItemOut(BaseModel):
    id: int
    product_id: int
    product_code: str | None
    product_name: str | None
    quantity: int
    unit_cost: float
    discount_pct1: float
    discount_pct2: float
    discount_pct3: float
    flete_unit: float
    line_total: float

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    doc_type: str | None = None
    doc_number: str | None = None
    supplier_doc: str | None = None
    condicion: str = "CONTADO"
    moneda: str = "SOLES"
    tipo_cambio: float | None = None
    igv_included: bool = True
    flete: float = 0
    grr_number: str | None = None
    issue_date: str | None = None
    expected_delivery_date: str | None = None
    items: list[PurchaseOrderItemIn]
    notes: str | None = None


class PurchaseOrderOut(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str
    supplier_ruc: str | None
    warehouse_id: int
    status: str
    doc_type: str | None
    doc_number: str | None
    supplier_doc: str | None
    condicion: str | None
    moneda: str | None
    tipo_cambio: float | None
    igv_included: bool | None
    subtotal: float | None
    igv_amount: float | None
    total: float | None
    flete: float | None
    grr_number: str | None
    notes: str | None
    expected_delivery_date: date | None
    issue_date: datetime | None
    received_at: datetime | None
    created_at: datetime
    items: list[PurchaseOrderItemOut]

    model_config = ConfigDict(from_attributes=True)
