import sqlite3
import os
import secrets
from datetime import datetime

# Buscamos la base de datos en la misma carpeta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "Db", "taller.db") # Asegúrate que la ruta a Db sea correcta

# Si tu estructura de carpetas tiene el .db en la raíz, usa esta línea en su lugar:
# DB_NAME = os.path.join(BASE_DIR, "taller.db") 

print(f"Intentando arreglar BD en: {DB_NAME}")

def reparar():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    columnas = [
        "ALTER TABLE vehiculos ADD COLUMN num_economico TEXT",
        "ALTER TABLE vehiculos ADD COLUMN vin TEXT",
        "ALTER TABLE vehiculos ADD COLUMN kilometraje TEXT"
    ]
    
    for sql in columnas:
        try:
            cursor.execute(sql)
            print(f"✅ Éxito ejecutando: {sql}")
        except sqlite3.OperationalError as e:
            print(f"⚠️ Aviso: {e} (Probablemente la columna ya existía)")
            
    conn.commit()
    conn.close()
    print("\n¡Base de datos reparada! Ahora intenta guardar el vehículo de nuevo.")

if __name__ == "__main__":
    reparar()
    
def aplicar_migracion_seguridad():
    if not os.path.exists(DB_NAME):
        print("❌ Error: No encuentro el archivo taller.db")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # 1. Crear tabla de USUARIOS (Si no existe)
        print("1️⃣ Verificando tabla 'usuarios'...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'tecnico',
                trabajador_id INTEGER,
                creado_el TEXT
            )
        ''')
        
        # 2. Agregar columnas de TRACKING a la tabla SERVICIOS
        print("2️⃣ Agregando columnas de tracking a 'servicios'...")
        columnas_nuevas = [
            "ALTER TABLE servicios ADD COLUMN uuid_publico TEXT",
            "ALTER TABLE servicios ADD COLUMN tecnico_asignado_id INTEGER",
            "ALTER TABLE servicios ADD COLUMN estatus_detalle TEXT DEFAULT 'En Cola'", 
            "ALTER TABLE servicios ADD COLUMN log_tiempos TEXT" 
        ]
        
        for sql in columnas_nuevas:
            try:
                cursor.execute(sql)
                print(f"   ✅ Columna agregada: {sql.split('COLUMN')[1]}")
            except sqlite3.OperationalError:
                print(f"   ⏩ {sql.split('COLUMN')[1]} ya existía.")

        # 3. Generar UUIDs para servicios viejos (Para que no den error)
        print("3️⃣ Generando links públicos para servicios existentes...")
        cursor.execute("SELECT id FROM servicios WHERE uuid_publico IS NULL")
        servicios_viejos = cursor.fetchall()
        for servicio in servicios_viejos:
            sid = servicio[0]
            nuevo_uuid = secrets.token_urlsafe(16)
            cursor.execute("UPDATE servicios SET uuid_publico = ? WHERE id = ?", (nuevo_uuid, sid))
        print(f"   🔄 Actualizados {len(servicios_viejos)} servicios antiguos.")

        # 4. Crear Usuario ADMIN por defecto (Si no existe)
        print("4️⃣ Verificando usuario Admin...")
        existe = cursor.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone()
        if not existe:
            fecha = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("INSERT INTO usuarios (username, password_hash, rol, creado_el) VALUES (?, ?, ?, ?)", 
                           ('admin', 'admin123', 'admin', fecha))
            print("   👤 Usuario 'admin' creado (Pass: admin123)")
        else:
            print("   ⏩ El usuario 'admin' ya existe.")

        conn.commit()
        print("\n✅ MANTENIMIENTO COMPLETADO EXITOSAMENTE.")
            
    except Exception as e:
        print(f"\n❌ Ocurrió un error crítico: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    aplicar_migracion_seguridad()