from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ruc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        back_populates="supplier"
    )

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, business_name='{self.business_name}')>"


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"), nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    doc_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # FACTURA, BOLETA
    doc_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    supplier_doc: Mapped[str | None] = mapped_column(String(50), nullable=True)
    condicion: Mapped[str | None] = mapped_column(String(20), default="CONTADO")  # CONTADO, CREDITO
    moneda: Mapped[str | None] = mapped_column(String(10), default="SOLES")
    tipo_cambio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    igv_included: Mapped[bool | None] = mapped_column(Boolean, default=True)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    igv_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    flete: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=0)
    grr_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    issue_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    warehouse: Mapped["Warehouse"] = relationship()  # noqa: F821
    creator: Mapped["User"] = relationship()  # noqa: F821
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<PurchaseOrder(id={self.id}, supplier_id={self.supplier_id}, "
            f"status='{self.status}')>"
        )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    discount_pct1: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=0)
    discount_pct2: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=0)
    discount_pct3: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=0)
    flete_unit: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<PurchaseOrderItem(id={self.id}, po_id={self.purchase_order_id}, "
            f"product_id={self.product_id}, qty={self.quantity})>"
        )
