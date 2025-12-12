import smtplib
import os
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

# --- CONFIGURACIÓN (Idealmente usa variables de entorno) ---
SMTP_SERVER = 'smtp.gmail.com' # O smtp.office365.com para Outlook
SMTP_PORT = 587
EMAIL_REMITENTE = 'jaimitoandroid1@gmail.com' # <--- CAMBIA ESTO
EMAIL_PASSWORD = 'dfeevalhxinadqzt'  # <--- TU CONTRASEÑA DE APLICACIÓN

def enviar_correo_con_pdf(destinatario, asunto, cuerpo, ruta_pdf):
    if not destinatario or '@' not in destinatario:
        return False, "Correo inválido o inexistente"

    msg = MIMEMultipart()
    msg['From'] = EMAIL_REMITENTE
    msg['To'] = destinatario
    msg['Subject'] = asunto

    # Cuerpo del mensaje
    msg.attach(MIMEText(cuerpo, 'plain'))

    # Adjuntar PDF
    try:
        with open(ruta_pdf, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        nombre_archivo = os.path.basename(ruta_pdf)
        part.add_header('Content-Disposition', f'attachment; filename="{nombre_archivo}"')
        msg.attach(part)

        # Enviar
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_REMITENTE, EMAIL_PASSWORD)
            server.send_message(msg)
            
        return True, "Correo enviado exitosamente"
        
    except Exception as e:
        return False, f"Error SMTP: {str(e)}"