import json
import logging
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.sale import Sale
from app.models.sunat import SunatDocument
from app.models.user import User
from app.schemas.sunat import (
    BajaRequest,
    ResumenRequest,
    SunatDocumentOut,
    SunatSaleStatus,
)
from app.services.sunat_service import (
    send_factura_to_sunat,
    send_nota_credito_to_sunat,
    send_resumen_to_sunat,
    send_baja_to_sunat,
    check_ticket_status,
)
from app.services.email_service import send_factura_email
from app.api.deps import get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter()


def _send_and_record_factura(sale: Sale, user: User, db: Session) -> SunatDocument:
    """Send a single factura to SUNAT and record the result."""
    parsed = send_factura_to_sunat(sale)

    # Check if there's an existing doc for this sale
    existing = (
        db.query(SunatDocument)
        .filter(SunatDocument.sale_id == sale.id, SunatDocument.doc_category == "FACTURA")
        .first()
    )

    now = datetime.now(timezone.utc)

    if existing:
        existing.sunat_status = parsed.get("sunat_status", "ERROR")
        existing.sunat_description = parsed.get("sunat_description")
        existing.sunat_hash = parsed.get("sunat_hash")
        existing.sunat_cdr_url = parsed.get("sunat_cdr_url")
        existing.sunat_xml_url = parsed.get("sunat_xml_url")
        existing.sunat_pdf_url = parsed.get("sunat_pdf_url")
        existing.ticket = parsed.get("ticket")
        existing.raw_request = ""
        existing.raw_response = json.dumps(parsed, ensure_ascii=False)
        existing.attempt_count += 1
        existing.last_attempt_at = now
        existing.sent_by = user.id
        doc = existing
    else:
        doc = SunatDocument(
            sale_id=sale.id,
            doc_category="FACTURA",
            reference_date=now,
            sunat_status=parsed.get("sunat_status", "ERROR"),
            sunat_description=parsed.get("sunat_description"),
            sunat_hash=parsed.get("sunat_hash"),
            sunat_cdr_url=parsed.get("sunat_cdr_url"),
            sunat_xml_url=parsed.get("sunat_xml_url"),
            sunat_pdf_url=parsed.get("sunat_pdf_url"),
            ticket=parsed.get("ticket"),
            raw_request="",
            raw_response=json.dumps(parsed, ensure_ascii=False),
            attempt_count=1,
            last_attempt_at=now,
            sent_by=user.id,
        )
        db.add(doc)

    db.flush()

    # Auto-email if ACEPTADO and client has email
    if doc.sunat_status == "ACEPTADO" and sale.client.email:
        try:
            send_factura_email(
                client_email=sale.client.email,
                client_name=sale.client.business_name,
                doc_series=sale.series,
                doc_number=sale.doc_number,
                pdf_url=doc.sunat_pdf_url or "",
                xml_url=doc.sunat_xml_url or "",
            )
        except Exception as e:
            logger.error("Email failed for sale %s: %s", sale.id, str(e))

    return doc


def _doc_to_out(doc: SunatDocument) -> SunatDocumentOut:
    sale = doc.sale
    return SunatDocumentOut(
        id=doc.id,
        sale_id=doc.sale_id,
        doc_category=doc.doc_category,
        reference_date=doc.reference_date,
        ticket=doc.ticket,
        sunat_status=doc.sunat_status,
        sunat_description=doc.sunat_description,
        sunat_hash=doc.sunat_hash,
        sunat_cdr_url=doc.sunat_cdr_url,
        sunat_xml_url=doc.sunat_xml_url,
        sunat_pdf_url=doc.sunat_pdf_url,
        attempt_count=doc.attempt_count,
        last_attempt_at=doc.last_attempt_at,
        sent_by=doc.sent_by,
        created_at=doc.created_at,
        doc_type=sale.doc_type if sale else None,
        series=sale.series if sale else None,
        doc_number=sale.doc_number if sale else None,
        client_name=sale.client.business_name if sale and sale.client else None,
        total=float(sale.total) if sale else None,
    )


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/facturas/{sale_id}/enviar", response_model=SunatDocumentOut)
def enviar_factura(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client))
        .filter(Sale.id == sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    if sale.status != "FACTURADO":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La venta debe estar FACTURADA")
    if sale.doc_type != "FACTURA":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo facturas se envian individualmente")

    doc = _send_and_record_factura(sale, current_user, db)
    db.commit()
    db.refresh(doc)
    return _doc_to_out(doc)


@router.post("/facturas/enviar-todas")
def enviar_todas_facturas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Send all pending facturas and NCs to SUNAT in bulk."""
    # Find FACTURA sales with PENDIENTE sunat status
    pending_factura_docs = (
        db.query(SunatDocument)
        .filter(
            SunatDocument.doc_category.in_(["FACTURA", "NOTA_CREDITO"]),
            SunatDocument.sunat_status == "PENDIENTE",
            SunatDocument.sale_id.isnot(None),
        )
        .all()
    )

    if not pending_factura_docs:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay facturas pendientes de envio")

    results = {"enviadas": 0, "aceptadas": 0, "rechazadas": 0, "errores": 0}

    for sunat_doc in pending_factura_docs:
        sale = (
            db.query(Sale)
            .options(joinedload(Sale.items), joinedload(Sale.client))
            .filter(Sale.id == sunat_doc.sale_id)
            .first()
        )
        if not sale:
            continue

        try:
            if sunat_doc.doc_category == "NOTA_CREDITO":
                doc = _send_and_record_nc(sale, current_user, db)
            else:
                doc = _send_and_record_factura(sale, current_user, db)
            db.flush()
            results["enviadas"] += 1
            if doc.sunat_status == "ACEPTADO":
                results["aceptadas"] += 1
            elif doc.sunat_status == "RECHAZADO":
                results["rechazadas"] += 1
            else:
                results["errores"] += 1
        except Exception as e:
            logger.error("Bulk send failed for sale %s: %s", sunat_doc.sale_id, str(e))
            results["errores"] += 1

    db.commit()
    return results


@router.post("/facturas/{sale_id}/reenviar", response_model=SunatDocumentOut)
def reenviar_factura(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items), joinedload(Sale.client))
        .filter(Sale.id == sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")

    existing = (
        db.query(SunatDocument)
        .filter(SunatDocument.sale_id == sale_id, SunatDocument.doc_category == "FACTURA")
        .first()
    )
    if existing and existing.sunat_status == "ACEPTADO":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La factura ya fue aceptada por SUNAT")

    doc = _send_and_record_factura(sale, current_user, db)
    db.commit()
    db.refresh(doc)
    return _doc_to_out(doc)


def _send_and_record_nc(sale: Sale, user: User, db: Session) -> SunatDocument:
    """Send a nota de credito to SUNAT and record the result."""
    parsed = send_nota_credito_to_sunat(sale)

    existing = (
        db.query(SunatDocument)
        .filter(SunatDocument.sale_id == sale.id, SunatDocument.doc_category == "NOTA_CREDITO")
        .first()
    )

    now = datetime.now(timezone.utc)

    if existing:
        existing.sunat_status = parsed.get("sunat_status", "ERROR")
        existing.sunat_description = parsed.get("sunat_description")
        existing.sunat_hash = parsed.get("sunat_hash")
        existing.sunat_cdr_url = parsed.get("sunat_cdr_url")
        existing.sunat_xml_url = parsed.get("sunat_xml_url")
        existing.sunat_pdf_url = parsed.get("sunat_pdf_url")
        existing.ticket = parsed.get("ticket")
        existing.raw_response = json.dumps(parsed, ensure_ascii=False)
        existing.attempt_count += 1
        existing.last_attempt_at = now
        existing.sent_by = user.id
        doc = existing
    else:
        doc = SunatDocument(
            sale_id=sale.id,
            doc_category="NOTA_CREDITO",
            reference_date=now,
            sunat_status=parsed.get("sunat_status", "ERROR"),
            sunat_description=parsed.get("sunat_description"),
            sunat_hash=parsed.get("sunat_hash"),
            sunat_cdr_url=parsed.get("sunat_cdr_url"),
            sunat_xml_url=parsed.get("sunat_xml_url"),
            sunat_pdf_url=parsed.get("sunat_pdf_url"),
            ticket=parsed.get("ticket"),
            raw_request="",
            raw_response=json.dumps(parsed, ensure_ascii=False),
            attempt_count=1,
            last_attempt_at=now,
            sent_by=user.id,
        )
        db.add(doc)

    db.flush()
    return doc


@router.post("/nota-credito/{sale_id}/enviar", response_model=SunatDocumentOut)
def enviar_nota_credito(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Send a nota de credito to SUNAT."""
    sale = (
        db.query(Sale)
        .options(
            joinedload(Sale.items),
            joinedload(Sale.client),
            joinedload(Sale.ref_sale),
        )
        .filter(Sale.id == sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nota de credito no encontrada")
    if sale.doc_type != "NOTA_CREDITO":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La venta no es una nota de credito")
    if sale.status != "FACTURADO":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La nota de credito debe estar FACTURADA")

    doc = _send_and_record_nc(sale, current_user, db)
    db.commit()
    db.refresh(doc)
    return _doc_to_out(doc)


def _get_pending_boletas(db: Session, fecha: date):
    """Get boletas pending to send to SUNAT for a given date.
    Returns (boletas_nuevas, boletas_anuladas) after filtering."""
    boletas_nuevas = (
        db.query(Sale)
        .options(joinedload(Sale.client))
        .filter(
            Sale.doc_type == "BOLETA",
            Sale.status == "FACTURADO",
            Sale.issue_date == fecha,
        )
        .all()
    )

    # Anuladas: no date filter — they can be sent in any resumen after acceptance
    boletas_anuladas = (
        db.query(Sale)
        .options(joinedload(Sale.client))
        .filter(
            Sale.doc_type == "BOLETA",
            Sale.status == "ANULADO",
        )
        .all()
    )

    # Filter out already sent nuevas (accepted or pending ticket)
    if boletas_nuevas:
        nueva_ids = [b.id for b in boletas_nuevas]
        already_sent_nueva_ids = set(
            row[0] for row in
            db.query(SunatDocument.sale_id)
            .filter(
                SunatDocument.sale_id.in_(nueva_ids),
                SunatDocument.doc_category == "RESUMEN",
                SunatDocument.sunat_status.in_(["ACEPTADO", "PENDIENTE"]),
            )
            .all()
        )
        boletas_nuevas = [b for b in boletas_nuevas if b.id not in already_sent_nueva_ids]

    # Filter anuladas: only include those whose original resumen was accepted
    # on a PREVIOUS day (same-day annulments = NO_ENVIADA, SUNAT never knew).
    # Also exclude already voided via resumen.
    today_start = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    if boletas_anuladas:
        anulada_ids = [b.id for b in boletas_anuladas]
        accepted_anulada_ids = set(
            row[0] for row in
            db.query(SunatDocument.sale_id)
            .filter(
                SunatDocument.sale_id.in_(anulada_ids),
                SunatDocument.doc_category == "RESUMEN",
                SunatDocument.sunat_status == "ACEPTADO",
                SunatDocument.last_attempt_at < today_start,
            )
            .all()
        )
        already_voided_ids = set(
            row[0] for row in
            db.query(SunatDocument.sale_id)
            .filter(
                SunatDocument.sale_id.in_(anulada_ids),
                SunatDocument.doc_category == "BAJA_RESUMEN",
                SunatDocument.sunat_status.in_(["ACEPTADO", "PENDIENTE"]),
            )
            .all()
        )
        boletas_anuladas = [
            b for b in boletas_anuladas
            if b.id in accepted_anulada_ids and b.id not in already_voided_ids
        ]

    return boletas_nuevas, boletas_anuladas


@router.get("/resumen-boletas/pendientes")
def get_pending_boletas_count(
    fecha: str = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get count of boletas pending to send to SUNAT for a given date."""
    try:
        fecha_date = date.fromisoformat(fecha)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de fecha invalido")
    nuevas, anuladas = _get_pending_boletas(db, fecha_date)
    return {"nuevas": len(nuevas), "anuladas": len(anuladas), "total": len(nuevas) + len(anuladas)}


@router.post("/resumen-boletas", response_model=SunatDocumentOut)
def enviar_resumen_boletas(
    data: ResumenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    try:
        fecha = date.fromisoformat(data.fecha)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Formato de fecha invalido (YYYY-MM-DD)")

    # Only apply 10 PM restriction when sending same-day resumen
    from zoneinfo import ZoneInfo
    lima_now = datetime.now(ZoneInfo("America/Lima"))
    if fecha == lima_now.date() and lima_now.hour < 22:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"El resumen diario de hoy solo se puede enviar a partir de las 10:00 PM. Hora actual: {lima_now.strftime('%I:%M %p')}",
        )

    boletas_nuevas, boletas_anuladas = _get_pending_boletas(db, fecha)

    # Combine all boletas with their condition codes
    boletas = boletas_nuevas + boletas_anuladas
    if not boletas:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No hay boletas pendientes de enviar ni anuladas para esa fecha",
        )

    condition_codes = {}
    for b in boletas_nuevas:
        condition_codes[b.id] = "1"  # Adicionar
    for b in boletas_anuladas:
        condition_codes[b.id] = "3"  # Anulado

    # Determine correlativo (count existing resumen docs for today)
    today = date.today()
    existing_count = (
        db.query(SunatDocument)
        .filter(
            SunatDocument.doc_category == "RESUMEN",
            SunatDocument.created_at >= datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
        )
        .count()
    )
    correlativo = existing_count + 1

    parsed = send_resumen_to_sunat(fecha, boletas, correlativo, condition_codes)

    now = datetime.now(timezone.utc)
    ref_date = datetime.combine(fecha, time(12, 0), tzinfo=timezone.utc)
    raw_resp = json.dumps(parsed, ensure_ascii=False)
    sunat_status = parsed.get("sunat_status", "ERROR")
    sunat_description = parsed.get("sunat_description")

    # Create a master resumen document (no sale_id)
    master_doc = SunatDocument(
        sale_id=None,
        doc_category="RESUMEN",
        reference_date=ref_date,
        sunat_status=sunat_status,
        sunat_description=sunat_description,
        sunat_hash=parsed.get("sunat_hash"),
        sunat_cdr_url=parsed.get("sunat_cdr_url"),
        sunat_xml_url=parsed.get("sunat_xml_url"),
        sunat_pdf_url=parsed.get("sunat_pdf_url"),
        ticket=parsed.get("ticket"),
        raw_request="",
        raw_response=raw_resp,
        attempt_count=1,
        last_attempt_at=now,
        sent_by=current_user.id,
    )
    db.add(master_doc)

    # Also link each boleta to a SUNAT document so sales list shows status
    for boleta in boletas:
        # Use BAJA_RESUMEN category for anuladas so we can track them separately
        is_anulada = condition_codes.get(boleta.id) == "3"
        boleta_doc = SunatDocument(
            sale_id=boleta.id,
            doc_category="BAJA_RESUMEN" if is_anulada else "RESUMEN",
            reference_date=ref_date,
            sunat_status=sunat_status,
            sunat_description=sunat_description,
            sunat_hash=parsed.get("sunat_hash"),
            ticket=parsed.get("ticket"),
            raw_request="",
            raw_response="",
            attempt_count=1,
            last_attempt_at=now,
            sent_by=current_user.id,
        )
        db.add(boleta_doc)

    db.commit()
    db.refresh(master_doc)
    return _doc_to_out(master_doc)


def _get_pending_baja_facturas(db: Session) -> list[Sale]:
    """Get ANULADO facturas that don't have an ACEPTADO or PENDIENTE baja."""
    already_sent_ids = (
        db.query(SunatDocument.sale_id)
        .filter(
            SunatDocument.doc_category == "BAJA",
            SunatDocument.sunat_status.in_(["ACEPTADO", "PENDIENTE"]),
        )
        .subquery()
    )
    return (
        db.query(Sale)
        .options(joinedload(Sale.client))
        .filter(
            Sale.status == "ANULADO",
            Sale.doc_type == "FACTURA",
            Sale.id.notin_(already_sent_ids),
        )
        .all()
    )


@router.get("/bajas/pendientes")
def get_pending_bajas(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    sales = _get_pending_baja_facturas(db)
    return {
        "total": len(sales),
        "data": [
            {
                "id": s.id,
                "doc_type": s.doc_type,
                "series": s.series,
                "doc_number": s.doc_number,
                "client_name": s.client.business_name if s.client else None,
                "total": float(s.total),
                "status": s.status,
            }
            for s in sales
        ],
    }


@router.post("/baja", response_model=SunatDocumentOut)
def enviar_baja(
    data: BajaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.client))
        .filter(Sale.id == data.sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    if sale.status != "ANULADO":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La venta debe estar ANULADA")
    if sale.doc_type != "FACTURA":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Solo facturas se pueden dar de baja. Las boletas se anulan via resumen diario.",
        )

    # Check if baja was already sent and accepted/pending
    existing_baja = (
        db.query(SunatDocument)
        .filter(
            SunatDocument.sale_id == sale.id,
            SunatDocument.doc_category == "BAJA",
            SunatDocument.sunat_status.in_(["ACEPTADO", "PENDIENTE"]),
        )
        .first()
    )
    if existing_baja:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Ya se envio baja para esta venta (estado: {existing_baja.sunat_status})",
        )

    # Determine correlativo (count existing baja docs for today)
    today = date.today()
    existing_count = (
        db.query(SunatDocument)
        .filter(
            SunatDocument.doc_category == "BAJA",
            SunatDocument.created_at >= datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
        )
        .count()
    )
    correlativo = existing_count + 1

    parsed = send_baja_to_sunat([sale], data.motivo, correlativo)

    now = datetime.now(timezone.utc)
    doc = SunatDocument(
        sale_id=sale.id,
        doc_category="BAJA",
        reference_date=now,
        sunat_status=parsed.get("sunat_status", "ERROR"),
        sunat_description=parsed.get("sunat_description"),
        sunat_hash=parsed.get("sunat_hash"),
        sunat_cdr_url=parsed.get("sunat_cdr_url"),
        sunat_xml_url=parsed.get("sunat_xml_url"),
        sunat_pdf_url=parsed.get("sunat_pdf_url"),
        ticket=parsed.get("ticket"),
        raw_request="",
        raw_response=json.dumps(parsed, ensure_ascii=False),
        attempt_count=1,
        last_attempt_at=now,
        sent_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_to_out(doc)


@router.post("/baja-masiva", response_model=SunatDocumentOut)
def enviar_baja_masiva(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Send Comunicacion de Baja for ALL pending anuladas facturas in one batch."""
    sales = _get_pending_baja_facturas(db)
    if not sales:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No hay facturas anuladas pendientes de baja",
        )

    today = date.today()
    existing_count = (
        db.query(SunatDocument)
        .filter(
            SunatDocument.doc_category == "BAJA",
            SunatDocument.created_at >= datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
        )
        .count()
    )
    correlativo = existing_count + 1

    parsed = send_baja_to_sunat(sales, "ANULACION DE OPERACION", correlativo)

    now = datetime.now(timezone.utc)
    # Create one master baja doc (sale_id=NULL) plus per-sale docs
    master_doc = SunatDocument(
        sale_id=None,
        doc_category="BAJA",
        reference_date=now,
        sunat_status=parsed.get("sunat_status", "ERROR"),
        sunat_description=parsed.get("sunat_description"),
        sunat_hash=parsed.get("sunat_hash"),
        sunat_cdr_url=parsed.get("sunat_cdr_url"),
        sunat_xml_url=parsed.get("sunat_xml_url"),
        sunat_pdf_url=parsed.get("sunat_pdf_url"),
        ticket=parsed.get("ticket"),
        raw_request="",
        raw_response=json.dumps(parsed, ensure_ascii=False),
        attempt_count=1,
        last_attempt_at=now,
        sent_by=current_user.id,
    )
    db.add(master_doc)
    db.flush()

    for sale in sales:
        per_sale_doc = SunatDocument(
            sale_id=sale.id,
            doc_category="BAJA",
            reference_date=now,
            sunat_status=parsed.get("sunat_status", "ERROR"),
            sunat_description=parsed.get("sunat_description"),
            ticket=parsed.get("ticket"),
            raw_request="",
            raw_response="",
            attempt_count=1,
            last_attempt_at=now,
            sent_by=current_user.id,
        )
        db.add(per_sale_doc)

    db.commit()
    db.refresh(master_doc)
    return _doc_to_out(master_doc)


@router.post("/ticket/{ticket}/status", response_model=SunatDocumentOut)
def consultar_ticket(
    ticket: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Check status of an async SUNAT operation by ticket number."""
    # Find the SunatDocument with this ticket
    doc = (
        db.query(SunatDocument)
        .options(joinedload(SunatDocument.sale).joinedload(Sale.client))
        .filter(SunatDocument.ticket == ticket)
        .first()
    )
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket no encontrado")

    if doc.sunat_status == "ACEPTADO":
        return _doc_to_out(doc)

    # Poll SUNAT
    parsed = check_ticket_status(ticket)

    if parsed.get("processing"):
        # Still processing — don't update DB, return current state
        return _doc_to_out(doc)

    # Update document with result
    now = datetime.now(timezone.utc)
    new_status = parsed.get("sunat_status", "ERROR")
    new_description = parsed.get("sunat_description")
    doc.sunat_status = new_status
    doc.sunat_description = new_description
    doc.sunat_cdr_url = parsed.get("sunat_cdr_url") or doc.sunat_cdr_url
    doc.last_attempt_at = now
    doc.attempt_count += 1

    # Also update all linked boleta documents with the same ticket
    linked_docs = (
        db.query(SunatDocument)
        .filter(SunatDocument.ticket == ticket, SunatDocument.id != doc.id)
        .all()
    )
    for linked in linked_docs:
        linked.sunat_status = new_status
        linked.sunat_description = new_description
        linked.last_attempt_at = now

    db.commit()
    db.refresh(doc)
    return _doc_to_out(doc)


@router.get("/resumen/{doc_id}/boletas")
def get_resumen_boletas(
    doc_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get the list of boletas included in a specific resumen."""
    master = db.query(SunatDocument).filter(SunatDocument.id == doc_id).first()
    if not master:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resumen no encontrado")
    if master.doc_category != "RESUMEN" or master.sale_id is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El documento no es un resumen maestro")

    # Find per-boleta docs linked by the same ticket
    linked_docs = (
        db.query(SunatDocument)
        .options(joinedload(SunatDocument.sale).joinedload(Sale.client))
        .filter(
            SunatDocument.ticket == master.ticket,
            SunatDocument.sale_id.isnot(None),
        )
        .all()
    )

    boletas = []
    for doc in linked_docs:
        sale = doc.sale
        if not sale:
            continue
        boletas.append({
            "sale_id": sale.id,
            "doc_number": f"{sale.series}-{str(sale.doc_number).zfill(7)}" if sale.doc_number else f"PRE-{sale.id}",
            "client_name": sale.client.business_name if sale.client else "",
            "total": float(sale.total),
            "condition": "Anulada" if doc.doc_category == "BAJA_RESUMEN" else "Nueva",
            "status": sale.status,
        })

    boletas.sort(key=lambda b: b["doc_number"])

    return {"boletas": boletas, "total": len(boletas)}


@router.get("/documentos", response_model=dict)
def list_sunat_documents(
    doc_category: str | None = Query(None),
    sunat_status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = (
        db.query(SunatDocument)
        .options(joinedload(SunatDocument.sale).joinedload(Sale.client))
    )
    if doc_category:
        query = query.filter(SunatDocument.doc_category == doc_category)
        # For RESUMEN lists, only show master records (not per-boleta links)
        if doc_category == "RESUMEN":
            query = query.filter(SunatDocument.sale_id.is_(None))
    if sunat_status:
        query = query.filter(SunatDocument.sunat_status == sunat_status)
    if date_from:
        query = query.filter(SunatDocument.created_at >= date_from)
    if date_to:
        query = query.filter(SunatDocument.created_at <= date_to + " 23:59:59")

    total = query.count()
    offset = (page - 1) * limit
    docs = query.order_by(SunatDocument.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "data": [_doc_to_out(d) for d in docs],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/documentos/sale/{sale_id}", response_model=SunatSaleStatus)
def get_sunat_for_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    doc = (
        db.query(SunatDocument)
        .filter(SunatDocument.sale_id == sale_id)
        .order_by(SunatDocument.created_at.desc())
        .first()
    )
    if not doc:
        return SunatSaleStatus()

    return SunatSaleStatus(
        sunat_status=doc.sunat_status,
        sunat_description=doc.sunat_description,
        sunat_pdf_url=doc.sunat_pdf_url,
        sunat_xml_url=doc.sunat_xml_url,
        sunat_cdr_url=doc.sunat_cdr_url,
    )
