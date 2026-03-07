from pydantic import BaseModel, ConfigDict


class ClientOut(BaseModel):
    id: int
    doc_type: str
    doc_number: str | None
    business_name: str
    ref_comercial: str | None
    address: str | None
    zona: str | None
    phone: str | None
    email: str | None
    comentario: str | None
    credit_limit: float | None
    credit_days: int | None
    is_walk_in: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ClientCreate(BaseModel):
    doc_type: str = "NONE"
    doc_number: str | None = None
    business_name: str
    ref_comercial: str | None = None
    address: str | None = None
    zona: str | None = None
    phone: str | None = None
    email: str | None = None
    comentario: str | None = None
    credit_limit: float | None = None
    credit_days: int | None = None


class ClientUpdate(BaseModel):
    doc_type: str | None = None
    doc_number: str | None = None
    business_name: str | None = None
    ref_comercial: str | None = None
    address: str | None = None
    zona: str | None = None
    phone: str | None = None
    email: str | None = None
    comentario: str | None = None
    credit_limit: float | None = None
    credit_days: int | None = None
    is_active: bool | None = None
