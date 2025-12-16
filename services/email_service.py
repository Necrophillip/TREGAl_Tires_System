import os
import resend
from dotenv import load_dotenv

# 1. Cargar las variables del archivo .env
load_dotenv() 

# 2. Configurar la API Key de Resend
resend.api_key = os.getenv("RESEND_API_KEY")

def enviar_correo_con_pdf(destinatario, asunto, cuerpo, ruta_pdf):
    # Validación de seguridad: Verificar que la llave exista
    if not resend.api_key:
        print("❌ Error: No se encontró RESEND_API_KEY en las variables de entorno.")
        return False, "Error de configuración servidor (Falta API Key)"

    try:
        # --- PREPARAR ADJUNTO (PDF) ---
        adjuntos = []
        if ruta_pdf and os.path.exists(ruta_pdf):
            nombre_archivo = os.path.basename(ruta_pdf)
            with open(ruta_pdf, "rb") as f:
                # Resend necesita una lista de bytes (números), no el objeto archivo
                lista_bytes = list(f.read())
                
            adjuntos.append({
                "filename": nombre_archivo,
                "content": lista_bytes
            })

        # --- ENVIAR CORREO (USANDO API RESEND) ---
        # NOTA: Esto usa el puerto 443 (HTTPS), por lo que NO se bloquea en DigitalOcean.
        
        params = {
            # ✅ MODO PROFESIONAL (Solo funciona si ya verificaste el dominio tregal.com.mx)
            "from": "TREGAL System <notificaciones@tregal.com.mx>", 
            
            # Si tu dominio aun NO está verde en Resend, usa esta línea en su lugar:
            # "from": "TREGAL System <onboarding@resend.dev>",
            
            "to": [destinatario],
            "subject": asunto,
            "html": cuerpo.replace('\n', '<br>'), # Convertir saltos de línea a HTML simple
            "attachments": adjuntos
        }

        email = resend.Emails.send(params)

        # --- VERIFICAR RESPUESTA ---
        if email.get("id"):
            return True, "Correo enviado exitosamente"
        else:
            return False, "No se recibió confirmación de envío"

    except Exception as e:
        print(f"❌ Error Resend: {e}")
        return False, f"Error API: {str(e)}"