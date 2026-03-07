from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SunatDocument(Base):
    __tablename__ = "sunat_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales.id"), nullable=True
    )
    doc_category: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # FACTURA, RESUMEN, BAJA
    reference_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ticket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sunat_status: Mapped[str] = mapped_column(
        String(20), default="PENDIENTE"
    )  # PENDIENTE, ACEPTADO, RECHAZADO, ERROR
    sunat_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sunat_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sunat_cdr_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sunat_xml_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sunat_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sale: Mapped["Sale | None"] = relationship()  # noqa: F821
    sender: Mapped["User | None"] = relationship(foreign_keys=[sent_by])  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<SunatDocument(id={self.id}, category='{self.doc_category}', "
            f"status='{self.sunat_status}')>"
        )
