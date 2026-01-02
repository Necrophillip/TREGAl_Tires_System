import sqlite3
import sys
import os
import secrets
from datetime import datetime, timedelta
from typing import List, Dict
from collections import Counter

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(BASE_DIR, "taller.db")

# ==========================================
# 1. MIGRACIONES (Schema)
# ==========================================
# (Se mantienen las funciones de migración para referencia, aunque fix_db es el ejecutor principal)
def init_db():
    # Inicializador básico para nuevas instalaciones
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    # Tablas Base
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, telefono TEXT, email TEXT, notas TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vehiculos (id INTEGER PRIMARY KEY AUTOINCREMENT, placas TEXT, modelo TEXT, anio INTEGER, color TEXT, cliente_id INTEGER, num_economico TEXT, vin TEXT, kilometraje TEXT)''')
    # Tabla Servicios Actualizada RC3
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, vehiculo_id INTEGER, fecha TEXT, descripcion TEXT, 
        estado TEXT, costo_estimado REAL, ticket_id TEXT, cobrado_por INTEGER, fecha_cierre TEXT, 
        uuid_publico TEXT, estatus_detalle TEXT, tecnico_asignado_id INTEGER, log_tiempos TEXT,
        tipo_doc TEXT DEFAULT 'Orden', metodo_pago TEXT, referencia_pago TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, descripcion TEXT, cantidad INTEGER, precio_venta REAL, categoria TEXT, umo TEXT DEFAULT 'Pza')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS trabajadores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha_ingreso TEXT, estado TEXT, sueldo_base REAL, esquema_pago TEXT, pct_mano_obra REAL, pct_refacciones REAL, pago_fijo_servicio REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicio_detalles (id INTEGER PRIMARY KEY AUTOINCREMENT, servicio_id INTEGER, trabajador_id INTEGER, descripcion_tarea TEXT, costo_cobrado REAL, porcentaje_comision REAL, monto_comision REAL, fecha TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS servicio_refacciones (id INTEGER PRIMARY KEY AUTOINCREMENT, servicio_id INTEGER, inventario_id INTEGER, cantidad INTEGER, precio_unitario REAL, subtotal REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_hash TEXT, rol TEXT, trabajador_id INTEGER, creado_el TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS catalogo_servicios (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, descripcion TEXT, precio_base REAL, categoria TEXT)''')
    
    # Defaults Config
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('min_stock', '5')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('meses_alerta', '6')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('expiracion_minutos', '30')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_iva', '16')")
    
    # Admin Default
    if not cursor.execute("SELECT id FROM usuarios WHERE username='admin'").fetchone():
        cursor.execute("INSERT INTO usuarios (username, password_hash, rol, creado_el) VALUES (?, ?, ?, ?)", ('admin', 'admin123', 'admin', datetime.now().strftime("%Y-%m-%d")))
    
    conn.commit(); conn.close()

# ==========================================
# 2. CONFIGURACIÓN
# ==========================================
def get_config_value(clave, default):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    try: val = cursor.execute("SELECT valor FROM configuracion WHERE clave=?", (clave,)).fetchone(); return val[0] if val else default
    except: return default
    finally: conn.close()

def set_config_value(clave, valor):
    conn = sqlite3.connect(DB_NAME); conn.cursor().execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)", (clave, str(valor))); conn.commit(); conn.close()

def get_stock_minimo(): return int(get_config_value('min_stock', 5))
def set_stock_minimo(val): set_config_value('min_stock', val)
def get_meses_alerta(): return int(get_config_value('meses_alerta', 6))
def set_meses_alerta(val): set_config_value('meses_alerta', val)
def get_tiempo_expiracion_minutos(): return int(get_config_value('expiracion_minutos', 30))
def set_tiempo_expiracion_minutos(val): set_config_value('expiracion_minutos', val)
def get_whatsapp_taller(): return get_config_value('whatsapp_taller', '5215555555555')
def set_whatsapp_taller(num): set_config_value('whatsapp_taller', ''.join(filter(str.isdigit, str(num))))
def get_tasa_iva(): return float(get_config_value('tasa_iva', 0.0))
def set_tasa_iva(val): set_config_value('tasa_iva', val)

# ==========================================
# 3. CATÁLOGOS E INVENTARIO
# ==========================================
def crear_servicio_catalogo(nombre, precio, categoria, descripcion=""):
    conn = sqlite3.connect(DB_NAME)
    try: conn.cursor().execute("INSERT INTO catalogo_servicios (nombre, precio_base, categoria, descripcion) VALUES (?, ?, ?, ?)", (nombre, precio, categoria, descripcion)); conn.commit(); return True, "Registrado"
    except Exception as e: return False, str(e)
    finally: conn.close()

def obtener_catalogo_servicios():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT * FROM catalogo_servicios ORDER BY nombre").fetchall(); conn.close()
    return [dict(r) for r in rows]

def eliminar_servicio_catalogo(sid):
    conn = sqlite3.connect(DB_NAME); conn.cursor().execute("DELETE FROM catalogo_servicios WHERE id=?", (sid,)); conn.commit(); conn.close()

def obtener_servicios_para_select():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.cursor().execute("SELECT id, nombre, precio_base FROM catalogo_servicios ORDER BY nombre").fetchall(); conn.close()
    return {r[0]: f"{r[1]} - ${r[2]:,.2f}" for r in rows}

def gestionar_producto(codigo, descripcion, cantidad_agregar, precio, categoria, umo='Pza'):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    try:
        existente = cursor.execute("SELECT cantidad FROM inventario WHERE codigo = ?", (codigo,)).fetchone()
        if existente:
            cursor.execute("UPDATE inventario SET descripcion=?, cantidad=?, precio_venta=?, categoria=?, umo=? WHERE codigo=?", (descripcion, existente[0] + cantidad_agregar, precio, categoria, umo, codigo))
            msg = "Stock actualizado"
        else:
            cursor.execute("INSERT INTO inventario (codigo, descripcion, cantidad, precio_venta, categoria, umo) VALUES (?, ?, ?, ?, ?, ?)", (codigo, descripcion, cantidad_agregar, precio, categoria, umo))
            msg = "Producto registrado"
        conn.commit(); return True, msg
    except Exception as e: return False, str(e)
    finally: conn.close()

def obtener_inventario():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT * FROM inventario ORDER BY descripcion ASC").fetchall(); conn.close()
    return [dict(row) for row in rows]

def obtener_producto_por_codigo(codigo):
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    prod = conn.cursor().execute("SELECT * FROM inventario WHERE codigo = ?", (codigo,)).fetchone(); conn.close()
    return dict(prod) if prod else None

def obtener_inventario_select():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.cursor().execute("SELECT id, descripcion, cantidad, precio_venta, umo FROM inventario WHERE cantidad > 0 ORDER BY descripcion").fetchall(); conn.close()
    return {r[0]: f"{r[1]} (Stock: {r[2]} {r[4] if len(r)>4 else 'Pza'}) - ${r[3]:,.2f}" for r in rows}

def eliminar_producto_por_id(pid):
    conn = sqlite3.connect(DB_NAME)
    try: conn.cursor().execute("DELETE FROM inventario WHERE id = ?", (pid,)); conn.commit(); return True, "Eliminado"
    except Exception as e: return False, str(e)
    finally: conn.close()

# ==========================================
# 4. SEGURIDAD Y USUARIOS
# ==========================================
def verificar_credenciales(u, p):
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    user = conn.cursor().execute("SELECT * FROM usuarios WHERE username=?", (u,)).fetchone(); conn.close()
    if user and user['password_hash'] == p: return dict(user)
    return None

def crear_usuario(u, p, r, tid=None):
    conn = sqlite3.connect(DB_NAME)
    try: conn.cursor().execute("INSERT INTO usuarios (username, password_hash, rol, trabajador_id, creado_el) VALUES (?,?,?,?,?)", (u, p, r, tid, datetime.now().strftime("%Y-%m-%d"))); conn.commit(); return True, "Creado"
    except: return False, "Usuario existente"
    finally: conn.close()

def obtener_usuarios():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT id, username, rol, trabajador_id, creado_el FROM usuarios").fetchall(); conn.close()
    return [dict(r) for r in rows]

def eliminar_usuario(uid):
    conn = sqlite3.connect(DB_NAME); conn.cursor().execute("DELETE FROM usuarios WHERE id=?", (uid,)); conn.commit(); conn.close()

# ==========================================
# 5. CLIENTES Y VEHICULOS
# ==========================================
def agregar_cliente(n, t, e, no):
    conn = sqlite3.connect(DB_NAME); conn.cursor().execute("INSERT INTO clientes (nombre, telefono, email, notas) VALUES (?,?,?,?)", (n, t, e, no)); conn.commit(); conn.close()

def obtener_clientes():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    meses = get_meses_alerta()
    rows = conn.cursor().execute("SELECT c.id, c.nombre, c.telefono, c.email, c.notas, MAX(s.fecha_cierre) as ultimo_servicio FROM clientes c LEFT JOIN vehiculos v ON c.id=v.cliente_id LEFT JOIN servicios s ON v.id=s.vehiculo_id AND s.estado='Terminado' GROUP BY c.id ORDER BY ultimo_servicio DESC, c.id DESC").fetchall(); conn.close()
    res = []
    hoy = datetime.now()
    for row in rows:
        d = dict(row); d['status_alerta'] = 'Nuevo'; d['ultimo_servicio_fmt'] = "-"
        if d['ultimo_servicio']:
            try:
                dt = datetime.strptime(d['ultimo_servicio'][:10], "%Y-%m-%d")
                d['ultimo_servicio_fmt'] = d['ultimo_servicio'][:10]
                if (hoy - dt).days > (meses * 30): d['status_alerta'] = f"⚠️ Vencido (+{meses}m)"
                else: d['status_alerta'] = "✅ Al día"
            except: pass
        res.append(d)
    return res

def obtener_clientes_para_select():
    conn = sqlite3.connect(DB_NAME); rows = conn.cursor().execute("SELECT id, nombre FROM clientes ORDER BY id DESC").fetchall(); conn.close()
    return {r[0]: r[1] for r in rows}

def eliminar_cliente_por_id(cid):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    try:
        vids = cursor.execute("SELECT id FROM vehiculos WHERE cliente_id=?", (cid,)).fetchall()
        if vids:
            ids = tuple(v[0] for v in vids); p = ','.join('?'*len(ids))
            cursor.execute(f"DELETE FROM servicio_detalles WHERE servicio_id IN (SELECT id FROM servicios WHERE vehiculo_id IN ({p}))", ids)
            cursor.execute(f"DELETE FROM servicio_refacciones WHERE servicio_id IN (SELECT id FROM servicios WHERE vehiculo_id IN ({p}))", ids)
            cursor.execute(f"DELETE FROM servicios WHERE vehiculo_id IN ({p})", ids)
            cursor.execute(f"DELETE FROM vehiculos WHERE cliente_id=?", (cid,))
        if cursor.execute("DELETE FROM clientes WHERE id=?", (cid,)).rowcount == 0: return False, "No encontrado"
        conn.commit(); return True, "Eliminado"
    except Exception as e: conn.rollback(); return False, str(e)
    finally: conn.close()

def agregar_vehiculo(placas, modelo, anio, color, cid, num="", vin="", km=""):
    conn = sqlite3.connect(DB_NAME); conn.cursor().execute("INSERT INTO vehiculos (placas, modelo, anio, color, cliente_id, num_economico, vin, kilometraje) VALUES (?,?,?,?,?,?,?,?)", (placas, modelo, anio, color, cid, num, vin, km)); conn.commit(); conn.close()

def obtener_vehiculos_con_dueno():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("SELECT v.*, c.nombre as dueno_nombre FROM vehiculos v JOIN clientes c ON v.cliente_id=c.id ORDER BY v.id DESC").fetchall(); conn.close()
    res = []
    for r in rows:
        d = dict(r)
        for k in ['num_economico', 'vin', 'kilometraje']: d[k] = d[k] or '-'
        res.append(d)
    return res

def obtener_vehiculos_select_format():
    conn = sqlite3.connect(DB_NAME); rows = conn.cursor().execute("SELECT v.id, v.placas, v.modelo, c.nombre FROM vehiculos v JOIN clientes c ON v.cliente_id=c.id").fetchall(); conn.close()
    return {r[0]: f"{r[1]} - {r[2]} ({r[3]})" for r in rows}

# --- RC5 Email atomatico!

def obtener_email_cliente_por_servicio(sid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Hacemos JOIN para llegar del Servicio -> Vehículo -> Cliente
    res = cursor.execute("""
        SELECT c.email, c.nombre 
        FROM servicios s
        JOIN vehiculos v ON s.vehiculo_id = v.id
        JOIN clientes c ON v.cliente_id = c.id
        WHERE s.id = ?
    """, (sid,)).fetchone()
    conn.close()
    
    if res:
        return {'email': res[0], 'nombre': res[1]}
    return None
# ==========================================
# 6. OPERACIONES TALLER (CORE WORKFLOW)
# ==========================================

# NUEVO RC3: Se añade parámetro 'tipo_doc' ('Orden' o 'Cotizacion')
def crear_servicio(vid, desc, costo, tid=None, tipo_doc='Orden'):
    conn = sqlite3.connect(DB_NAME)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    uuid = secrets.token_urlsafe(16)
    # Si es Cotización, el estado inicial es 'Borrador', si es Orden es 'Pendiente'
    estado = 'Borrador' if tipo_doc == 'Cotizacion' else 'Pendiente'
    estatus_detalle = 'Cotizando' if tipo_doc == 'Cotizacion' else 'Recibido'
    
    conn.cursor().execute("""
        INSERT INTO servicios (vehiculo_id, fecha, descripcion, estado, costo_estimado, uuid_publico, estatus_detalle, tecnico_asignado_id, tipo_doc) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
        (vid, fecha, desc, estado, costo, uuid, estatus_detalle, tid, tipo_doc)
    )
    conn.commit(); conn.close()

# NUEVO RC3: Función para obtener SOLO cotizaciones
def obtener_cotizaciones():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    sql = """
        SELECT s.id, s.fecha, s.descripcion, s.costo_estimado, 
               v.placas, v.modelo, c.nombre as dueno_nombre
        FROM servicios s 
        JOIN vehiculos v ON s.vehiculo_id = v.id 
        JOIN clientes c ON v.cliente_id = c.id 
        WHERE s.tipo_doc = 'Cotizacion' AND s.estado != 'Terminado'
        ORDER BY s.id DESC
    """
    rows = conn.cursor().execute(sql).fetchall(); conn.close()
    return [dict(r) for r in rows]

# NUEVO RC4: NUEVO Restar inventario solo en ordenes de trabajo
# --- EN Db/database.py ---

def convertir_cotizacion_a_orden(servicio_id, tecnico_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 1. Convertir el encabezado (Cambiar estado y asignar fecha)
        cursor.execute("""
            UPDATE servicios 
            SET tipo_doc='Orden', 
                estado='Pendiente', 
                estatus_detalle='Recibido',
                fecha=?,
                tecnico_asignado_id=?
            WHERE id=?
        """, (fecha_hoy, tecnico_id, servicio_id))
        
        # 2. IMPACTO AL INVENTARIO (Modo Permisivo)
        # Obtenemos todas las refacciones que estaban "reservadas" en la cotización
        items = cursor.execute("SELECT inventario_id, cantidad FROM servicio_refacciones WHERE servicio_id=?", (servicio_id,)).fetchall()
        
        items_afectados = 0
        for iid, cant in items:
            # Restamos directamente. Si hay 0, pasa a -1. Si hay 5 y piden 10, pasa a -5.
            cursor.execute("UPDATE inventario SET cantidad = cantidad - ? WHERE id=?", (cant, iid))
            items_afectados += 1

        conn.commit()
        
        msg = "Cotización aprobada"
        if items_afectados > 0:
            msg += f" y stock descontado de {items_afectados} productos"
            
        return True, msg
        
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

# UPDATE RC3: Filtro para solo traer Órdenes (no cotizaciones)
def obtener_servicios_activos(filtro_trabajador_id=None):
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    sql = """
        SELECT s.id, s.fecha, s.descripcion, s.estado, s.costo_estimado, s.ticket_id, 
               s.uuid_publico, s.estatus_detalle, s.tecnico_asignado_id,
               v.placas, v.modelo, c.nombre as dueno_nombre,
               t.nombre as nombre_tecnico
        FROM servicios s 
        JOIN vehiculos v ON s.vehiculo_id = v.id 
        JOIN clientes c ON v.cliente_id = c.id 
        LEFT JOIN trabajadores t ON s.tecnico_asignado_id = t.id
        WHERE s.estado != 'Terminado' AND s.tipo_doc = 'Orden'
    """
    params = []
    if filtro_trabajador_id:
        sql += " AND s.tecnico_asignado_id = ?"
        params.append(filtro_trabajador_id)
        
    sql += " ORDER BY s.id DESC"
    rows = conn.cursor().execute(sql, tuple(params)).fetchall(); conn.close()
    return [dict(row) for row in rows]

# UPDATE RC3: Cerrar servicio requiere Método y Referencia
# Corrección Crítica Módulo 4: Guardar costo_final
def cerrar_servicio(servicio_id, ticket_id, trabajador_id, costo_final, metodo_pago="Efectivo", ref_pago=""):
    conn = sqlite3.connect(DB_NAME)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn.cursor().execute("""
        UPDATE servicios 
        SET estado='Terminado', 
            estatus_detalle='Entregado', 
            ticket_id=?, 
            cobrado_por=?, 
            costo_estimado=?,     -- Mantenemos actualizado el estimado por consistencia
            costo_final=?,        -- ✅ NUEVO: Aquí se guarda el dinero real para Reportes
            fecha_cierre=?, 
            metodo_pago=?, 
            referencia_pago=? 
        WHERE id=?""", 
        # Nota que pasamos 'costo_final' DOS VECES en los parámetros (una para estimado, una para final)
        (ticket_id, trabajador_id, costo_final, costo_final, fecha, metodo_pago, ref_pago, servicio_id)
    )
    conn.commit(); conn.close()

def obtener_servicios_terminados():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    rows = conn.cursor().execute("""SELECT s.*, v.placas, v.modelo, c.nombre as dueno_nombre FROM servicios s JOIN vehiculos v ON s.vehiculo_id=v.id JOIN clientes c ON v.cliente_id=c.id WHERE s.estado='Terminado' ORDER BY s.fecha_cierre DESC""").fetchall(); conn.close()
    return [dict(r) for r in rows]

def recalcular_total_servicio(sid):
    conn = sqlite3.connect(DB_NAME); cur = conn.cursor()
    mo = cur.execute("SELECT SUM(costo_cobrado) FROM servicio_detalles WHERE servicio_id=?", (sid,)).fetchone()[0] or 0
    ref = cur.execute("SELECT SUM(subtotal) FROM servicio_refacciones WHERE servicio_id=?", (sid,)).fetchone()[0] or 0
    total = mo + ref
    cur.execute("UPDATE servicios SET costo_estimado=? WHERE id=?", (total, sid)); conn.commit(); conn.close(); return total

def agregar_tarea_comision(sid, tid, desc, costo, pct):
    conn = sqlite3.connect(DB_NAME); monto = costo * (pct/100)
    conn.cursor().execute("INSERT INTO servicio_detalles (servicio_id, trabajador_id, descripcion_tarea, costo_cobrado, porcentaje_comision, monto_comision, fecha) VALUES (?,?,?,?,?,?,?)", (sid, tid, desc, costo, pct, monto, datetime.now().strftime("%Y-%m-%d"))); conn.commit(); conn.close(); recalcular_total_servicio(sid)

# RC4

def agregar_refaccion_a_servicio(sid, iid, cant):
    conn = sqlite3.connect(DB_NAME); cur = conn.cursor()
    try:
        # 1. Obtenemos datos del producto y tipo de documento
        prod = cur.execute("SELECT cantidad, precio_venta, descripcion FROM inventario WHERE id=?", (iid,)).fetchone()
        tipo_row = cur.execute("SELECT tipo_doc FROM servicios WHERE id=?", (sid,)).fetchone()
        
        if not prod: return False, "Producto no encontrado"
        
        stock_actual = prod[0]
        precio = prod[1]
        desc = prod[2]
        
        # Si por alguna razón tipo_doc es None (registros viejos), asumimos 'Orden'
        tipo_doc = tipo_row[0] if tipo_row else 'Orden'

        # 2. Lógica Diferenciada (Modo Permisivo)
        if tipo_doc == 'Cotizacion':
            # En cotización NO tocamos el inventario físico
            pass 
        else:
            # En Orden SÍ descontamos, permitiendo negativos
            nuevo_stock = stock_actual - cant
            cur.execute("UPDATE inventario SET cantidad=? WHERE id=?", (nuevo_stock, iid))

        # 3. Insertamos el registro en la orden/cotización
        cur.execute("""
            INSERT INTO servicio_refacciones 
            (servicio_id, inventario_id, cantidad, precio_unitario, subtotal) 
            VALUES (?,?,?,?,?)
        """, (sid, iid, cant, precio, cant * precio))
        
        conn.commit()
        recalcular_total_servicio(sid)
        
        # 4. Generamos el mensaje de respuesta
        msg = f"Agregado: {desc}"
        
        # Alerta visual si estamos en números rojos (solo para Ordenes)
        if tipo_doc != 'Cotizacion' and (stock_actual - cant) < 0:
            msg += f" (⚠️ Stock Negativo: {stock_actual - cant})"
            
        return True, msg

    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def eliminar_servicio_por_id(sid):
    conn = sqlite3.connect(DB_NAME); cur = conn.cursor()
    try:
        if cur.execute("SELECT estado FROM servicios WHERE id=?", (sid,)).fetchone()[0] == 'Terminado': return False, "Ya terminado"
        cur.execute("DELETE FROM servicio_detalles WHERE servicio_id=?", (sid,))
        cur.execute("DELETE FROM servicio_refacciones WHERE servicio_id=?", (sid,))
        if cur.execute("DELETE FROM servicios WHERE id=?", (sid,)).rowcount == 0: return False, "No encontrado"
        conn.commit(); return True, "Eliminado"
    except: return False, "Error"
    finally: conn.close()

def actualizar_estatus_servicio(sid, est):
    conn = sqlite3.connect(DB_NAME); uuid = secrets.token_urlsafe(16)
    conn.cursor().execute("UPDATE servicios SET estatus_detalle=?, uuid_publico=COALESCE(uuid_publico, ?) WHERE id=?", (est, uuid, sid)); conn.commit(); conn.close()

def obtener_info_publica_servicio(uuid):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    
    # CONSULTA RECUPERADA (Con JOIN trabajadores y costo)
    sql = """
        SELECT 
            s.estatus_detalle, s.fecha, s.costo_estimado,
            v.modelo, v.placas, v.color,
            t.nombre as mecanico
        FROM servicios s 
        JOIN vehiculos v ON s.vehiculo_id=v.id 
        LEFT JOIN trabajadores t ON s.tecnico_asignado_id = t.id
        WHERE s.uuid_publico=?
    """
    
    row = conn.cursor().execute(sql, (uuid,)).fetchone()
    conn.close()
    
    if row:
        d = dict(row)
        # Si la orden es MUY vieja y de verdad no tenía técnico, ponemos fallback
        if not d['mecanico']: d['mecanico'] = "Equipo TREGAL"
        return d
    return None


def obtener_items_editables(sid):
    """Obtiene los ítems con sus IDs reales para poder borrarlos"""
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    
    # 1. Mano de Obra
    mo = cur.execute("""
        SELECT id, 'MO' as tipo, descripcion_tarea as desc, 1 as cant, costo_cobrado as total 
        FROM servicio_detalles WHERE servicio_id=?""", (sid,)).fetchall()
    
    # 2. Refacciones
    ref = cur.execute("""
        SELECT sr.id, 'Ref' as tipo, i.descripcion as desc, sr.cantidad as cant, sr.subtotal as total 
        FROM servicio_refacciones sr 
        JOIN inventario i ON sr.inventario_id = i.id 
        WHERE sr.servicio_id=?""", (sid,)).fetchall()
    
    conn.close()
    return [dict(r) for r in mo] + [dict(r) for r in ref]

def eliminar_item_orden(tipo, item_id, servicio_id):
    """Elimina un ítem y devuelve stock si es necesario"""
    conn = sqlite3.connect(DB_NAME); cur = conn.cursor()
    try:
        if tipo == 'Ref':
            # CORRECCIÓN: Usamos alias 'sr' e 'i' para evitar ambigüedad en 'cantidad'
            # Queremos saber cuántos se vendieron (sr.cantidad), no cuánto stock hay (i.cantidad)
            sql = """
                SELECT sr.inventario_id, sr.cantidad, i.descripcion 
                FROM servicio_refacciones sr
                JOIN inventario i ON sr.inventario_id = i.id 
                WHERE sr.id=?
            """
            data = cur.execute(sql, (item_id,)).fetchone()
            
            if data:
                inv_id, cant_vendida, desc = data
                
                # DEVOLUCION DE STOCK (Sumamos lo que se había vendido)
                # Aquí sí actualizamos la tabla inventario
                cur.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE id=?", (cant_vendida, inv_id))
                
                # Borramos la línea de la orden
                cur.execute("DELETE FROM servicio_refacciones WHERE id=?", (item_id,))
        else:
            # Es Mano de Obra, solo borramos
            cur.execute("DELETE FROM servicio_detalles WHERE id=?", (item_id,))
            
        conn.commit()
        # Recalcular el total de la orden ($)
        recalcular_total_servicio(servicio_id)
        return True, "Ítem eliminado y totales actualizados"
        
    except Exception as e:
        conn.rollback()
        return False, f"Error DB: {str(e)}"
    finally:
        conn.close()

def obtener_datos_completos_pdf(sid):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    cur = conn.cursor()
    
    # CONSULTA RECUPERADA (Con JOIN trabajadores)
    sql = """
        SELECT 
            s.id, s.fecha, 
            c.nombre as cliente, c.telefono, 
            v.modelo, v.anio, v.placas, v.color, v.num_economico, v.vin, v.kilometraje,
            t.nombre as mecanico
        FROM servicios s 
        JOIN vehiculos v ON s.vehiculo_id=v.id 
        JOIN clientes c ON v.cliente_id=c.id
        LEFT JOIN trabajadores t ON s.tecnico_asignado_id = t.id
        WHERE s.id=?
    """
    
    head = cur.execute(sql, (sid,)).fetchone()
    
    if not head: 
        conn.close()
        return None
        
    d = dict(head)
    if not d['mecanico']: d['mecanico'] = "Por Asignar"

    d['items'] = []
    # Recuperar mano de obra y refacciones (se mantiene igual)
    for r in cur.execute("SELECT descripcion_tarea, costo_cobrado FROM servicio_detalles WHERE servicio_id=?", (sid,)):
        d['items'].append({'cantidad':1, 'descripcion':r[0], 'tipo':'MO', 'unitario':r[1], 'total':r[1]})
    for r in cur.execute("SELECT i.descripcion, sr.cantidad, sr.precio_unitario, sr.subtotal FROM servicio_refacciones sr JOIN inventario i ON sr.inventario_id=i.id WHERE sr.servicio_id=?", (sid,)):
        d['items'].append({'cantidad':r[1], 'descripcion':r[0], 'tipo':'Ref', 'unitario':r[2], 'total':r[3]})
        
    conn.close()
    return d

def obtener_detalle_completo_servicio(sid):
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    t = cur.execute("SELECT 'Mano de Obra' as tipo, descripcion_tarea as descripcion, 1 as cantidad, costo_cobrado as total FROM servicio_detalles WHERE servicio_id=?", (sid,)).fetchall()
    r = cur.execute("SELECT 'Refacción' as tipo, i.descripcion, r.cantidad, r.subtotal as total FROM servicio_refacciones r JOIN inventario i ON r.inventario_id=i.id WHERE r.servicio_id=?", (sid,)).fetchall()
    conn.close(); return [dict(row) for row in t] + [dict(row) for row in r]

# ==========================================
# 7. TRABAJADORES Y DASHBOARD (Modulo 2 y 4)
# ==========================================
def agregar_trabajador(nombre, fecha, sueldo):
    conn = sqlite3.connect(DB_NAME); conn.cursor().execute("INSERT INTO trabajadores (nombre, fecha_ingreso, estado, sueldo_base) VALUES (?, ?, 'Activo', ?)", (nombre, fecha, sueldo)); conn.commit(); conn.close()

def obtener_trabajadores_select():
    conn = sqlite3.connect(DB_NAME); rows = conn.cursor().execute("SELECT id, nombre FROM trabajadores WHERE estado='Activo'").fetchall(); conn.close()
    return {r[0]: r[1] for r in rows}

def obtener_trabajador_detalle(tid):
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row
    row = conn.cursor().execute("SELECT * FROM trabajadores WHERE id=?", (tid,)).fetchone(); conn.close()
    return dict(row) if row else None

def actualizar_esquema_trabajador(tid, esquema, pct_mo, pct_ref, fijo):
    conn = sqlite3.connect(DB_NAME)
    try: conn.cursor().execute("UPDATE trabajadores SET esquema_pago=?, pct_mano_obra=?, pct_refacciones=?, pago_fijo_servicio=? WHERE id=?", (esquema, pct_mo, pct_ref, fijo, tid)); conn.commit(); return True, "Actualizado"
    except Exception as e: return False, str(e)
    finally: conn.close()

def obtener_estadisticas_trabajador(tid):
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    w = cur.execute("SELECT fecha_ingreso FROM trabajadores WHERE id=?", (tid,)).fetchone()
    fi = w['fecha_ingreso'] if w else None
    hoy = datetime.now().strftime("%Y-%m-%d"); mes = datetime.now().strftime("%Y-%m")
    h_val = cur.execute("SELECT SUM(monto_comision) FROM servicio_detalles WHERE trabajador_id=? AND fecha=?", (tid, hoy)).fetchone()[0] or 0
    m_val = cur.execute("SELECT SUM(monto_comision) FROM servicio_detalles WHERE trabajador_id=? AND fecha LIKE ?", (tid, f'{mes}%')).fetchone()[0] or 0
    hist = cur.execute("SELECT descripcion_tarea, monto_comision, fecha FROM servicio_detalles WHERE trabajador_id=? ORDER BY id DESC LIMIT 10", (tid,)).fetchall()
    conn.close()
    return {"fecha_ingreso": fi, "especialidad": "General", "hoy": h_val, "mes": m_val, "historial": [dict(r) for r in hist]}


# ==========================================
# 8. Reportes y Cortes (Modulo 4)
# ==========================================

def obtener_resumen_mensual():
    conn = sqlite3.connect(DB_NAME); cur = conn.cursor(); mes = datetime.now().strftime("%Y-%m")
    cobrado = cur.execute("SELECT SUM(costo_estimado) FROM servicios WHERE estado='Terminado' AND fecha_cierre LIKE ?", (f'{mes}%',)).fetchone()[0] or 0
    pendiente = cur.execute("SELECT SUM(costo_estimado) FROM servicios WHERE estado!='Terminado' AND fecha LIKE ?", (f'{mes}%',)).fetchone()[0] or 0
    autos = cur.execute("SELECT COUNT(*) FROM servicios WHERE estado!='Terminado'").fetchone()[0]
    stock = cur.execute("SELECT COUNT(*) FROM inventario WHERE cantidad < ?", (get_stock_minimo(),)).fetchone()[0]
    conn.close(); return {"cobrado_mes": cobrado, "pendiente_mes": pendiente, "autos_activos": autos, "alertas_stock": stock}

def obtener_conteo_estados_servicios():
    conn = sqlite3.connect(DB_NAME); rows = conn.cursor().execute("SELECT estado, COUNT(*) FROM servicios GROUP BY estado").fetchall(); conn.close()
    return [{"name": r[0], "value": r[1]} for r in rows]


def obtener_resumen_financiero(fecha_inicio: str, fecha_fin: str):
    """
    Retorna el total cobrado y el desglose por método de pago.
    """
    conn = sqlite3.connect(DB_NAME) 
    cursor = conn.cursor()
    
    # 1. Total General
    sql_total = """
        SELECT SUM(costo_final) as total
        FROM servicios 
        WHERE estado = 'Terminado'   -- ✅ CORREGIDO (Antes decía estatus)
          AND date(fecha_cierre) BETWEEN ? AND ?
    """
    cursor.execute(sql_total, (fecha_inicio, fecha_fin))
    res = cursor.fetchone()
    total_general = res[0] if res and res[0] else 0.0

    # 2. Desglose por Método de Pago
    sql_metodos = """
        SELECT metodo_pago, SUM(costo_final) as subtotal, COUNT(*) as cantidad_tickets
        FROM servicios 
        WHERE estado = 'Terminado'   -- ✅ CORREGIDO
          AND date(fecha_cierre) BETWEEN ? AND ?
        GROUP BY metodo_pago
    """
    cursor.execute(sql_metodos, (fecha_inicio, fecha_fin))
    
    desglose = []
    for row in cursor.fetchall():
        desglose.append({
            'metodo_pago': row[0] or 'Sin Definir',
            'subtotal': row[1] or 0.0,
            'cantidad_tickets': row[2]
        })

    conn.close()
    return {
        'total': total_general,
        'desglose': desglose
    }
#--- RC4 Obtener datos para reporte pro
def obtener_detalle_ventas(fecha_inicio: str, fecha_fin: str):
    """Obtiene la lista de tickets para la tabla de detalle (INCLUYE CLIENTE)"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    sql = """
        SELECT s.id, s.fecha_cierre, v.modelo, c.nombre as cliente, s.metodo_pago, s.costo_final
        FROM servicios s
        LEFT JOIN vehiculos v ON s.vehiculo_id = v.id
        LEFT JOIN clientes c ON v.cliente_id = c.id  -- ✅ NUEVO: Traemos el nombre del cliente
        WHERE s.estado = 'Terminado'
          AND date(s.fecha_cierre) BETWEEN ? AND ?
        ORDER BY s.fecha_cierre DESC
    """
    cursor.execute(sql, (fecha_inicio, fecha_fin))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
# --- Major Realease 2026: KPIS dinamicos---

def obtener_kpis_dashboard():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    hoy = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Ventas del Día
    res_ventas = cursor.execute("SELECT SUM(costo_final) FROM servicios WHERE estado='Terminado' AND fecha_cierre LIKE ?", (f'{hoy}%',)).fetchone()
    ventas_hoy = res_ventas[0] or 0.0

    # 2. Autos en Proceso (Total activos)
    res_autos = cursor.execute("SELECT COUNT(*) FROM servicios WHERE estado != 'Terminado' AND tipo_doc = 'Orden'").fetchone()
    autos_activos = res_autos[0] or 0

    # 3. Autos LISTOS para Entrega (NUEVO KPI) 🚦
    # Contamos los que dicen 'Listo' en estatus_detalle
    res_listos = cursor.execute("SELECT COUNT(*) FROM servicios WHERE estatus_detalle = 'Listo' AND estado != 'Terminado'").fetchone()
    autos_listos = res_listos[0] or 0

    # 4. Alertas Stock
    min_stock = int(get_config_value('min_stock', 5))
    res_stock = cursor.execute("SELECT COUNT(*) FROM inventario WHERE cantidad <= ?", (min_stock,)).fetchone()
    alertas_stock = res_stock[0] or 0

    conn.close()
    
    return {
        "ventas": ventas_hoy,
        "autos": autos_activos,
        "listos": autos_listos, # <--- Nuevo dato
        "alertas": alertas_stock
    }
# --- AGREGAR AL FINAL DE Db/database.py ---

def obtener_datos_grafico_semanal():
    """
    Calcula el flujo de trabajo de los últimos 7 días.
    Retorna una lista con: Día, Ingresos (Nuevas Órdenes) y Salidas (Terminados).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    datos = []
    hoy = datetime.now()
    
    # Iteramos los últimos 7 días hacia atrás
    for i in range(6, -1, -1):
        fecha_obj = hoy - timedelta(days=i)
        dia_str = fecha_obj.strftime("%Y-%m-%d") # Para buscar en DB
        label_dia = fecha_obj.strftime("%d/%m")    # Para mostrar en gráfica (Ej: 25/10)
        
        # 1. Contar Ingresos (Fecha de creación)
        # Filtramos por fecha y que sea una 'Orden' (ignoramos cotizaciones)
        ingresos = cursor.execute("""
            SELECT COUNT(*) FROM servicios 
            WHERE fecha LIKE ? AND tipo_doc = 'Orden'
        """, (f'{dia_str}%',)).fetchone()[0]
        
        # 2. Contar Salidas (Fecha de cierre)
        salidas = cursor.execute("""
            SELECT COUNT(*) FROM servicios 
            WHERE estado='Terminado' AND fecha_cierre LIKE ?
        """, (f'{dia_str}%',)).fetchone()[0]
        
        datos.append({
            "dia": label_dia,
            "ingresos": ingresos,
            "salidas": salidas
        })
        
    conn.close()
    return datos
# --- AGREGAR AL FINAL DE Db/database.py ---

def obtener_metricas_ventas_mensuales():
    """
    Compara las ventas cerradas de este mes vs el mes anterior.
    Retorna: {'actual': 15000.0, 'anterior': 40000.0}
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    hoy = datetime.now()
    mes_actual_str = hoy.strftime("%Y-%m") # Ej: "2023-10"
    
    # Calcular mes anterior (truco matemático con fechas)
    primer_dia_este_mes = hoy.replace(day=1)
    ultimo_dia_mes_anterior = primer_dia_este_mes - timedelta(days=1)
    mes_anterior_str = ultimo_dia_mes_anterior.strftime("%Y-%m") # Ej: "2023-09"
    
    # 1. Ventas Mes Actual
    res_act = cursor.execute("SELECT SUM(costo_final) FROM servicios WHERE estado='Terminado' AND fecha_cierre LIKE ?", (f'{mes_actual_str}%',)).fetchone()
    v_actual = res_act[0] if res_act and res_act[0] else 0.0
    
    # 2. Ventas Mes Anterior
    res_ant = cursor.execute("SELECT SUM(costo_final) FROM servicios WHERE estado='Terminado' AND fecha_cierre LIKE ?", (f'{mes_anterior_str}%',)).fetchone()
    v_anterior = res_ant[0] if res_ant and res_ant[0] else 0.0
    
    conn.close()
    return {"actual": v_actual, "anterior": v_anterior}

def obtener_carga_tecnicos():
    """
    Cuenta cuántas Órdenes Activas tiene cada técnico.
    """
    conn = sqlite3.connect(DB_NAME)
    sql = """
        SELECT t.nombre, COUNT(s.id) as total
        FROM servicios s
        JOIN trabajadores t ON s.tecnico_asignado_id = t.id
        WHERE s.estado != 'Terminado' AND s.tipo_doc = 'Orden'
        GROUP BY t.nombre
    """
    rows = conn.cursor().execute(sql).fetchall()
    conn.close()
    # Formato para gráfica ECharts: [{'name': 'Juan', 'value': 5}, ...]
    return [{"name": r[0], "value": r[1]} for r in rows]

# --- AGREGAR AL FINAL DE Db/database.py ---

def obtener_ticket_promedio_mensual():
    """
    Calcula el valor promedio de venta por auto en el mes actual.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    mes_actual = datetime.now().strftime("%Y-%m")
    
    # Promedio de costos finales de servicios terminados este mes
    res = cursor.execute("""
        SELECT AVG(costo_final) FROM servicios 
        WHERE estado='Terminado' AND fecha_cierre LIKE ?
    """, (f'{mes_actual}%',)).fetchone()
    
    conn.close()
    return res[0] if res and res[0] else 0.0

def obtener_top_servicios():
    """
    Devuelve los 5 servicios (Mano de Obra) más frecuentes del mes.
    """
    conn = sqlite3.connect(DB_NAME)
    # Contamos cuántas veces aparece cada descripción en los detalles
    sql = """
        SELECT descripcion_tarea, COUNT(*) as cantidad
        FROM servicio_detalles
        GROUP BY descripcion_tarea
        ORDER BY cantidad DESC
        LIMIT 5
    """
    rows = conn.cursor().execute(sql).fetchall()
    conn.close()
    
    # Formato para gráfica: [{'name': 'Afinación', 'value': 10}, ...]
    return [{"name": r[0], "value": r[1]} for r in rows]

# --- EN LA SECCIÓN DE IMPORTS ---
import resend # Asegúrate de instalarlo: pip install resend

# --- EN LA FUNCIÓN init_db() ---
def init_db():
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    # ... (tus tablas existentes) ...
    
    # NUEVA TABLA: Historial de Correos (Para evitar spam y logs de marketing)
    cursor.execute('''CREATE TABLE IF NOT EXISTS email_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        fecha_envio TEXT,
        tipo TEXT, -- 'Recordatorio', 'Promocion', 'Cotizacion'
        asunto TEXT,
        estatus TEXT -- 'Enviado', 'Error'
    )''')
    
    # Configuración Default para Resend (Si no existe)
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('resend_api_key', '')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('email_remitente', 'Taller <onboarding@resend.dev>')") # Cambiar por tu dominio verificado
    
    conn.commit(); conn.close()

# --- EN LA SECCIÓN DE CONFIGURACIÓN ---
def get_resend_api_key(): return get_config_value('resend_api_key', '')
def set_resend_api_key(val): set_config_value('resend_api_key', val)
def get_email_remitente(): return get_config_value('email_remitente', 'onboarding@resend.dev')
def set_email_remitente(val): set_config_value('email_remitente', val)

# --- NUEVA SECCIÓN: LÓGICA DE EMAILS ---

def registrar_envio_email(cid, tipo, asunto, estatus):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO email_logs (cliente_id, fecha_envio, tipo, asunto, estatus) VALUES (?, datetime('now'), ?, ?, ?)", (cid, tipo, asunto, estatus))
    conn.commit(); conn.close()

def verificar_recordatorio_reciente(cliente_id, dias_cooldown=30):
    """Verifica si ya enviamos un recordatorio a este cliente recientemente"""
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    limite = (datetime.now() - timedelta(days=dias_cooldown)).strftime("%Y-%m-%d")
    res = cursor.execute("SELECT id FROM email_logs WHERE cliente_id=? AND tipo='Recordatorio' AND fecha_envio > ?", (cliente_id, limite)).fetchone()
    conn.close()
    return res is not None

def enviar_email_resend(destinatario, asunto, html_body, cliente_id=None, tipo="General"):
    """Función maestra para enviar correos"""
    api_key = get_resend_api_key()
    remitente = get_email_remitente()
    
    if not api_key: return False, "Falta API Key"
    
    resend.api_key = api_key
    try:
        params = {
            "from": remitente,
            "to": [destinatario],
            "subject": asunto,
            "html": html_body
        }
        email = resend.Emails.send(params)
        
        # Registrar en bitácora si se envió bien
        if cliente_id:
            registrar_envio_email(cliente_id, tipo, asunto, "Enviado")
            
        return True, email
    except Exception as e:
        if cliente_id:
            registrar_envio_email(cliente_id, tipo, asunto, f"Error: {str(e)}")
        return False, str(e)

# EN Db/database.py

def procesar_recordatorios_automaticos():
    """Busca clientes próximos a servicio y envía correos si faltan 7 días o menos."""
    clientes = obtener_clientes()
    meses = get_meses_alerta()
    limite_dias = meses * 30
    hoy = datetime.now()
    enviados = 0
    
    # --- AJUSTE CLAVE: VENTANA DE AVISO ---
    # Solo avisar si faltan 7 días o menos para el vencimiento.
    DIAS_AVISO_PREVIO = 7 
    
    for c in clientes:
        if c.get('email') and c.get('ultimo_servicio_fmt') != '-':
            try:
                dt = datetime.strptime(c['ultimo_servicio'][:10], "%Y-%m-%d")
                delta = (hoy - dt).days
                dias_restantes = limite_dias - delta
                
                # CORRECCIÓN: Si dias_restantes es 30, NO entra.
                # Solo entra si dias_restantes es 7, 6, 5... hasta 1.
                if 0 < dias_restantes <= DIAS_AVISO_PREVIO:
                    
                    if not verificar_recordatorio_reciente(c['id'], dias_cooldown=20):
                        html = f"""
                        <h1>Hola {c['nombre']}</h1>
                        <p>Notamos que tu vehículo está próximo a requerir su mantenimiento preventivo.</p>
                        <p><strong>Fecha estimada:</strong> En {dias_restantes} días.</p>
                        <p>Evita fallas y agenda tu cita hoy mismo.</p>
                        <br><p>Atte. El equipo de TREGAL Tires</p>
                        """
                        # Usamos la función que lee la API Key de la DB
                        ok, _ = enviar_email_resend(c['email'], "Recordatorio de Servicio 🚗", html, c['id'], "Recordatorio")
                        if ok: enviados += 1
            except: pass
    return enviados