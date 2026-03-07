"""
Email service — sends factura PDF+XML links to clients via Gmail SMTP.
"""
import logging
import smtplib
import time
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
