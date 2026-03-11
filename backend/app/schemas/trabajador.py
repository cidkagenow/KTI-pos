from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# ── Trabajador ───────────────────────────────────────────────────────

class TrabajadorCreate(BaseModel):
    full_name: str
    dni: str | None = None
    phone: str | None = None
    cargo: str


class TrabajadorUpdate(BaseModel):
    full_name: str | None = None
    dni: str | None = None
    phone: str | None = None
    cargo: str | None = None
    is_active: bool | None = None


class TrabajadorOut(BaseModel):
    id: int
    full_name: str
    dni: str | None
    phone: str | None
    cargo: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Asistencia ───────────────────────────────────────────────────────

class AsistenciaCreate(BaseModel):
    trabajador_id: int
    date: date
    check_in_time: str | None = None
    check_out_time: str | None = None
    status: str = "PRESENTE"
    notes: str | None = None


class AsistenciaUpdate(BaseModel):
    check_in_time: str | None = None
    check_out_time: str | None = None
    status: str | None = None
    notes: str | None = None


class AsistenciaOut(BaseModel):
    id: int
    trabajador_id: int
    trabajador_name: str
    date: date
    check_in_time: str | None
    check_out_time: str | None
    status: str
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Bulk Asistencia ──────────────────────────────────────────────────

class AsistenciaBulkItem(BaseModel):
    trabajador_id: int
    check_in_time: str | None = None
    check_out_time: str | None = None
    status: str = "PRESENTE"
    notes: str | None = None


class AsistenciaBulkCreate(BaseModel):
    date: date
    items: list[AsistenciaBulkItem]
