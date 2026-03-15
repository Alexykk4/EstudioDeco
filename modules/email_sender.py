"""
modules/email_sender.py
Envía el PDF del corte de caja por correo electrónico usando Gmail SMTP.
"""

import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from datetime import date


def enviar_corte_email(pdf_path: str, resumen: dict, cajero: str,
                       callback_ok=None, callback_error=None):
    """
    Envía el PDF del corte por email en un hilo separado.
    callback_ok(msg) se llama si el envío es exitoso.
    callback_error(msg) se llama si hay error.
    """
    def _enviar():
        try:
            from modules.database import get_email_config
            config = get_email_config()

            email_from = config.get("email_from", "").strip()
            email_pass = config.get("email_password", "").strip()
            email_dest = config.get("email_destino", "").strip()

            if not email_from or not email_pass:
                if callback_error:
                    callback_error(
                        "No hay credenciales de email configuradas.\n"
                        "Configura email_from y email_password en la tabla config."
                    )
                return

            if not email_dest:
                email_dest = "estudiodecomx@gmail.com"

            fecha = resumen.get("fecha", date.today().strftime("%Y-%m-%d"))
            total = resumen.get("total_ventas", 0)
            num_ventas = resumen.get("num_ventas", 0)

            # Construir el mensaje
            msg = MIMEMultipart()
            msg["From"] = email_from
            msg["To"] = email_dest
            msg["Subject"] = f"Corte de Caja – {fecha}"

            body = (
                f"Corte de Caja – {fecha}\n"
                f"Cajero: {cajero}\n\n"
                f"Total Ventas: ${total:,.2f}\n"
                f"Número de Ventas: {num_ventas}\n\n"
                f"Se adjunta el PDF con el detalle completo."
            )
            msg.attach(MIMEText(body, "plain"))

            # Adjuntar PDF
            pdf_file = Path(pdf_path)
            if pdf_file.exists():
                with open(pdf_file, "rb") as f:
                    part = MIMEBase("application", "pdf")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={pdf_file.name}",
                    )
                    msg.attach(part)

            # Enviar via Gmail SMTP
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(email_from, email_pass)
                server.sendmail(email_from, email_dest, msg.as_string())

            if callback_ok:
                callback_ok(f"Correo enviado a {email_dest}")

        except Exception as e:
            if callback_error:
                callback_error(f"Error al enviar email: {e}")

    hilo = threading.Thread(target=_enviar, daemon=True)
    hilo.start()


def enviar_notificacion_email(asunto: str, cuerpo: str):
    """
    Envía un email de notificación simple (sin adjuntos) en un hilo separado.
    Usado para notificar ingresos y gastos.
    """
    def _enviar():
        try:
            from modules.database import get_email_config
            config = get_email_config()

            email_from = config.get("email_from", "").strip()
            email_pass = config.get("email_password", "").strip()
            email_dest = config.get("email_destino", "").strip()

            if not email_from or not email_pass:
                print("[EMAIL] No hay credenciales configuradas, omitiendo notificación.")
                return

            if not email_dest:
                email_dest = "estudiodecomx@gmail.com"

            msg = MIMEMultipart()
            msg["From"] = email_from
            msg["To"] = email_dest
            msg["Subject"] = asunto
            msg.attach(MIMEText(cuerpo, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(email_from, email_pass)
                server.sendmail(email_from, email_dest, msg.as_string())

            print(f"[EMAIL] Notificación enviada: {asunto}")
        except Exception as e:
            print(f"[EMAIL] Error notificación: {e}")

    hilo = threading.Thread(target=_enviar, daemon=True)
    hilo.start()
