"""
Scheduled tasks for KTI-POS.

- Sends Resumen Diario (boletas) automatically every day at 11 PM Lima time.
- Sends pending facturas + NC-facturas automatically every day at 11 PM Lima time.
- Checks pending SUNAT tickets every 5 minutes.
"""

import json
import logging
from datetime import date, datetime, time, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models.sale import Sale
from app.models.sunat import SunatDocument
from app.models.sunat_settings import SunatSettings
from app.services.sunat_service import send_resumen_to_sunat, check_ticket_status


def _is_auto_send_enabled(db) -> bool:
    """Check if automatic SUNAT sending is enabled."""
    row = db.query(SunatSettings).filter(SunatSettings.id == 1).first()
    if not row:
        return True  # Default: enabled
    return row.auto_send_enabled

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="America/Lima")


def _get_pending_boletas_for_today(db):
    """Get new boletas for today + anuladas from previous days."""
    fecha = date.today()

    # New boletas for today
    boletas_nuevas = (
        db.query(Sale)
        .options(joinedload(Sale.client))
        .filter(Sale.doc_type == "BOLETA", Sale.status == "FACTURADO", Sale.issue_date == fecha)
        .all()
    )

    # Filter out already sent
    if boletas_nuevas:
        nueva_ids = [b.id for b in boletas_nuevas]
        already_sent = set(
            row[0] for row in
            db.query(SunatDocument.sale_id)
            .filter(
                SunatDocument.sale_id.in_(nueva_ids),
                SunatDocument.doc_category == "RESUMEN",
                SunatDocument.sunat_status.in_(["ACEPTADO", "PENDIENTE"]),
            )
            .all()
        )
        boletas_nuevas = [b for b in boletas_nuevas if b.id not in already_sent]

    # Anuladas from previous days (original resumen accepted before today)
    today_start = datetime.combine(fecha, time.min, tzinfo=timezone.utc)
    boletas_anuladas = (
        db.query(Sale)
        .options(joinedload(Sale.client))
        .filter(Sale.doc_type == "BOLETA", Sale.status == "ANULADO")
        .all()
    )

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


def send_resumen_diario_job():
    """Automatically send Resumen Diario at end of day."""
    logger.info("⏰ Resumen Diario automático: iniciando...")
    db = SessionLocal()
    try:
        if not _is_auto_send_enabled(db):
            logger.info("⏰ Resumen Diario: envío automático desactivado, omitiendo")
            return

        fecha = date.today()
        boletas_nuevas, boletas_anuladas = _get_pending_boletas_for_today(db)
        boletas = boletas_nuevas + boletas_anuladas

        if not boletas:
            logger.info("⏰ Resumen Diario: no hay boletas pendientes para %s", fecha)
            return

        condition_codes = {}
        for b in boletas_nuevas:
            condition_codes[b.id] = "1"
        for b in boletas_anuladas:
            condition_codes[b.id] = "3"

        # Correlativo
        existing_count = (
            db.query(SunatDocument)
            .filter(
                SunatDocument.doc_category == "RESUMEN",
                SunatDocument.created_at >= datetime.combine(fecha, time.min, tzinfo=timezone.utc),
            )
            .count()
        )
        correlativo = existing_count + 1

        logger.info(
            "⏰ Resumen Diario: enviando %d nuevas + %d anuladas (correlativo %d)",
            len(boletas_nuevas), len(boletas_anuladas), correlativo,
        )

        parsed = send_resumen_to_sunat(fecha, boletas, correlativo, condition_codes)

        now = datetime.now(timezone.utc)
        ref_date = datetime.combine(fecha, time(12, 0), tzinfo=timezone.utc)
        sunat_status = parsed.get("sunat_status", "ERROR")

        master_doc = SunatDocument(
            sale_id=None,
            doc_category="RESUMEN",
            reference_date=ref_date,
            sunat_status=sunat_status,
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
            sent_by=None,
        )
        db.add(master_doc)

        for boleta in boletas:
            is_anulada = condition_codes.get(boleta.id) == "3"
            boleta_doc = SunatDocument(
                sale_id=boleta.id,
                doc_category="BAJA_RESUMEN" if is_anulada else "RESUMEN",
                reference_date=ref_date,
                sunat_status=sunat_status,
                sunat_description=parsed.get("sunat_description"),
                sunat_hash=parsed.get("sunat_hash"),
                ticket=parsed.get("ticket"),
                raw_request="",
                raw_response="",
                attempt_count=1,
                last_attempt_at=now,
                sent_by=None,
            )
            db.add(boleta_doc)

        db.commit()
        logger.info("⏰ Resumen Diario enviado: %s (ticket: %s)", sunat_status, parsed.get("ticket"))

    except Exception:
        logger.exception("⏰ Error en Resumen Diario automático")
        db.rollback()
    finally:
        db.close()


MAX_RETRY_ATTEMPTS = 5


def send_pending_facturas_job():
    """Automatically send all pending/error facturas and NC-facturas to SUNAT at end of day.

    - PENDIENTE: new documents, first attempt
    - ERROR: failed previously (SUNAT down, timeout, etc.) — auto-retry up to MAX_RETRY_ATTEMPTS
    - RECHAZADO: XML problem — skip (needs manual fix)
    """
    logger.info("⏰ Envío automático de facturas: iniciando...")
    # Import here to avoid circular imports at module load time
    from app.api.sunat import _send_and_record_factura, _send_and_record_nc

    db = SessionLocal()
    try:
        if not _is_auto_send_enabled(db):
            logger.info("⏰ Facturas: envío automático desactivado, omitiendo")
            return

        pending_docs = (
            db.query(SunatDocument)
            .filter(
                SunatDocument.doc_category.in_(["FACTURA", "NOTA_CREDITO"]),
                SunatDocument.sunat_status.in_(["PENDIENTE", "ERROR"]),
                SunatDocument.sale_id.isnot(None),
                SunatDocument.attempt_count < MAX_RETRY_ATTEMPTS,
            )
            .all()
        )

        if not pending_docs:
            logger.info("⏰ Facturas: no hay facturas/NC pendientes de envío")
            return

        # For NC we only auto-send NC-facturas (F-series). NC-boletas go via Resumen Diario.
        count = {"factura": 0, "nc_factura": 0, "aceptadas": 0, "errores": 0, "reintentos": 0}

        for sunat_doc in pending_docs:
            sale = (
                db.query(Sale)
                .options(
                    joinedload(Sale.items),
                    joinedload(Sale.client),
                    joinedload(Sale.ref_sale).joinedload(Sale.client),
                )
                .filter(Sale.id == sunat_doc.sale_id)
                .first()
            )
            if not sale:
                continue

            is_retry = sunat_doc.sunat_status == "ERROR"

            try:
                if sunat_doc.doc_category == "NOTA_CREDITO":
                    # Only NC-facturas (F-series) go via sendBill; NC-boletas via Resumen
                    if not (sale.series or "").upper().startswith("F"):
                        continue
                    doc = _send_and_record_nc(sale, None, db)
                    count["nc_factura"] += 1
                else:
                    doc = _send_and_record_factura(sale, None, db)
                    count["factura"] += 1

                db.flush()
                if is_retry:
                    count["reintentos"] += 1
                if doc.sunat_status == "ACEPTADO":
                    count["aceptadas"] += 1
                else:
                    count["errores"] += 1
            except Exception:
                logger.exception("⏰ Error enviando factura/NC %s", sunat_doc.sale_id)
                count["errores"] += 1

        db.commit()
        logger.info(
            "⏰ Envío automático completado: %d facturas + %d NC (%d reintentos), %d aceptadas, %d errores",
            count["factura"], count["nc_factura"], count["reintentos"],
            count["aceptadas"], count["errores"],
        )
    except Exception:
        logger.exception("⏰ Error en envío automático de facturas")
        db.rollback()
    finally:
        db.close()


def check_pending_tickets_job():
    """Check status of pending SUNAT tickets (resumen/baja)."""
    db = SessionLocal()
    try:
        pending_docs = (
            db.query(SunatDocument)
            .filter(
                SunatDocument.sunat_status == "PENDIENTE",
                SunatDocument.ticket.isnot(None),
                SunatDocument.sale_id.is_(None),  # Only master docs
            )
            .all()
        )
        if not pending_docs:
            return

        for doc in pending_docs:
            try:
                result = check_ticket_status(doc.ticket)
                new_status = result.get("sunat_status", "PENDIENTE")
                if new_status != "PENDIENTE":
                    # Update master doc
                    doc.sunat_status = new_status
                    doc.sunat_description = result.get("sunat_description")
                    doc.sunat_cdr_url = result.get("sunat_cdr_url")
                    doc.last_attempt_at = datetime.now(timezone.utc)

                    # Update per-boleta/per-sale docs with same ticket
                    per_sale_docs = (
                        db.query(SunatDocument)
                        .filter(
                            SunatDocument.ticket == doc.ticket,
                            SunatDocument.sale_id.isnot(None),
                        )
                        .all()
                    )
                    for sd in per_sale_docs:
                        sd.sunat_status = new_status
                        sd.sunat_description = result.get("sunat_description")

                    logger.info("⏰ Ticket %s: %s", doc.ticket, new_status)
            except Exception:
                logger.exception("⏰ Error checking ticket %s", doc.ticket)

        db.commit()
    except Exception:
        logger.exception("⏰ Error en check_pending_tickets")
        db.rollback()
    finally:
        db.close()


def init_scheduler():
    """Start the scheduler with all jobs."""
    # Push dashboard stats every 60 seconds
    from app.services.dashboard_push import push_dashboard_stats

    scheduler.add_job(
        push_dashboard_stats,
        trigger="interval",
        seconds=60,
        id="dashboard_push",
        name="Push stats to dashboard",
        replace_existing=True,
    )

    # Send Resumen Diario (boletas) at 11:00 PM Lima time (every day)
    scheduler.add_job(
        send_resumen_diario_job,
        trigger=CronTrigger(hour=23, minute=0),
        id="resumen_diario",
        name="Enviar Resumen Diario",
        replace_existing=True,
    )

    # Send pending facturas + NC-facturas at 11:00 PM Lima time (every day)
    scheduler.add_job(
        send_pending_facturas_job,
        trigger=CronTrigger(hour=23, minute=0),
        id="facturas_auto",
        name="Enviar facturas pendientes",
        replace_existing=True,
    )

    # Check pending tickets every 5 minutes
    scheduler.add_job(
        check_pending_tickets_job,
        trigger="interval",
        minutes=5,
        id="check_tickets",
        name="Verificar tickets SUNAT pendientes",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "⏰ Scheduler iniciado: Resumen Diario + Facturas a las 23:00, tickets cada 5 min, dashboard push cada 60s"
    )


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("⏰ Scheduler detenido")
