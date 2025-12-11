import sqlite3
import os

# --- CONFIGURACIÓN DE RUTAS ---
# Esto asegura que encuentre la DB sin importar desde dónde corras el script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "Db", "taller.db")

print(f"🔧 Iniciando Mantenimiento de Base de Datos en: {DB_NAME}")

def aplicar_todas_las_migraciones():
    if not os.path.exists(DB_NAME):
        print("❌ Error: No encuentro el archivo taller.db")
        print("   Asegúrate de haber ejecutado el sistema al menos una vez.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # ==========================================
        # 1. VEHÍCULOS Y USUARIOS (Base)
        # ==========================================
        print("\n--- 1. Verificando Estructura Base (Vehículos/Usuarios) ---")
        
        # Tabla Usuarios
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

        # Columnas extra para Vehículos
        cols_vehiculos = [
            "ALTER TABLE vehiculos ADD COLUMN num_economico TEXT",
            "ALTER TABLE vehiculos ADD COLUMN vin TEXT",
            "ALTER TABLE vehiculos ADD COLUMN kilometraje TEXT"
        ]
        for sql in cols_vehiculos:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError: pass # Ya existía

        # ==========================================
        # 2. CATÁLOGOS Y TRABAJADORES (Módulos 1 y 2)
        # ==========================================
        print("\n--- 2. Verificando Catálogos y Finanzas ---")
        
        # Tabla Catálogo Servicios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS catalogo_servicios (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                nombre TEXT NOT NULL UNIQUE, 
                descripcion TEXT, 
                precio_base REAL DEFAULT 0, 
                categoria TEXT DEFAULT 'General'
            )
        ''')
        
        # Inventario (Unidad de Medida)
        try:
            cursor.execute("ALTER TABLE inventario ADD COLUMN umo TEXT DEFAULT 'Pza'")
        except sqlite3.OperationalError: pass
        
        # Configuración Financiera Trabajadores
        cols_trabajadores = [
            "ALTER TABLE trabajadores ADD COLUMN esquema_pago TEXT DEFAULT 'mixto'", 
            "ALTER TABLE trabajadores ADD COLUMN pct_mano_obra REAL DEFAULT 0", 
            "ALTER TABLE trabajadores ADD COLUMN pct_refacciones REAL DEFAULT 0", 
            "ALTER TABLE trabajadores ADD COLUMN pago_fijo_servicio REAL DEFAULT 0"
        ]
        for sql in cols_trabajadores:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError: pass

        # ==========================================
        # 3. WORKFLOW Y REPORTES (Módulos 3 y 4)
        # ==========================================
        print("\n--- 3. Verificando Workflow y Reportes (CRÍTICO) ---")
        
        # Aquí están las columnas que causaban tu error:
        # fecha_cierre -> Para filtrar reportes por fecha
        # costo_final -> Para sumar dinero real cobrado
        # metodo_pago -> Para desglosar (Efectivo/Tarjeta)
        
        cols_servicios = [
            # Identificadores y Workflow
            "ALTER TABLE servicios ADD COLUMN uuid_publico TEXT",
            "ALTER TABLE servicios ADD COLUMN tecnico_asignado_id INTEGER",
            "ALTER TABLE servicios ADD COLUMN estatus_detalle TEXT DEFAULT 'En Cola'",
            "ALTER TABLE servicios ADD COLUMN log_tiempos TEXT",
            
            # Documentación de Venta
            "ALTER TABLE servicios ADD COLUMN tipo_doc TEXT DEFAULT 'Orden'", # Cotizacion vs Orden
            
            # Cierre y Cobro (Vital para Reports UI)
            "ALTER TABLE servicios ADD COLUMN metodo_pago TEXT",
            "ALTER TABLE servicios ADD COLUMN referencia_pago TEXT",
            "ALTER TABLE servicios ADD COLUMN fecha_cierre TEXT", 
            "ALTER TABLE servicios ADD COLUMN costo_final REAL DEFAULT 0"
        ]
        
        contador_nuevas = 0
        for sql in cols_servicios:
            try:
                cursor.execute(sql)
                col_name = sql.split('COLUMN')[1].strip().split(' ')[0]
                print(f"   ✅ Columna agregada: {col_name}")
                contador_nuevas += 1
            except sqlite3.OperationalError: 
                # Si falla es porque ya existe, lo ignoramos de forma segura
                pass

        if contador_nuevas == 0:
            print("   ⏩ Todas las columnas necesarias ya existían.")

        conn.commit()
        print("\n✨ MANTENIMIENTO FINALIZADO CON ÉXITO ✨")
        print("   Tu base de datos ahora soporta Reportes y Workflow.")
            
    except Exception as e:
        print(f"\n❌ Error crítico durante la migración: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    aplicar_todas_las_migraciones()
    # --- AGREGAR ESTO AL FINAL DE fix_db.py ---

def reparar_datos_historicos():
    print("\n--- 4. Reparando Datos Históricos (Backfill) ---")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # 1. Copiar costo_estimado a costo_final en servicios terminados que tengan 0
        cursor.execute("""
            UPDATE servicios 
            SET costo_final = costo_estimado 
            WHERE estado = 'Terminado' AND (costo_final IS NULL OR costo_final = 0)
        """)
        if cursor.rowcount > 0:
            print(f"   💰 Se corrigieron {cursor.rowcount} tickets antiguos con monto $0.")
        
        # 2. Asegurar que tengan fecha_cierre (si no tienen, usar la fecha de creación)
        cursor.execute("""
            UPDATE servicios 
            SET fecha_cierre = fecha 
            WHERE estado = 'Terminado' AND (fecha_cierre IS NULL OR fecha_cierre = '')
        """)
        if cursor.rowcount > 0:
            print(f"   📅 Se corrigieron {cursor.rowcount} fechas de cierre vacías.")

        # 3. Asignar 'Efectivo' por defecto a lo viejo
        cursor.execute("""
            UPDATE servicios 
            SET metodo_pago = 'Efectivo' 
            WHERE estado = 'Terminado' AND (metodo_pago IS NULL OR metodo_pago = '')
        """)
        
        conn.commit()
        print("   ✅ Datos históricos actualizados correctamente.")

    except Exception as e:
        print(f"   ❌ Error reparando datos: {e}")
    finally:
        conn.close()

# --- MODIFICAR LA EJECUCIÓN AL FINAL DEL ARCHIVO ---
if __name__ == "__main__":
    aplicar_todas_las_migraciones()
    reparar_datos_historicos()  # <--- ¡IMPORTANTE: AGREGA ESTA LÍNEA!