from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Trabajador(Base):
    __tablename__ = "trabajadores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dni: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cargo: Mapped[str] = mapped_column(String(30), nullable=False)  # VENDEDOR, ALMACEN, ADMINISTRACION, DELIVERY
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    asistencias: Mapped[list["Asistencia"]] = relationship(back_populates="trabajador")

    def __repr__(self) -> str:
        return f"<Trabajador(id={self.id}, name='{self.full_name}', cargo='{self.cargo}')>"


class Asistencia(Base):
    __tablename__ = "asistencias"
    __table_args__ = (
        UniqueConstraint("trabajador_id", "date", name="uq_asistencia_trabajador_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trabajador_id: Mapped[int] = mapped_column(
        ForeignKey("trabajadores.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # HH:MM
    check_out_time: Mapped[str | None] = mapped_column(String(5), nullable=True)  # HH:MM
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PRESENTE"
    )  # PRESENTE, AUSENTE, TARDANZA
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    trabajador: Mapped["Trabajador"] = relationship(back_populates="asistencias")

    def __repr__(self) -> str:
        return (
            f"<Asistencia(id={self.id}, trabajador_id={self.trabajador_id}, "
            f"date={self.date}, status='{self.status}')>"
        )
