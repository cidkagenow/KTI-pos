from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # DNI, RUC, NONE
    doc_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    ref_comercial: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    departamento: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    distrito: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ubigeo: Mapped[str | None] = mapped_column(String(6), nullable=True)
    zona: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    comentario: Mapped[str | None] = mapped_column(String(500), nullable=True)
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    credit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_walk_in: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, business_name='{self.business_name}')>"
