import smtplib
from email.mime.text import MIMEText
from modules.database import get_email_config

def send_test_email():
    try:
        config = get_email_config()
        email_from = config.get("email_from", "").strip()
        email_pass = config.get("email_password", "").strip()
        email_dest = config.get("email_destino", "").strip()

        if not email_from or not email_pass:
            print("Error: No hay credenciales de email configuradas.")
            return

        if not email_dest:
            email_dest = "estudiodecomx@gmail.com"

        msg = MIMEText("¡Hola Diana! Este es un correo de prueba enviado desde tu sistema POS de Estudio Deco. Si estás leyendo esto, significa que la configuración de correo quedó correcta y el sistema ya puede enviar correos con los cortes de caja de forma automática.")
        msg["Subject"] = "Prueba de Correo - Estudio Deco POS"
        msg["From"] = email_from
        msg["To"] = email_dest

        print(f"Enviando correo de prueba de {email_from} a {email_dest}...")
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_from, email_pass)
            server.sendmail(email_from, email_dest, msg.as_string())
        
        print("¡Correo enviado exitosamente!")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

if __name__ == "__main__":
    send_test_email()
