from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Boolean,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentSeries(Base):
    __tablename__ = "document_series"
    __table_args__ = (
        UniqueConstraint("doc_type", "series", name="uq_docseries_type_series"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    series: Mapped[str] = mapped_column(String(10), nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    def __repr__(self) -> str:
        return (
            f"<DocumentSeries(doc_type='{self.doc_type}', "
            f"series='{self.series}', next={self.next_number})>"
        )


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint(
            "doc_type", "series", "doc_number", name="uq_sale_doc_identity"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    series: Mapped[str] = mapped_column(String(10), nullable=False)
    doc_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False
    )
    seller_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    trabajador_id: Mapped[int | None] = mapped_column(
        ForeignKey("trabajadores.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    payment_cond: Mapped[str] = mapped_column(String(20), default="CONTADO")
    payment_method: Mapped[str | None] = mapped_column(String(20), default="EFECTIVO")  # EFECTIVO, TARJETA, MIXTO
    cash_received: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cash_change: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=0)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    igv_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PREVENTA")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales.id"), nullable=True
    )
    nc_motivo_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    nc_motivo_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    voided_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )
    client: Mapped["Client"] = relationship()  # noqa: F821
    warehouse: Mapped["Warehouse"] = relationship()  # noqa: F821
    seller: Mapped["User | None"] = relationship(foreign_keys=[seller_id])  # noqa: F821
    trabajador: Mapped["Trabajador | None"] = relationship()  # noqa: F821
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821
    voider: Mapped["User | None"] = relationship(  # noqa: F821
        foreign_keys=[voided_by]
    )
    ref_sale: Mapped["Sale | None"] = relationship(
        remote_side="Sale.id", foreign_keys=[ref_sale_id]
    )

    def __repr__(self) -> str:
        return (
            f"<Sale(id={self.id}, doc='{self.doc_type}-{self.series}-{self.doc_number}', "
            f"total={self.total}, status='{self.status}')>"
        )


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    brand_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    presentation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    sale: Mapped["Sale"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<SaleItem(id={self.id}, sale_id={self.sale_id}, "
            f"product_id={self.product_id}, qty={self.quantity})>"
        )
