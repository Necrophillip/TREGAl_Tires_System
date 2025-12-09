import sqlite3
import sys
import os
from datetime import datetime
from typing import List, Dict
from collections import Counter #

# --- LÓGICA DE RUTAS ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(BASE_DIR, "taller.db")

# --- FUNCIÓN DE MIGRACIÓN AUTOMÁTICA ---
def migrar_db_vehiculos():
    """Agrega columnas nuevas a la tabla vehiculos si no existen"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        columnas_nuevas = [
            "ALTER TABLE vehiculos ADD COLUMN num_economico TEXT",
            "ALTER TABLE vehiculos ADD COLUMN vin TEXT",
            "ALTER TABLE vehiculos ADD COLUMN kilometraje TEXT"
        ]
        for sql in columnas_nuevas:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError:
                pass 
        conn.commit()
    except Exception as e:
        print(f"Nota de migración: {e}")
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # TABLAS BASE
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, telefono TEXT, email TEXT, notas TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vehiculos (id INTEGER PRIMARY KEY AUTOINCREMENT, placas TEXT NOT NULL, modelo TEXT NOT NULL, anio INTEGER, color TEXT, cliente_id INTEGER NOT NULL, FOREIGN KEY(cliente_id) REFERENCES clientes(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicios (id INTEGER PRIMARY KEY AUTOINCREMENT, vehiculo_id INTEGER NOT NULL, fecha TEXT NOT NULL, descripcion TEXT NOT NULL, estado TEXT NOT NULL, costo_estimado REAL, ticket_id TEXT, cobrado_por INTEGER, fecha_cierre TEXT, FOREIGN KEY(vehiculo_id) REFERENCES vehiculos(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, descripcion TEXT NOT NULL, cantidad INTEGER DEFAULT 0, precio_venta REAL, categoria TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS trabajadores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, fecha_ingreso TEXT, estado TEXT DEFAULT 'Activo', sueldo_base REAL DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicio_detalles (id INTEGER PRIMARY KEY AUTOINCREMENT, servicio_id INTEGER NOT NULL, trabajador_id INTEGER NOT NULL, descripcion_tarea TEXT NOT NULL, costo_cobrado REAL NOT NULL, porcentaje_comision REAL, monto_comision REAL, fecha TEXT, FOREIGN KEY(servicio_id) REFERENCES servicios(id), FOREIGN KEY(trabajador_id) REFERENCES trabajadores(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicio_refacciones (id INTEGER PRIMARY KEY AUTOINCREMENT, servicio_id INTEGER NOT NULL, inventario_id INTEGER NOT NULL, cantidad INTEGER NOT NULL, precio_unitario REAL NOT NULL, subtotal REAL NOT NULL, FOREIGN KEY(servicio_id) REFERENCES servicios(id), FOREIGN KEY(inventario_id) REFERENCES inventario(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)''')
    
    # VALORES POR DEFECTO
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('min_stock', '5')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('meses_alerta', '6')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('expiracion_minutos', '10')")
    # EJECUTAMOS MIGRACIÓN
    migrar_db_vehiculos()

    conn.commit()
    conn.close()

# --- FUNCIONES DE CONFIGURACIÓN ---

def get_stock_minimo():
    conn = sqlite3.connect(DB_NAME)
    try:
        val = conn.cursor().execute("SELECT valor FROM configuracion WHERE clave='min_stock'").fetchone()
        limit = int(val[0]) if val else 5
    except: limit = 5
    conn.close()
    return limit

def set_stock_minimo(nuevo_limite):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('min_stock', ?)", (str(nuevo_limite),))
    conn.commit()
    conn.close()

def get_meses_alerta():
    """Obtiene umbral para alertas de servicio (Default: 6 meses)"""
    conn = sqlite3.connect(DB_NAME)
    try:
        val = conn.cursor().execute("SELECT valor FROM configuracion WHERE clave='meses_alerta'").fetchone()
        meses = int(val[0]) if val else 6
    except: meses = 6
    conn.close()
    return meses

def set_meses_alerta(meses):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('meses_alerta', ?)", (str(meses),))
    conn.commit()
    conn.close()

def get_tiempo_expiracion_minutos():
    """Obtiene el tiempo de expiración de la sesión en minutos (Default: 30)"""
    conn = sqlite3.connect(DB_NAME)
    try:
        val = conn.cursor().execute("SELECT valor FROM configuracion WHERE clave='expiracion_minutos'").fetchone()
        minutos = int(val[0]) if val else 30
    except:
        minutos = 30
    conn.close()
    return minutos

def set_tiempo_expiracion_minutos(minutos):
    """Guarda el tiempo de expiración de la sesión en minutos"""
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('expiracion_minutos', ?)", (str(minutos),))
    conn.commit()
    conn.close()

# --- GESTIÓN DE CLIENTES ---

def agregar_cliente(nombre, telefono, email, notas):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO clientes (nombre, telefono, email, notas) VALUES (?, ?, ?, ?)", (nombre, telefono, email, notas))
    conn.commit()
    conn.close()

def obtener_clientes():
    """Obtiene clientes calculando su estado de alerta de servicio"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    
    meses_limite = get_meses_alerta()
    
    sql = """
        SELECT c.id, c.nombre, c.telefono, c.email, c.notas,
               MAX(s.fecha_cierre) as ultimo_servicio
        FROM clientes c
        LEFT JOIN vehiculos v ON c.id = v.cliente_id
        LEFT JOIN servicios s ON v.id = s.vehiculo_id AND s.estado = 'Terminado'
        GROUP BY c.id
        ORDER BY ultimo_servicio DESC, c.id DESC
    """
    rows = conn.cursor().execute(sql).fetchall()
    conn.close()
    
    resultados = []
    hoy = datetime.now()
    
    for row in rows:
        d = dict(row)
        fecha_str = d['ultimo_servicio']
        
        d['status_alerta'] = 'Nuevo'
        d['ultimo_servicio_fmt'] = "-"

        if fecha_str:
            try:
                fecha_serv = datetime.strptime(fecha_str[:10], "%Y-%m-%d") 
                d['ultimo_servicio_fmt'] = fecha_str[:10]
                
                dias_pasados = (hoy - fecha_serv).days
                dias_limite = meses_limite * 30
                
                if dias_pasados > dias_limite:
                    d['status_alerta'] = f"⚠️ Vencido (+{meses_limite}m)"
                else:
                    d['status_alerta'] = "✅ Al día"
            except:
                d['status_alerta'] = "Error fecha"
                d['ultimo_servicio_fmt'] = fecha_str
        
        resultados.append(d)
        
    return resultados

def obtener_clientes_para_select():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.cursor().execute("SELECT * FROM clientes ORDER BY id DESC").fetchall()
    conn.close()
    return {c[0]: c[1] for c in rows}

# --- GESTIÓN DE VEHÍCULOS ---

def agregar_vehiculo(placas, modelo, anio, color, cliente_id, num_economico="", vin="", kilometraje=""):
    conn = sqlite3.connect(DB_NAME)
    sql = """
        INSERT INTO vehiculos (placas, modelo, anio, color, cliente_id, num_economico, vin, kilometraje) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn.cursor().execute(sql, (placas, modelo, anio, color, cliente_id, num_economico, vin, kilometraje))
    conn.commit()
    conn.close()

def obtener_vehiculos_con_dueno():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT v.id, v.placas, v.modelo, v.anio, v.color, 
               v.num_economico, v.vin, v.kilometraje,
               c.nombre as dueno_nombre 
        FROM vehiculos v 
        JOIN clientes c ON v.cliente_id = c.id 
        ORDER BY v.id DESC
    """
    rows = conn.cursor().execute(sql).fetchall()
    conn.close()
    
    resultado = []
    for row in rows:
        d = dict(row)
        d['num_economico'] = d['num_economico'] or '-'
        d['vin'] = d['vin'] or '-'
        d['kilometraje'] = d['kilometraje'] or '-'
        resultado.append(d)
    return resultado

def obtener_vehiculos_select_format():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT v.id, v.placas, v.modelo, c.nombre FROM vehiculos v JOIN clientes c ON v.cliente_id=c.id").fetchall()
    conn.close()
    return {v['id']: f"{v['placas']} - {v['modelo']} ({v['nombre']})" for v in rows}

# En Db/database.py, sección de Gestión de Clientes

def eliminar_cliente_por_id(cliente_id):
    """Elimina un cliente, sus vehículos asociados y los servicios/detalles relacionados."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # 1. Obtener IDs de vehículos del cliente
        vehiculo_ids = cursor.execute("SELECT id FROM vehiculos WHERE cliente_id = ?", (cliente_id,)).fetchall()
        
        if vehiculo_ids:
            ids_a_eliminar = tuple(vid[0] for vid in vehiculo_ids)
            placeholders = ','.join('?' for _ in ids_a_eliminar)

            # 2. Eliminar detalles de servicios (mano de obra/refacciones) asociados a esos vehículos
            # NOTA: Esto es complejo sin ON DELETE CASCADE, asumimos la estructura de la tabla servicios.
            cursor.execute(f"DELETE FROM servicio_detalles WHERE servicio_id IN (SELECT id FROM servicios WHERE vehiculo_id IN ({placeholders}))", ids_a_eliminar)
            cursor.execute(f"DELETE FROM servicio_refacciones WHERE servicio_id IN (SELECT id FROM servicios WHERE vehiculo_id IN ({placeholders}))", ids_a_eliminar)

            # 3. Eliminar servicios asociados a los vehículos
            cursor.execute(f"DELETE FROM servicios WHERE vehiculo_id IN ({placeholders})", ids_a_eliminar)

            # 4. Eliminar los vehículos
            cursor.execute(f"DELETE FROM vehiculos WHERE cliente_id IN ({placeholders})", (cliente_id,))
        
        # 5. Eliminar el cliente
        count = cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,)).rowcount
        conn.commit()
        
        if count == 0:
            return False, "Cliente no encontrado."
            
        return True, f"Cliente ID {cliente_id} y todos sus registros asociados han sido eliminados."
        
    except Exception as e:
        conn.rollback()
        return False, f"Error DB crítico al eliminar cliente: {str(e)}"
    finally:
        conn.close()
# --- GESTIÓN DE SERVICIOS Y PDF ---

def crear_servicio(vehiculo_id, descripcion, costo_inicial):
    conn = sqlite3.connect(DB_NAME)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.cursor().execute("INSERT INTO servicios (vehiculo_id, fecha, descripcion, estado, costo_estimado) VALUES (?, ?, ?, 'Pendiente', ?)", (vehiculo_id, fecha, descripcion, costo_inicial))
    conn.commit()
    conn.close()

def obtener_servicios_activos():
    """Consulta actualizada: SOLO retorna servicios con estado != 'Terminado'."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT s.id, s.fecha, s.descripcion, s.estado, s.costo_estimado, s.ticket_id, v.placas, v.modelo, c.nombre as dueno_nombre 
        FROM servicios s 
        JOIN vehiculos v ON s.vehiculo_id = v.id 
        JOIN clientes c ON v.cliente_id = c.id 
        WHERE s.estado != 'Terminado'  -- <--- ESTA ES LA CLÁUSULA CRÍTICA
        ORDER BY s.id DESC
    """
    rows = conn.cursor().execute(sql).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def obtener_servicios_terminados():
    """Retorna SOLAMENTE los servicios con estado = 'Terminado' (Historial)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT s.id, s.fecha_cierre, s.descripcion, s.estado, s.costo_estimado, s.ticket_id, v.placas, v.modelo, c.nombre as dueno_nombre 
        FROM servicios s 
        JOIN vehiculos v ON s.vehiculo_id = v.id 
        JOIN clientes c ON v.cliente_id = c.id 
        WHERE s.estado = 'Terminado' 
        ORDER BY s.fecha_cierre DESC
    """
    rows = conn.cursor().execute(sql).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def cerrar_servicio(servicio_id, ticket_id, trabajador_id, costo_final):
    conn = sqlite3.connect(DB_NAME)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.cursor().execute("UPDATE servicios SET estado='Terminado', ticket_id=?, cobrado_por=?, costo_estimado=?, fecha_cierre=? WHERE id=?", (ticket_id, trabajador_id, costo_final, fecha, servicio_id))
    conn.commit()
    conn.close()

def obtener_datos_completos_pdf(servicio_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sql_header = """
        SELECT s.id, s.fecha, 
               c.nombre as cliente, c.telefono, 
               v.modelo, v.anio, v.placas, v.color,
               v.num_economico, v.vin, v.kilometraje
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
    
    rows_mo = cursor.execute("SELECT descripcion_tarea as descripcion, costo_cobrado as total FROM servicio_detalles WHERE servicio_id = ?", (servicio_id,)).fetchall()
    for row in rows_mo:
        datos['items'].append({'cantidad': 1, 'descripcion': row['descripcion'], 'tipo': 'Mano de Obra', 'unitario': row['total'], 'total': row['total']})
        
    sql_ref = """
        SELECT i.descripcion, r.cantidad, r.precio_unitario, r.subtotal
        FROM servicio_refacciones r
        JOIN inventario i ON r.inventario_id = i.id
        WHERE r.servicio_id = ?
    """
    rows_ref = cursor.execute(sql_ref, (servicio_id,)).fetchall()
    for row in rows_ref:
        datos['items'].append({'cantidad': row['cantidad'], 'descripcion': row['descripcion'], 'tipo': 'Refacción', 'unitario': row['precio_unitario'], 'total': row['subtotal']})
        
    conn.close()
    return datos

def obtener_detalle_completo_servicio(servicio_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    tareas = cursor.execute("SELECT 'Mano de Obra' as tipo, descripcion_tarea as descripcion, 1 as cantidad, costo_cobrado as total FROM servicio_detalles WHERE servicio_id = ?", (servicio_id,)).fetchall()
    refacciones = cursor.execute("SELECT 'Refacción' as tipo, i.descripcion, r.cantidad, r.subtotal as total FROM servicio_refacciones r JOIN inventario i ON r.inventario_id = i.id WHERE r.servicio_id = ?", (servicio_id,)).fetchall()
    conn.close()
    return [dict(t) for t in tareas] + [dict(r) for r in refacciones]
# En Db/database.py (Buscar estas funciones y reemplazarlas)

def recalcular_total_servicio(servicio_id):
    """Calcula la suma de MO y Refacciones para un servicio ESPECÍFICO y actualiza su costo."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Sumamos el total para este servicio_id
    mo = cursor.execute("SELECT SUM(costo_cobrado) FROM servicio_detalles WHERE servicio_id = ?", (servicio_id,)).fetchone()[0] or 0.0
    ref = cursor.execute("SELECT SUM(subtotal) FROM servicio_refacciones WHERE servicio_id = ?", (servicio_id,)).fetchone()[0] or 0.0
    gran_total = mo + ref
    
    # 2. Corregido: Actualizamos el costo SÓLO donde el ID de servicio coincide.
    cursor.execute("UPDATE servicios SET costo_estimado = ? WHERE id = ?", (gran_total, servicio_id))
    
    conn.commit()
    conn.close()
    return gran_total

def agregar_tarea_comision(servicio_id, trabajador_id, descripcion, costo, porcentaje):
    """Agrega un detalle de MO y recalcula el costo total del servicio."""
    conn = sqlite3.connect(DB_NAME)
    monto = costo * (porcentaje / 100)
    fecha = datetime.now().strftime("%Y-%m-%d")
    conn.cursor().execute("INSERT INTO servicio_detalles (servicio_id, trabajador_id, descripcion_tarea, costo_cobrado, porcentaje_comision, monto_comision, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)", (servicio_id, trabajador_id, descripcion, costo, porcentaje, monto, fecha))
    conn.commit()
    conn.close()
    # Llama a la función corregida
    recalcular_total_servicio(servicio_id)

def agregar_refaccion_a_servicio(servicio_id, inventario_id, cantidad):
    """Agrega una refacción, descuenta inventario y recalcula el costo total del servicio."""
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
    # Llama a la función corregida
    recalcular_total_servicio(servicio_id)
    return True, f"Agregado: {cantidad}x {nombre}"

# En Db/database.py

def eliminar_servicio_por_id(servicio_id):
    """Elimina un servicio, sus detalles, y verifica si no está terminado."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # 1. Verificación de estado (para no eliminar cobrados)
        status = cursor.execute("SELECT estado FROM servicios WHERE id = ?", (servicio_id,)).fetchone()
        
        if status and status[0] == 'Terminado':
            return False, "Error: No se puede eliminar un servicio ya Terminado/Cobrado."

        # 2. Eliminar detalles relacionados primero (para evitar errores de FK)
        cursor.execute("DELETE FROM servicio_detalles WHERE servicio_id = ?", (servicio_id,))
        cursor.execute("DELETE FROM servicio_refacciones WHERE servicio_id = ?", (servicio_id,))
        
        # 3. Eliminar el servicio principal
        count = cursor.execute("DELETE FROM servicios WHERE id = ?", (servicio_id,)).rowcount
        
        conn.commit()
        if count == 0:
            return False, "Servicio no encontrado."
        
        return True, f"Servicio #{servicio_id} eliminado de la base de datos."
        
    except Exception as e:
        conn.rollback()
        return False, f"Error DB al eliminar servicio: {str(e)}"
    finally:
        conn.close()

# --- GESTIÓN DE INVENTARIO (CORREGIDA PARA UPSERT) ---

def obtener_producto_por_codigo(codigo):
    """Busca un producto y devuelve sus datos si existe"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    prod = conn.cursor().execute("SELECT * FROM inventario WHERE codigo = ?", (codigo,)).fetchone()
    conn.close()
    return dict(prod) if prod else None

def gestionar_producto(codigo, descripcion, cantidad_agregar, precio, categoria):
    """
    Lógica UPSERT:
    - Si existe: SUMA la cantidad al stock actual y actualiza datos (Descripción/Precio).
    - Si no existe: CREA el producto nuevo.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # 1. Verificamos si existe
        existente = cursor.execute("SELECT cantidad FROM inventario WHERE codigo = ?", (codigo,)).fetchone()
        
        if existente:
            # UPDATE: Sumamos la cantidad nueva a la existente
            stock_actual = existente[0]
            nuevo_total = stock_actual + cantidad_agregar
            
            cursor.execute("""
                UPDATE inventario 
                SET descripcion=?, cantidad=?, precio_venta=?, categoria=? 
                WHERE codigo=?
            """, (descripcion, nuevo_total, precio, categoria, codigo))
            
            msg = f"Actualizado: Stock {stock_actual} -> {nuevo_total}"
        else:
            # INSERT: Creamos nuevo
            cursor.execute("""
                INSERT INTO inventario (codigo, descripcion, cantidad, precio_venta, categoria) 
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, descripcion, cantidad_agregar, precio, categoria))
            msg = f"Producto nuevo registrado: {descripcion}"
            
        conn.commit()
        return True, msg
    except Exception as e:
        return False, f"Error DB: {str(e)}"
    finally:
        conn.close()

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
# En Db/database.py, al final de la sección de Inventario

def eliminar_producto_por_id(producto_id):
    """Elimina un producto del inventario por su ID."""
    conn = sqlite3.connect(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventario WHERE id = ?", (producto_id,))
        conn.commit()
        return True, "Producto eliminado correctamente."
    except Exception as e:
        return False, f"Error al eliminar: {str(e)}"
    finally:
        conn.close()

def obtener_productos_bajo_stock():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    limite = get_stock_minimo()
    rows = conn.cursor().execute("SELECT descripcion, cantidad FROM inventario WHERE cantidad < ? ORDER BY cantidad ASC LIMIT 10", (limite,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- GESTIÓN DE TRABAJADORES ---

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


# En Db/database.py

def obtener_estadisticas_trabajador(trabajador_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Datos del trabajador
    worker = cursor.execute("SELECT fecha_ingreso FROM trabajadores WHERE id=?", (trabajador_id,)).fetchone()
    fecha_ingreso = worker['fecha_ingreso'] if worker else None

    # 2. Datos financieros
    hoy = datetime.now().strftime("%Y-%m-%d")
    mes = datetime.now().strftime("%Y-%m")
    hoy_val = cursor.execute("SELECT SUM(monto_comision) FROM servicio_detalles WHERE trabajador_id=? AND fecha=?", (trabajador_id, hoy)).fetchone()[0] or 0
    mes_val = cursor.execute("SELECT SUM(monto_comision) FROM servicio_detalles WHERE trabajador_id=? AND fecha LIKE ?", (trabajador_id, f'{mes}%')).fetchone()[0] or 0
    
    # 3. Historial crudo (para tabla)
    hist = cursor.execute("SELECT descripcion_tarea, monto_comision, fecha FROM servicio_detalles WHERE trabajador_id=? ORDER BY id DESC LIMIT 10", (trabajador_id,)).fetchall()
    
    # =======================================================
    # 4. LÓGICA INTELIGENTE DE ESPECIALIDAD
    # =======================================================
    
    # --- LÍNEA AÑADIDA / CORREGIDA: Trae todas las tareas ---
    sql_desc = "SELECT descripcion_tarea FROM servicio_detalles WHERE trabajador_id = ?"
    all_tasks = cursor.execute(sql_desc, (trabajador_id,)).fetchall() # <--- ¡ESTO FALTABA!
    
    # Definimos categorías
    categorias = {
        'Frenos': ['freno', 'balata', 'disco', 'rectificado', 'caliper', 'abs'],
        # ... (resto de categorías, asumimos están definidas) ...
        'Motor': ['motor', 'banda', 'bujia', 'bujía', 'empaque', 'cabeza', 'piston', 'pistón'],
        'Afinación': ['afinacion', 'afinación', 'aceite', 'filtro', 'lavado', 'inyectores'],
        'Suspensión': ['suspension', 'suspensión', 'amortiguador', 'rotula', 'rótula', 'buje'],
        'Llantas': ['llanta', 'parche', 'rotacion', 'alineacion', 'balanceo', 'montaje'],
        'Eléctrico': ['electrico', 'eléctrico', 'bateria', 'batería', 'foco', 'alternador', 'marcha'],
        'Transmisión': ['transmision', 'caja', 'velocidades', 'clutch', 'embrague']
    }
    
    conteo_categorias = Counter()
    
    for row in all_tasks: 
        desc = row['descripcion_tarea'].lower()
        encontrado = False
        
        for cat_nombre, keywords in categorias.items():
            if any(k in desc for k in keywords):
                conteo_categorias[cat_nombre] += 1
                encontrado = True
                break
        
        if not encontrado:
            conteo_categorias['Varios'] += 1

    if conteo_categorias:
        especialidad = conteo_categorias.most_common(1)[0][0]
    else:
        especialidad = "Sin datos"

    conn.close()
    
    return {
        "fecha_ingreso": fecha_ingreso,
        "especialidad": especialidad,
        "hoy": hoy_val, 
        "mes": mes_val, 
        "historial": [dict(r) for r in hist]
    }

def obtener_resumen_mensual():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    mes = datetime.now().strftime("%Y-%m")
    limite = get_stock_minimo()
    cobrado = cursor.execute("SELECT SUM(costo_estimado) FROM servicios WHERE estado='Terminado' AND fecha_cierre LIKE ?", (f'{mes}%',)).fetchone()[0] or 0
    pendiente = cursor.execute("SELECT SUM(costo_estimado) FROM servicios WHERE estado!='Terminado' AND fecha LIKE ?", (f'{mes}%',)).fetchone()[0] or 0
    autos = cursor.execute("SELECT COUNT(*) FROM servicios WHERE estado!='Terminado'").fetchone()[0]
    stock = cursor.execute("SELECT COUNT(*) FROM inventario WHERE cantidad < ?", (limite,)).fetchone()[0]
    conn.close()
    return {"cobrado_mes": cobrado, "pendiente_mes": pendiente, "autos_activos": autos, "alertas_stock": stock}

def obtener_conteo_estados_servicios():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.cursor().execute("SELECT estado, COUNT(*) FROM servicios GROUP BY estado").fetchall()
    conn.close()
    return [{"name": row[0], "value": row[1]} for row in rows]