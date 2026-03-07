"""
SOAP client for SUNAT electronic invoicing.

Uses zeep with WS-Security to call SUNAT's billService operations:
- sendBill (sync, for facturas)
- sendSummary (async, for resumen diario and comunicacion de baja)
- getStatus (poll async result)
"""
import base64
import io
import logging
import zipfile
from lxml import etree

from zeep import Client
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
from requests import Session

from app.config import settings

logger = logging.getLogger(__name__)

# SUNAT endpoints
SUNAT_URLS = {
    "beta": "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService?wsdl",
    "production": "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService?wsdl",
}

# Cache SOAP client
_cached_client = None
_cached_env = None


def _get_soap_client() -> Client:
    """Get or create zeep SOAP client with WS-Security."""
    global _cached_client, _cached_env

    env = settings.SUNAT_ENV if settings.SUNAT_ENV in SUNAT_URLS else "beta"

    if _cached_client is not None and _cached_env == env:
        return _cached_client

    wsdl_url = SUNAT_URLS[env]
    ruc = settings.EMPRESA_RUC
    sol_user = settings.SUNAT_SOL_USER
    sol_password = settings.SUNAT_SOL_PASSWORD

    # Note: for beta, SUNAT_SOL_USER / SUNAT_SOL_PASSWORD from .env are used as-is

    # WS-Security username = RUC + SOL user
    ws_user = f"{ruc}{sol_user}"

    session = Session()
    session.verify = True
    transport = Transport(session=session, timeout=30, operation_timeout=30)

    client = Client(
        wsdl_url,
        wsse=UsernameToken(ws_user, sol_password),
        transport=transport,
    )

    _cached_client = client
    _cached_env = env
    logger.info("SOAP client created for env=%s, user=%s", env, ws_user)

    return client


def _zip_xml(xml_bytes: bytes, filename: str) -> bytes:
    """ZIP the XML file (SUNAT requires ZIP packaging)."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{filename}.xml", xml_bytes)
    return zip_buffer.getvalue()


def _parse_cdr(cdr_zip_bytes: bytes) -> dict:
    """
    Parse CDR (Constancia de Recepcion) from ZIP response.
    Returns dict with: code, description, accepted, cdr_xml.
    """
    try:
        zip_buffer = io.BytesIO(cdr_zip_bytes)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            # Find the .xml file (skip directories like dummy/)
            cdr_filename = None
            for name in zf.namelist():
                if name.lower().endswith(".xml"):
                    cdr_filename = name
                    break
            if not cdr_filename:
                cdr_filename = zf.namelist()[0]
            cdr_xml = zf.read(cdr_filename)

        # Parse CDR XML to extract response code and description
        root = etree.fromstring(cdr_xml)

        # Namespace for CDR
        ns = {
            "ar": "urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }

        # Try to find ResponseCode and Description
        response_code = None
        description = None

        # Search in DocumentResponse/Response
        for resp in root.iter():
            if resp.tag.endswith("}ResponseCode"):
                response_code = resp.text
            elif resp.tag.endswith("}Description") and response_code is not None:
                description = resp.text
                break

        code = response_code or "unknown"
        desc = description or "Sin descripcion"

        # Code 0 = accepted, codes 100-1999 = accepted with observations
        accepted = False
        if code.isdigit():
            code_int = int(code)
            accepted = code_int == 0 or (100 <= code_int <= 1999)

        return {
            "code": code,
            "description": desc,
            "accepted": accepted,
            "cdr_xml": cdr_xml,
        }

    except Exception as e:
        logger.error("Error parsing CDR: %s", str(e))
        return {
            "code": "error",
            "description": f"Error al parsear CDR: {str(e)}",
            "accepted": False,
            "cdr_xml": None,
        }


def send_bill(signed_xml: bytes, filename: str) -> dict:
    """
    Send a factura via sendBill (synchronous).
    Returns dict with: success, code, description, accepted, cdr_xml, cdr_zip.
    """
    client = _get_soap_client()

    zip_bytes = _zip_xml(signed_xml, filename)
    zip_filename = f"{filename}.zip"

    logger.info("sendBill → %s (%d bytes)", zip_filename, len(zip_bytes))

    try:
        # sendBill expects: fileName (string), contentFile (base64binary)
        # zeep handles base64 encoding for base64Binary fields — pass raw bytes
        result = client.service.sendBill(zip_filename, zip_bytes)

        if result is None:
            return {
                "success": False,
                "code": "null",
                "description": "SUNAT returned null response",
                "accepted": False,
            }

        # result is the CDR ZIP bytes
        cdr_zip_bytes = result if isinstance(result, bytes) else base64.b64decode(result)
        cdr = _parse_cdr(cdr_zip_bytes)

        logger.info("sendBill response: code=%s, desc=%s, accepted=%s",
                     cdr["code"], cdr["description"], cdr["accepted"])

        return {
            "success": True,
            "code": cdr["code"],
            "description": cdr["description"],
            "accepted": cdr["accepted"],
            "cdr_xml": cdr["cdr_xml"],
            "cdr_zip": cdr_zip_bytes,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error("sendBill error: %s", error_msg)

        # Try to extract SUNAT fault code from SOAP fault
        code = "error"
        if hasattr(e, "detail"):
            code = "soap_fault"

        return {
            "success": False,
            "code": code,
            "description": error_msg,
            "accepted": False,
        }


def send_summary(signed_xml: bytes, filename: str) -> dict:
    """
    Send resumen diario or comunicacion de baja via sendSummary (asynchronous).
    Returns dict with: success, ticket, description.
    """
    client = _get_soap_client()

    zip_bytes = _zip_xml(signed_xml, filename)
    zip_filename = f"{filename}.zip"

    logger.info("sendSummary → %s (%d bytes)", zip_filename, len(zip_bytes))

    try:
        # zeep handles base64 encoding — pass raw bytes
        result = client.service.sendSummary(zip_filename, zip_bytes)

        ticket = str(result) if result else None

        logger.info("sendSummary response: ticket=%s", ticket)

        return {
            "success": True,
            "ticket": ticket,
            "description": f"Ticket recibido: {ticket}",
        }

    except Exception as e:
        error_msg = str(e)
        logger.error("sendSummary error: %s", error_msg)

        return {
            "success": False,
            "ticket": None,
            "description": error_msg,
        }


def get_status(ticket: str) -> dict:
    """
    Poll async result via getStatus.
    Returns dict with: success, code, description, accepted, cdr_xml, cdr_zip, processing.
    """
    client = _get_soap_client()

    logger.info("getStatus → ticket=%s", ticket)

    try:
        result = client.service.getStatus(ticket)

        if result is None:
            return {
                "success": False,
                "processing": False,
                "code": "null",
                "description": "SUNAT returned null response",
                "accepted": False,
            }

        # getStatus returns a StatusResponse with statusCode and content
        status_code = None
        content = None

        if hasattr(result, "statusCode"):
            status_code = str(result.statusCode)
        elif hasattr(result, "status"):
            status_code = str(result.status)

        if hasattr(result, "content"):
            content = result.content

        # statusCode 98 or 99 = still processing
        if status_code in ("98", "99"):
            return {
                "success": True,
                "processing": True,
                "code": status_code,
                "description": "En proceso" if status_code == "98" else "En proceso (reintentar)",
                "accepted": False,
            }

        # statusCode 0 = done successfully, content has CDR ZIP
        # Any other code = error/rejection from SUNAT
        if status_code != "0":
            logger.warning("getStatus rejected: statusCode=%s", status_code)
            return {
                "success": True,
                "processing": False,
                "code": status_code or "unknown",
                "description": f"SUNAT rechazo el documento (codigo {status_code})",
                "accepted": False,
            }

        if content:
            cdr_zip_bytes = content if isinstance(content, bytes) else base64.b64decode(content)
            cdr = _parse_cdr(cdr_zip_bytes)

            logger.info("getStatus response: code=%s, desc=%s, accepted=%s",
                         cdr["code"], cdr["description"], cdr["accepted"])

            return {
                "success": True,
                "processing": False,
                "code": cdr["code"],
                "description": cdr["description"],
                "accepted": cdr["accepted"],
                "cdr_xml": cdr["cdr_xml"],
                "cdr_zip": cdr_zip_bytes,
            }

        return {
            "success": True,
            "processing": False,
            "code": status_code or "unknown",
            "description": f"Status code: {status_code}",
            "accepted": False,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error("getStatus error: %s", error_msg)

        return {
            "success": False,
            "processing": False,
            "code": "error",
            "description": error_msg,
            "accepted": False,
        }
