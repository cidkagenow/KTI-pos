from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OnlineOrder(Base):
    __tablename__ = "online_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # Customer info
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Payment
    payment_method: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="EN_TIENDA"
    )
    payment_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Totals
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    igv_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="PENDIENTE"
    )

    # Tracking
    confirmed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ready_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Optional linkage to POS sale
    sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    items: Mapped[list["OnlineOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<OnlineOrder(id={self.id}, code='{self.order_code}', status='{self.status}')>"


class OnlineOrderItem(Base):
    __tablename__ = "online_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("online_orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Snapshots
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    presentation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    order: Mapped["OnlineOrder"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<OnlineOrderItem(id={self.id}, product='{self.product_name}', qty={self.quantity})>"
