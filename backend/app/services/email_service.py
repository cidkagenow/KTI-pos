"""
Email service — sends factura PDF+XML links to clients via Gmail SMTP.
"""
import logging
import smtplib
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]  # seconds between retries


def send_factura_email(
    client_email: str,
    client_name: str,
    doc_series: str,
    doc_number: int,
    pdf_url: str,
    xml_url: str,
) -> bool:
    """
    Send factura PDF+XML links to client email.
    Returns True on success, False on failure.
    """
    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        logger.warning("SMTP not configured — skipping email for %s-%s", doc_series, doc_number)
        return False

    doc_id = f"{doc_series}-{str(doc_number).zfill(7)}"
    subject = f"Factura Electronica {doc_id} - {settings.EMPRESA_RAZON_SOCIAL}"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Factura Electronica {doc_id}</h2>
        <p>Estimado(a) <strong>{client_name}</strong>,</p>
        <p>Le hacemos llegar su comprobante electronico emitido por
           <strong>{settings.EMPRESA_RAZON_SOCIAL}</strong>
           (RUC: {settings.EMPRESA_RUC}).</p>
        <table style="margin: 20px 0;">
            <tr>
                <td style="padding: 8px 16px;">
                    <a href="{pdf_url}" style="color: #1a73e8;">Descargar PDF</a>
                </td>
            </tr>
            <tr>
                <td style="padding: 8px 16px;">
                    <a href="{xml_url}" style="color: #1a73e8;">Descargar XML</a>
                </td>
            </tr>
        </table>
        <p style="font-size: 12px; color: #888;">
            Este correo fue generado automaticamente. Por favor no responda a este mensaje.
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = client_email
    msg.attach(MIMEText(html, "html"))

    for attempt in range(MAX_RETRIES):
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Email sent to %s for factura %s", client_email, doc_id)
            return True
        except Exception as e:
            delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
            logger.warning(
                "Email attempt %d/%d failed for %s: %s. Retrying in %ds...",
                attempt + 1, MAX_RETRIES, client_email, str(e), delay,
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)

    logger.error("All %d email attempts failed for factura %s to %s", MAX_RETRIES, doc_id, client_email)
    return False


def send_registro_ventas_email(
    to_email: str,
    year: int,
    month: int,
    xlsx_bytes: bytes,
    filename: str,
) -> tuple[bool, str]:
    """
    Send the monthly Registro de Ventas Excel to the accountant.

    Returns (success, error_message). error_message is "" on success.
    """
    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        return False, "SMTP no está configurado en el servidor."

    if not to_email:
        return False, "Falta el correo de destino."

    months_es = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    period_label = f"{months_es[month]} {year}"

    subject = f"Registro de Ventas {period_label} - {settings.EMPRESA_RAZON_SOCIAL}"

    # Plain text version (spam filters like multipart/alternative)
    plain = (
        f"Hola,\n\n"
        f"Te envío el Registro de Ventas del período {period_label} "
        f"de {settings.EMPRESA_RAZON_SOCIAL} (RUC: {settings.EMPRESA_RUC}).\n\n"
        f"El archivo está adjunto: {filename}\n\n"
        f"Cualquier duda me avisas.\n\n"
        f"Saludos,\n"
        f"{settings.EMPRESA_RAZON_SOCIAL}\n"
    )

    html = f"""\
<!DOCTYPE html>
<html lang="es">
<body style="font-family: Arial, Helvetica, sans-serif; color: #222; max-width: 600px; margin: 0; padding: 20px;">
    <p>Hola,</p>
    <p>Te envío el <strong>Registro de Ventas</strong> del período <strong>{period_label}</strong>
       de <strong>{settings.EMPRESA_RAZON_SOCIAL}</strong> (RUC: {settings.EMPRESA_RUC}).</p>
    <p>El archivo está adjunto: <strong>{filename}</strong></p>
    <p>Cualquier duda me avisas.</p>
    <p>Saludos,<br>
    <strong>{settings.EMPRESA_RAZON_SOCIAL}</strong></p>
</body>
</html>
"""

    # multipart/mixed (root) → multipart/alternative (text+html) → attachment
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMPRESA_RAZON_SOCIAL} <{settings.SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Reply-To"] = settings.SMTP_EMAIL

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    # Attach the XLSX file
    attachment = MIMEApplication(
        xlsx_bytes,
        _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    last_error = ""
    for attempt in range(MAX_RETRIES):
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Registro de Ventas %s sent to %s", period_label, to_email)
            return True, ""
        except Exception as e:
            last_error = str(e)
            delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
            logger.warning(
                "Registro email attempt %d/%d failed for %s: %s",
                attempt + 1, MAX_RETRIES, to_email, last_error,
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)

    err = f"Error SMTP: {last_error}" if last_error else f"No se pudo enviar el correo después de {MAX_RETRIES} intentos."
    logger.error(err + f" Destino: {to_email}")
    return False, err
