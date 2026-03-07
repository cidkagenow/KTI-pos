from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_inventory_product_warehouse"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    product: Mapped["Product"] = relationship()  # noqa: F821
    warehouse: Mapped["Warehouse"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Inventory(product_id={self.product_id}, "
            f"warehouse_id={self.warehouse_id}, qty={self.quantity})>"
        )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False
    )
    movement_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # SALE, PURCHASE, ADJUSTMENT, TRANSFER, VOID_RETURN
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    product: Mapped["Product"] = relationship()  # noqa: F821
    warehouse: Mapped["Warehouse"] = relationship()  # noqa: F821
    creator: Mapped["User"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<InventoryMovement(id={self.id}, type='{self.movement_type}', "
            f"product_id={self.product_id}, qty={self.quantity})>"
        )
