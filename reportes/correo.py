"""Envío de correo por el relay SMTP de la empresa (smtp.txt).

El relay smtp-relay.gmail.com suele autenticar por IP (sin usuario/clave). Si se
definen SMTP_USER y SMTP_PASS en el entorno (.env), se hace login.
"""
from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "no_reply@americanad.com.ar")
FROM_NAME = os.getenv("SMTP_FROM_NAME", "American Advisor")


def enviar_mail(destinatario: str, asunto: str, cuerpo: str,
                adjuntos: list[tuple[str, bytes]] | None = None) -> None:
    """Envía un mail con adjuntos PDF. Lanza excepción si falla."""
    msg = EmailMessage()
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.set_content(cuerpo)
    for nombre, data in (adjuntos or []):
        msg.add_attachment(data, maintype="application", subtype="pdf", filename=nombre)

    user, pwd = os.getenv("SMTP_USER"), os.getenv("SMTP_PASS")
    ctx = ssl.create_default_context()
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx, timeout=30) as s:
            if user and pwd:
                s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as s:
            s.starttls(context=ctx)
            if user and pwd:
                s.login(user, pwd)
            s.send_message(msg)
