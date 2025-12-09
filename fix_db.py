import sqlite3
import os

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