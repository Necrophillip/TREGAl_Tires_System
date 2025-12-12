import sqlite3
import os
from datetime import datetime

# Localizar la base de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "Db", "taller.db")

def asegurar_sistema():
    if not os.path.exists(DB_NAME):
        print("❌ Error: No encuentro la base de datos.")
        return

    print("🛡️ --- PROTOCOLO DE SEGURIDAD: ELIMINAR ADMIN DEFAULT ---")
    print("⚠️  ADVERTENCIA: Vamos a crear un nuevo ADMIN antes de borrar al anterior.")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # 1. Pedir credenciales nuevas
        nuevo_user = input("\n👤 Ingresa el NUEVO usuario Admin (ej. jtrejo): ").strip()
        if not nuevo_user:
            print("❌ El usuario no puede estar vacío."); return

        # Verificar que no exista ya
        existe = cursor.execute("SELECT id FROM usuarios WHERE username=?", (nuevo_user,)).fetchone()
        if existe:
            print("❌ Ese usuario ya existe. Elige otro."); return

        nueva_pass = input(f"🔑 Ingresa la contraseña para '{nuevo_user}': ").strip()
        if len(nueva_pass) < 6:
            print("❌ La contraseña es muy corta (mínimo 6 caracteres)."); return

        # 2. Crear el nuevo Super Admin
        fecha = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO usuarios (username, password_hash, rol, creado_el) 
            VALUES (?, ?, 'admin', ?)
        """, (nuevo_user, nueva_pass, fecha))
        
        print(f"\n✅ Usuario '{nuevo_user}' creado exitosamente.")

        # 3. Eliminar al admin default
        cursor.execute("DELETE FROM usuarios WHERE username='admin'")
        
        if cursor.rowcount > 0:
            print("🗑️  Usuario 'admin' (default) ELIMINADO del sistema.")
        else:
            print("ℹ️  El usuario 'admin' ya no existía.")

        conn.commit()
        print("\n✨ SEGURIDAD APLICADA CORRECTAMENTE ✨")
        print(f"👉 Ahora inicia sesión con: {nuevo_user}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    asegurar_sistema()