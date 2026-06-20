"""Servicio de envío de emails vía SMTP."""
import os
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger("app")


def _smtp_configurado() -> bool:
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    return bool(user) and bool(password)


def enviar_codigo(destinatario: str, codigo: str) -> bool:
    """Envía el código de acceso por email. Retorna True si se envió, False si falló."""
    if not _smtp_configurado():
        logger.info(f"[CODIGO] (modo consola) Email={destinatario} | Codigo={codigo}")
        return False

    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")

    msg = MIMEText(f"Tu codigo de acceso es: {codigo}\n\nEste codigo expira en 5 minutos.")
    msg["Subject"] = "Tu codigo de acceso - ListaMasterInsumos"
    msg["From"] = user
    msg["To"] = destinatario

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        logger.info(f"[EMAIL] Codigo enviado a {destinatario}")
        return True
    except Exception as e:
        logger.warning(f"[EMAIL] Fallo al enviar a {destinatario}: {e}")
        logger.info(f"[CODIGO] (fallback consola) Email={destinatario} | Codigo={codigo}")
        return False
