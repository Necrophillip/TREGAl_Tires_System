import os
import resend
from Db import database as db # <--- Importamos la DB para leer la configuración real

def enviar_correo_con_pdf(destinatario, asunto, cuerpo, ruta_pdf):
    # 1. OBTENER CREDENCIALES DE LA BASE DE DATOS (Lo que configuraste en el Dashboard)
    api_key = db.get_resend_api_key()
    remitente = db.get_email_remitente()

    # Validación
    if not api_key:
        print("❌ Error: Falta API Key en Configuración.")
        return False, "Error: Falta configurar API Key en el Dashboard"

    resend.api_key = api_key

    try:
        # --- PREPARAR ADJUNTO ---
        adjuntos = []
        if ruta_pdf and os.path.exists(ruta_pdf):
            nombre_archivo = os.path.basename(ruta_pdf)
            with open(ruta_pdf, "rb") as f:
                lista_bytes = list(f.read())
            adjuntos.append({
                "filename": nombre_archivo,
                "content": lista_bytes
            })

        # --- ENVIAR CORREO ---
        params = {
            "from": remitente, # <--- Usamos el correo que pusiste en el Dashboard (avisos@app.tregal...)
            "to": [destinatario],
            "subject": asunto,
            "html": cuerpo.replace('\n', '<br>'),
            "attachments": adjuntos
        }

        email = resend.Emails.send(params)

        if email.get("id"):
            return True, "Correo enviado exitosamente"
        else:
            return False, "No se recibió confirmación de envío"

    except Exception as e:
        print(f"❌ Error Resend: {e}")
        return False, f"Error API: {str(e)}"