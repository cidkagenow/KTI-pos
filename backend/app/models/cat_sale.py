"""CAT (Certificado contra Accidentes de Transito) sales tracking."""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, Numeric, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CatSale(Base):
    __tablename__ = "cat_sales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Certificate info
    certificate_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    serie: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Vehicle data
    placa: Mapped[str] = mapped_column(String(20), nullable=False)
    marca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    año: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serie_vehiculo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    asientos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(20), nullable=True)
    clase: Mapped[str | None] = mapped_column(String(50), nullable=True)
    uso: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Customer data
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_dni: Mapped[str | None] = mapped_column(String(20), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    customer_address: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Coverage dates
    fecha_desde: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fecha_hasta: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Pricing
    precio: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ap_extra: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="VENDIDO")  # VENDIDO, ANULADO

    # AFOCAT response
    pdf_cat_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    pdf_boleta_path: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Metadata
    sold_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
