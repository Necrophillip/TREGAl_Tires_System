import sqlite3  # <--- ESTA ES LA QUE TE FALTA
import sys      # <--- Esta es para el .exe
import os
from datetime import datetime
from typing import List, Dict

# --- LÓGICA CRÍTICA PARA WINDOWS ---
if getattr(sys, 'frozen', False):
    # Si es .exe, usa la carpeta donde está el archivo .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Si es script, usa la carpeta del archivo .py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(BASE_DIR, "taller.db")

# ... El resto del código sigue igual ...

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # TABLAS EXISTENTES
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, telefono TEXT, email TEXT, notas TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vehiculos (id INTEGER PRIMARY KEY AUTOINCREMENT, placas TEXT NOT NULL, modelo TEXT NOT NULL, anio INTEGER, color TEXT, cliente_id INTEGER NOT NULL, FOREIGN KEY(cliente_id) REFERENCES clientes(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicios (id INTEGER PRIMARY KEY AUTOINCREMENT, vehiculo_id INTEGER NOT NULL, fecha TEXT NOT NULL, descripcion TEXT NOT NULL, estado TEXT NOT NULL, costo_estimado REAL, ticket_id TEXT, cobrado_por INTEGER, fecha_cierre TEXT, FOREIGN KEY(vehiculo_id) REFERENCES vehiculos(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, descripcion TEXT NOT NULL, cantidad INTEGER DEFAULT 0, precio_venta REAL, categoria TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS trabajadores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, fecha_ingreso TEXT, estado TEXT DEFAULT 'Activo', sueldo_base REAL DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicio_detalles (id INTEGER PRIMARY KEY AUTOINCREMENT, servicio_id INTEGER NOT NULL, trabajador_id INTEGER NOT NULL, descripcion_tarea TEXT NOT NULL, costo_cobrado REAL NOT NULL, porcentaje_comision REAL, monto_comision REAL, fecha TEXT, FOREIGN KEY(servicio_id) REFERENCES servicios(id), FOREIGN KEY(trabajador_id) REFERENCES trabajadores(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicio_refacciones (id INTEGER PRIMARY KEY AUTOINCREMENT, servicio_id INTEGER NOT NULL, inventario_id INTEGER NOT NULL, cantidad INTEGER NOT NULL, precio_unitario REAL NOT NULL, subtotal REAL NOT NULL, FOREIGN KEY(servicio_id) REFERENCES servicios(id), FOREIGN KEY(inventario_id) REFERENCES inventario(id))''')
    
    # 8. NUEVA TABLA: CONFIGURACION (Para el stock minimo)
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)''')
    
    # Insertamos el valor por defecto (5) si no existe
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('min_stock', '5')")
    
    conn.commit()
    conn.close()

# --- FUNCIONES DE CONFIGURACION ---
def get_stock_minimo():
    conn = sqlite3.connect(DB_NAME)
    # Obtenemos el valor, si hay error devolvemos 5 por seguridad
    try:
        val = conn.cursor().execute("SELECT valor FROM configuracion WHERE clave='min_stock'").fetchone()
        limit = int(val[0]) if val else 5
    except:
        limit = 5
    conn.close()
    return limit

def set_stock_minimo(nuevo_limite):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('min_stock', ?)", (str(nuevo_limite),))
    conn.commit()
    conn.close()

# --- FUNCIONES MODIFICADAS PARA USAR EL LIMITE DINÁMICO ---

def obtener_resumen_mensual():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    mes = datetime.now().strftime("%Y-%m")
    
    # Obtenemos el limite configurado por el usuario
    limite = get_stock_minimo()
    
    cobrado = cursor.execute("SELECT SUM(costo_estimado) FROM servicios WHERE estado='Terminado' AND fecha_cierre LIKE ?", (f'{mes}%',)).fetchone()[0] or 0
    pendiente = cursor.execute("SELECT SUM(costo_estimado) FROM servicios WHERE estado!='Terminado' AND fecha LIKE ?", (f'{mes}%',)).fetchone()[0] or 0
    autos = cursor.execute("SELECT COUNT(*) FROM servicios WHERE estado!='Terminado'").fetchone()[0]
    
    # USAMOS EL LIMITE DINÁMICO AQUÍ
    stock = cursor.execute("SELECT COUNT(*) FROM inventario WHERE cantidad < ?", (limite,)).fetchone()[0]
    
    conn.close()
    return {"cobrado_mes": cobrado, "pendiente_mes": pendiente, "autos_activos": autos, "alertas_stock": stock}

def obtener_productos_bajo_stock():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    
    limite = get_stock_minimo()
    
    # USAMOS EL LIMITE DINÁMICO AQUÍ TAMBIÉN
    rows = conn.cursor().execute("SELECT descripcion, cantidad FROM inventario WHERE cantidad < ? ORDER BY cantidad ASC LIMIT 10", (limite,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- RESTO DE FUNCIONES (INTACTAS) ---
def recalcular_total_servicio(servicio_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    mo = cursor.execute("SELECT SUM(costo_cobrado) FROM servicio_detalles WHERE servicio_id = ?", (servicio_id,)).fetchone()[0] or 0.0
    ref = cursor.execute("SELECT SUM(subtotal) FROM servicio_refacciones WHERE servicio_id = ?", (servicio_id,)).fetchone()[0] or 0.0
    gran_total = mo + ref
    cursor.execute("UPDATE servicios SET costo_estimado = ? WHERE id = ?", (gran_total, servicio_id))
    conn.commit()
    conn.close()
    return gran_total

def agregar_tarea_comision(servicio_id, trabajador_id, descripcion, costo, porcentaje):
    conn = sqlite3.connect(DB_NAME)
    monto = costo * (porcentaje / 100)
    fecha = datetime.now().strftime("%Y-%m-%d")
    conn.cursor().execute("INSERT INTO servicio_detalles (servicio_id, trabajador_id, descripcion_tarea, costo_cobrado, porcentaje_comision, monto_comision, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)", (servicio_id, trabajador_id, descripcion, costo, porcentaje, monto, fecha))
    conn.commit()
    conn.close()
    recalcular_total_servicio(servicio_id)

def agregar_refaccion_a_servicio(servicio_id, inventario_id, cantidad):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    prod = cursor.execute("SELECT cantidad, precio_venta, descripcion FROM inventario WHERE id = ?", (inventario_id,)).fetchone()
    if not prod:
        conn.close()
        return False, "Producto no encontrado"
    stock_actual, precio, nombre = prod
    if stock_actual < cantidad:
        conn.close()
        return False, f"Stock insuficiente. Solo quedan {stock_actual}"
    nuevo_stock = stock_actual - cantidad
    cursor.execute("UPDATE inventario SET cantidad = ? WHERE id = ?", (nuevo_stock, inventario_id))
    subtotal = cantidad * precio
    cursor.execute("INSERT INTO servicio_refacciones (servicio_id, inventario_id, cantidad, precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)", (servicio_id, inventario_id, cantidad, precio, subtotal))
    conn.commit()
    conn.close()
    recalcular_total_servicio(servicio_id)
    return True, f"Agregado: {cantidad}x {nombre}"

def obtener_detalle_completo_servicio(servicio_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    tareas = cursor.execute("SELECT 'Mano de Obra' as tipo, descripcion_tarea as descripcion, 1 as cantidad, costo_cobrado as total FROM servicio_detalles WHERE servicio_id = ?", (servicio_id,)).fetchall()
    refacciones = cursor.execute("SELECT 'Refacción' as tipo, i.descripcion, r.cantidad, r.subtotal as total FROM servicio_refacciones r JOIN inventario i ON r.inventario_id = i.id WHERE r.servicio_id = ?", (servicio_id,)).fetchall()
    conn.close()
    return [dict(t) for t in tareas] + [dict(r) for r in refacciones]

def agregar_cliente(nombre, telefono, email, notas):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO clientes (nombre, telefono, email, notas) VALUES (?, ?, ?, ?)", (nombre, telefono, email, notas))
    conn.commit()
    conn.close()

def obtener_clientes():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT * FROM clientes ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def obtener_clientes_para_select():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.cursor().execute("SELECT * FROM clientes ORDER BY id DESC").fetchall()
    conn.close()
    return {c[0]: c[1] for c in rows}

def agregar_vehiculo(placas, modelo, anio, color, cliente_id):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO vehiculos (placas, modelo, anio, color, cliente_id) VALUES (?, ?, ?, ?, ?)", (placas, modelo, anio, color, cliente_id))
    conn.commit()
    conn.close()

def obtener_vehiculos_con_dueno():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    sql = "SELECT v.id, v.placas, v.modelo, v.anio, v.color, c.nombre as dueno_nombre FROM vehiculos v JOIN clientes c ON v.cliente_id = c.id ORDER BY v.id DESC"
    rows = conn.cursor().execute(sql).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def obtener_vehiculos_select_format():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT v.id, v.placas, v.modelo, c.nombre FROM vehiculos v JOIN clientes c ON v.cliente_id=c.id").fetchall()
    conn.close()
    return {v['id']: f"{v['placas']} - {v['modelo']} ({v['nombre']})" for v in rows}

def crear_servicio(vehiculo_id, descripcion, costo_inicial):
    conn = sqlite3.connect(DB_NAME)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.cursor().execute("INSERT INTO servicios (vehiculo_id, fecha, descripcion, estado, costo_estimado) VALUES (?, ?, ?, 'Pendiente', ?)", (vehiculo_id, fecha, descripcion, costo_inicial))
    conn.commit()
    conn.close()

def obtener_servicios_activos():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    sql = "SELECT s.id, s.fecha, s.descripcion, s.estado, s.costo_estimado, s.ticket_id, v.placas, v.modelo, c.nombre as dueno_nombre FROM servicios s JOIN vehiculos v ON s.vehiculo_id = v.id JOIN clientes c ON v.cliente_id = c.id ORDER BY s.id DESC"
    rows = conn.cursor().execute(sql).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def cerrar_servicio(servicio_id, ticket_id, trabajador_id, costo_final):
    conn = sqlite3.connect(DB_NAME)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.cursor().execute("UPDATE servicios SET estado='Terminado', ticket_id=?, cobrado_por=?, costo_estimado=?, fecha_cierre=? WHERE id=?", (ticket_id, trabajador_id, costo_final, fecha, servicio_id))
    conn.commit()
    conn.close()

def agregar_producto(codigo, descripcion, cantidad, precio, categoria):
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.cursor().execute("INSERT INTO inventario (codigo, descripcion, cantidad, precio_venta, categoria) VALUES (?, ?, ?, ?, ?)", (codigo, descripcion, cantidad, precio, categoria))
        conn.commit()
        return True, "OK"
    except: return False, "Error"

def obtener_inventario():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT * FROM inventario ORDER BY descripcion ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def obtener_inventario_select():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.cursor().execute("SELECT id, descripcion, cantidad, precio_venta FROM inventario WHERE cantidad > 0 ORDER BY descripcion").fetchall()
    conn.close()
    return {r[0]: f"{r[1]} (Stock: {r[2]}) - ${r[3]:,.2f}" for r in rows}

def obtener_conteo_estados_servicios():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.cursor().execute("SELECT estado, COUNT(*) FROM servicios GROUP BY estado").fetchall()
    conn.close()
    return [{"name": row[0], "value": row[1]} for row in rows]

def agregar_trabajador(nombre, fecha, sueldo):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO trabajadores (nombre, fecha_ingreso, estado, sueldo_base) VALUES (?, ?, 'Activo', ?)", (nombre, fecha, sueldo))
    conn.commit()
    conn.close()

def obtener_trabajadores_select():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.cursor().execute("SELECT id, nombre FROM trabajadores WHERE estado='Activo'").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def obtener_estadisticas_trabajador(trabajador_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    hoy = datetime.now().strftime("%Y-%m-%d")
    mes = datetime.now().strftime("%Y-%m")
    hoy_val = cursor.execute("SELECT SUM(monto_comision) FROM servicio_detalles WHERE trabajador_id=? AND fecha=?", (trabajador_id, hoy)).fetchone()[0] or 0
    mes_val = cursor.execute("SELECT SUM(monto_comision) FROM servicio_detalles WHERE trabajador_id=? AND fecha LIKE ?", (trabajador_id, f'{mes}%')).fetchone()[0] or 0
    hist = cursor.execute("SELECT descripcion_tarea, monto_comision, fecha FROM servicio_detalles WHERE trabajador_id=? ORDER BY id DESC LIMIT 10", (trabajador_id,)).fetchall()
    conn.close()
    return {"hoy": hoy_val, "mes": mes_val, "historial": [dict(r) for r in hist]}
# --- FUNCIÓN PARA EL PDF ---
def obtener_datos_completos_pdf(servicio_id):
    """Reúne toda la info para la cotización"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Info General (Servicio + Cliente + Auto)
    sql_header = """
        SELECT s.id, s.fecha, 
               c.nombre as cliente, c.telefono, 
               v.modelo, v.anio, v.placas, v.color
        FROM servicios s
        JOIN vehiculos v ON s.vehiculo_id = v.id
        JOIN clientes c ON v.cliente_id = c.id
        WHERE s.id = ?
    """
    header = cursor.execute(sql_header, (servicio_id,)).fetchone()
    
    if not header:
        conn.close()
        return None
    
    datos = dict(header)
    datos['items'] = []
    
    # 2. Mano de Obra
    sql_mo = "SELECT descripcion_tarea as descripcion, costo_cobrado as total FROM servicio_detalles WHERE servicio_id = ?"
    rows_mo = cursor.execute(sql_mo, (servicio_id,)).fetchall()
    for row in rows_mo:
        datos['items'].append({
            'cantidad': 1,
            'descripcion': row['descripcion'],
            'tipo': 'Mano de Obra',
            'unitario': row['total'],
            'total': row['total']
        })
        
    # 3. Refacciones
    sql_ref = """
        SELECT i.descripcion, r.cantidad, r.precio_unitario, r.subtotal
        FROM servicio_refacciones r
        JOIN inventario i ON r.inventario_id = i.id
        WHERE r.servicio_id = ?
    """
    rows_ref = cursor.execute(sql_ref, (servicio_id,)).fetchall()
    for row in rows_ref:
        datos['items'].append({
            'cantidad': row['cantidad'],
            'descripcion': row['descripcion'],
            'tipo': 'Refacción',
            'unitario': row['precio_unitario'],
            'total': row['subtotal']
        })
        
    conn.close()
    return datos