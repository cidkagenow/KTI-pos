"""
SUNAT direct integration — orchestrator.

Coordinates XML building → signing → SOAP sending → CDR parsing → file storage.
Replaces the previous APISUNAT Lucode REST integration.
"""
import hashlib
import logging
import os
from datetime import date
from pathlib import Path

from app.config import settings
from app.models.sale import Sale
from app.services.sunat_xml import (
    build_invoice_xml,
    build_summary_xml,
    build_voided_xml,
    get_invoice_filename,
    get_summary_filename,
    get_voided_filename,
)
from app.services.sunat_signer import sign_xml
from app.services.sunat_soap import send_bill, send_summary, get_status

logger = logging.getLogger(__name__)

# Local storage for XML and CDR files
SUNAT_FILES_DIR = Path(__file__).resolve().parent.parent.parent / "sunat_files"


def _ensure_dirs():
    """Create sunat_files directory structure if it doesn't exist."""
    (SUNAT_FILES_DIR / "xml").mkdir(parents=True, exist_ok=True)
    (SUNAT_FILES_DIR / "cdr").mkdir(parents=True, exist_ok=True)


def _save_xml(filename: str, xml_bytes: bytes) -> str:
    """Save signed XML to local file. Returns relative path."""
    _ensure_dirs()
    path = SUNAT_FILES_DIR / "xml" / f"{filename}.xml"
    path.write_bytes(xml_bytes)
    return str(path)


def _save_cdr(filename: str, cdr_xml: bytes) -> str:
    """Save CDR XML to local file. Returns relative path."""
    _ensure_dirs()
    path = SUNAT_FILES_DIR / "cdr" / f"R-{filename}.xml"
    path.write_bytes(cdr_xml)
    return str(path)


def _xml_hash(xml_bytes: bytes) -> str:
    """Compute SHA-256 hash of XML for reference."""
    return hashlib.sha256(xml_bytes).hexdigest()[:16]


def process_sunat_response(soap_result: dict, filename: str, signed_xml: bytes) -> dict:
    """
    Normalize SOAP response into our internal format compatible with SunatDocument model.

    Returns dict with: sunat_status, sunat_description, sunat_hash,
                       sunat_cdr_url, sunat_xml_url, sunat_pdf_url, ticket
    """
    xml_path = _save_xml(filename, signed_xml)

    if not soap_result.get("success"):
        return {
            "sunat_status": "ERROR",
            "sunat_description": soap_result.get("description", "Error desconocido"),
            "sunat_hash": "",
            "sunat_cdr_url": "",
            "sunat_xml_url": xml_path,
            "sunat_pdf_url": "",
            "ticket": soap_result.get("ticket", ""),
        }

    # Async response (sendSummary) — returns ticket
    if "ticket" in soap_result and soap_result.get("ticket"):
        return {
            "sunat_status": "PENDIENTE",
            "sunat_description": soap_result.get("description", ""),
            "sunat_hash": _xml_hash(signed_xml),
            "sunat_cdr_url": "",
            "sunat_xml_url": xml_path,
            "sunat_pdf_url": "",
            "ticket": soap_result["ticket"],
        }

    # Sync response (sendBill) — has CDR
    cdr_path = ""
    if soap_result.get("cdr_xml"):
        cdr_path = _save_cdr(filename, soap_result["cdr_xml"])

    accepted = soap_result.get("accepted", False)

    return {
        "sunat_status": "ACEPTADO" if accepted else "RECHAZADO",
        "sunat_description": soap_result.get("description", ""),
        "sunat_hash": _xml_hash(signed_xml),
        "sunat_cdr_url": cdr_path,
        "sunat_xml_url": xml_path,
        "sunat_pdf_url": "",
        "ticket": "",
    }


def send_factura_to_sunat(sale: Sale) -> dict:
    """
    Send a single factura or boleta to SUNAT via sendBill (synchronous).
    Returns normalized response dict.
    """
    filename = get_invoice_filename(sale)
    logger.info("Building invoice XML: %s", filename)

    xml_bytes = build_invoice_xml(sale)
    signed_xml = sign_xml(xml_bytes)
    soap_result = send_bill(signed_xml, filename)

    return process_sunat_response(soap_result, filename, signed_xml)


def send_resumen_to_sunat(fecha: date, sales: list[Sale], correlativo: int = 1,
                          condition_codes: dict[int, str] | None = None) -> dict:
    """
    Send resumen diario de boletas to SUNAT via sendSummary (asynchronous).
    condition_codes: dict mapping sale.id -> ConditionCode (1=Adicionar, 3=Anulado).
    Returns normalized response dict with ticket for polling.
    """
    filename = get_summary_filename(correlativo)
    logger.info("Building summary XML: %s (%d boletas)", filename, len(sales))

    xml_bytes = build_summary_xml(fecha, sales, correlativo, condition_codes)
    signed_xml = sign_xml(xml_bytes)
    soap_result = send_summary(signed_xml, filename)

    return process_sunat_response(soap_result, filename, signed_xml)


def send_baja_to_sunat(sales: list[Sale], motivo: str = "ANULACION DE OPERACION",
                       correlativo: int = 1) -> dict:
    """
    Send comunicacion de baja to SUNAT via sendSummary (asynchronous).
    Returns normalized response dict with ticket for polling.
    """
    filename = get_voided_filename(correlativo)
    fecha = sales[0].issue_date or date.today()
    logger.info("Building voided XML: %s (%d docs)", filename, len(sales))

    xml_bytes = build_voided_xml(fecha, sales, correlativo, motivo)
    signed_xml = sign_xml(xml_bytes)
    soap_result = send_summary(signed_xml, filename)

    return process_sunat_response(soap_result, filename, signed_xml)


def check_ticket_status(ticket: str) -> dict:
    """
    Check status of an async operation (resumen/baja) by ticket number.
    Returns normalized response dict.
    """
    logger.info("Checking ticket status: %s", ticket)
    soap_result = get_status(ticket)

    if soap_result.get("processing"):
        return {
            "sunat_status": "PENDIENTE",
            "sunat_description": soap_result.get("description", "En proceso"),
            "sunat_hash": "",
            "sunat_cdr_url": "",
            "sunat_xml_url": "",
            "sunat_pdf_url": "",
            "ticket": ticket,
            "processing": True,
        }

    # CDR received — save it
    cdr_path = ""
    if soap_result.get("cdr_xml"):
        cdr_path = _save_cdr(f"ticket-{ticket}", soap_result["cdr_xml"])

    accepted = soap_result.get("accepted", False)

    return {
        "sunat_status": "ACEPTADO" if accepted else "RECHAZADO",
        "sunat_description": soap_result.get("description", ""),
        "sunat_hash": "",
        "sunat_cdr_url": cdr_path,
        "sunat_xml_url": "",
        "sunat_pdf_url": "",
        "ticket": ticket,
        "processing": False,
    }
