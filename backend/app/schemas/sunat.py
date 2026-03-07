from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SunatDocumentOut(BaseModel):
    id: int
    sale_id: int | None
    doc_category: str
    reference_date: datetime | None
    ticket: str | None
    sunat_status: str
    sunat_description: str | None
    sunat_hash: str | None
    sunat_cdr_url: str | None
    sunat_xml_url: str | None
    sunat_pdf_url: str | None
    attempt_count: int
    last_attempt_at: datetime | None
    sent_by: int | None
    created_at: datetime

    # extra joined fields
    doc_type: str | None = None
    series: str | None = None
    doc_number: int | None = None
    client_name: str | None = None
    total: float | None = None

    model_config = ConfigDict(from_attributes=True)


class ResumenRequest(BaseModel):
    fecha: str  # YYYY-MM-DD


class BajaRequest(BaseModel):
    sale_id: int
    motivo: str = "ANULACION DE OPERACION"


class SunatSaleStatus(BaseModel):
    """Lightweight SUNAT status for a specific sale."""
    sunat_status: str | None = None
    sunat_description: str | None = None
    sunat_pdf_url: str | None = None
    sunat_xml_url: str | None = None
    sunat_cdr_url: str | None = None
