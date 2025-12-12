import smtplib

# 1. PON TU CORREO EXACTO AQUÍ
USUARIO = 'jaimitoandroid1@gmail.com'.strip()

# 2. PEGA LA NUEVA CONTRASEÑA AQUÍ (Sin espacios manuales)
PASSWORD = 'pegacomobiene'.strip()  # El .strip() quitará espacios si se colaron

print(f"🔒 Probando autenticación para: {USUARIO}")
print(f"🔑 Longitud de contraseña: {len(PASSWORD)} (Debe ser 16)")

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(USUARIO, PASSWORD)
    print("✅ ¡ÉXITO TOTAL! Gmail te dejó pasar.")
    server.quit()
except Exception as e:
    print("❌ Sigue fallando. Error exacto:")
    print(e)