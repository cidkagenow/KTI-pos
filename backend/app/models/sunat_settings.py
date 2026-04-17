from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SunatSettings(Base):
    __tablename__ = "sunat_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auto_send_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    block_before_10pm: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    updater: Mapped["User | None"] = relationship(foreign_keys=[updated_by])  # noqa: F821
