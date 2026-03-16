from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---------- Items ----------

class OnlineOrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    line_total: float
    product_code: str
    product_name: str
    brand_name: str | None
    presentation: str | None

    model_config = ConfigDict(from_attributes=True)


class OnlineOrderItemCreate(BaseModel):
    product_id: int
    quantity: int


# ---------- Order ----------

class OnlineOrderOut(BaseModel):
    id: int
    order_code: str
    customer_name: str
    customer_phone: str
    customer_email: str | None
    payment_method: str
    payment_reference: str | None
    subtotal: float
    igv_amount: float
    total: float
    status: str
    confirmed_at: datetime | None
    ready_at: datetime | None
    picked_up_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    items: list[OnlineOrderItemOut]

    model_config = ConfigDict(from_attributes=True)


class OnlineOrderCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: str | None = None
    payment_method: str = "EN_TIENDA"
    payment_reference: str | None = None
    items: list[OnlineOrderItemCreate]


class OnlineOrderPublicOut(BaseModel):
    """Minimal order info returned to the customer."""
    order_code: str
    status: str
    customer_name: str
    payment_method: str
    subtotal: float
    igv_amount: float
    total: float
    created_at: datetime
    confirmed_at: datetime | None
    ready_at: datetime | None
    picked_up_at: datetime | None
    items: list[OnlineOrderItemOut]

    model_config = ConfigDict(from_attributes=True)


class OnlineOrderStats(BaseModel):
    pendiente: int = 0
    confirmado: int = 0
    listo: int = 0
    recogido: int = 0
    cancelado: int = 0


class CancelRequest(BaseModel):
    reason: str
