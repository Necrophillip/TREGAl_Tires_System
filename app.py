from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import mysql.connector
import os
import decimal
from fpdf import FPDF
from datetime import datetime, timedelta

app = Flask(__name__)
# Habilitar CORS para permitir que el frontend (en otro origen) se comunique con esta API
CORS(app)

# --- Configuración de la Base de Datos ---
# Se usarán variables de entorno si están disponibles, si no, valores por defecto.
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'tregal_user'),
    'password': os.environ.get('DB_PASSWORD', 'tregal_password'),
    'database': os.environ.get('DB_NAME', 'tregal_erp')
}

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar con la base de datos: {err}")
        return None

# --- Rutas de la API ---

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Endpoint para obtener todos los clientes."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "No se pudo establecer conexión con la base de datos."}), 500

    try:
        # dictionary=True devuelve las filas como diccionarios (JSON friendly)
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id_cliente, nombre, rfc, correo, telefono FROM clientes ORDER BY nombre ASC"
        cursor.execute(query)
        clients = cursor.fetchall()

        # Convertir campos de fecha/hora a string si los hubiera, para evitar problemas de serialización JSON.
        for client in clients:
            for key, value in client.items():
                if hasattr(value, 'isoformat'): # Chequea si es un objeto de fecha/hora
                    client[key] = value.isoformat()

        return jsonify(clients)

    except mysql.connector.Error as err:
        print(f"Error al consultar clientes: {err}")
        return jsonify({"error": "Ocurrió un error al obtener los datos."}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# --- API Endpoints for Inventory ---

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Fetches all inventory items."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM inventario ORDER BY descripcion ASC")
        items = cursor.fetchall()
        # Handle decimal and date serialization
        for item in items:
            for key, value in item.items():
                if isinstance(value, decimal.Decimal):
                    item[key] = str(value)
                elif hasattr(value, 'isoformat'):
                    item[key] = value.isoformat()
        return jsonify(items)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Failed to fetch inventory: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/inventory', methods=['POST'])
def add_inventory_item():
    """Adds a new item to the inventory."""
    data = request.get_json()
    if not data or not data.get('descripcion') or data.get('precio_venta') is None:
        return jsonify({"error": "La descripción y el precio de venta son obligatorios."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        sql = """INSERT INTO inventario (sku, descripcion, proveedor, stock, precio_compra, precio_venta, stock_minimo)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        params = (
            data.get('sku'),
            data.get('descripcion'),
            data.get('proveedor'),
            data.get('stock', 0),
            data.get('precio_compra'),
            data.get('precio_venta'),
            data.get('stock_minimo', 0)
        )
        cursor.execute(sql, params)
        conn.commit()
        new_id = cursor.lastrowid

        cursor.execute("SELECT * FROM inventario WHERE id_producto = %s", (new_id,))
        new_item = cursor.fetchone()
        for key, value in new_item.items():
            if isinstance(value, decimal.Decimal):
                new_item[key] = str(value)
            elif hasattr(value, 'isoformat'):
                new_item[key] = value.isoformat()

        return jsonify(new_item), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": f"Failed to add item: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
def update_inventory_item(item_id):
    """Updates an existing inventory item."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM inventario WHERE id_producto = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"error": "Item not found"}), 404

        update_fields = []
        params = []
        for key, value in data.items():
            if key in ['sku', 'descripcion', 'proveedor', 'stock', 'precio_compra', 'precio_venta', 'stock_minimo']:
                update_fields.append(f"`{key}` = %s")
                params.append(value)

        if not update_fields:
            return jsonify({"error": "No valid fields to update"}), 400

        sql = f"UPDATE inventario SET {', '.join(update_fields)} WHERE id_producto = %s"
        params.append(item_id)

        cursor.execute(sql, tuple(params))
        conn.commit()

        cursor.execute("SELECT * FROM inventario WHERE id_producto = %s", (item_id,))
        updated_item = cursor.fetchone()
        for key, value in updated_item.items():
            if isinstance(value, decimal.Decimal):
                updated_item[key] = str(value)
            elif hasattr(value, 'isoformat'):
                updated_item[key] = value.isoformat()

        return jsonify(updated_item)
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": f"Failed to update item: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
def delete_inventory_item(item_id):
    """Deletes an inventory item."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventario WHERE id_producto = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"error": "Item not found"}), 404

        cursor.execute("DELETE FROM inventario WHERE id_producto = %s", (item_id,))
        conn.commit()

        return jsonify({"message": "Item deleted successfully"}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": f"Failed to delete item: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# --- PDF Generation ---

class PDF(FPDF):
    def header(self):
        # TODO: Could add a logo image here
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'TREGAL Tires', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(0, 6, 'Centro de Servicio Automotriz', 0, 1, 'L')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def quote_title(self, folio, fecha):
        self.set_font('Arial', 'B', 18)
        self.cell(0, 10, f'Cotización: {folio}', 0, 1, 'R')
        self.set_font('Arial', '', 12)
        self.cell(0, 6, f'Fecha: {fecha}', 0, 1, 'R')
        self.ln(10)

    def customer_details(self, data):
        self.set_font('Arial', 'B', 12)
        self.cell(95, 7, 'Cliente', 1, 0, 'C')
        self.cell(95, 7, 'Vehículo', 1, 1, 'C')

        self.set_font('Arial', '', 10)
        self.cell(95, 6, data.get('cliente', ''), 'LR', 0)
        self.cell(95, 6, data.get('vehiculo', ''), 'LR', 1)
        self.cell(95, 6, f"RFC: {data.get('rfc', '')}", 'LR', 0)
        self.cell(95, 6, f"Placas: {data.get('placas', '')}", 'LR', 1)
        self.cell(95, 6, data.get('email', ''), 'LR', 0)
        self.cell(95, 6, f"VIN: {data.get('vin', '')}", 'LR', 1)
        self.cell(95, 6, data.get('telefono', ''), 'LRB', 0)
        self.cell(95, 6, f"KM: {data.get('km', '')}", 'LRB', 1)
        self.ln(10)

    def items_table(self, items):
        self.set_font('Arial', 'B', 10)
        self.cell(100, 7, 'Descripción', 1, 0, 'C')
        self.cell(15, 7, 'Cant.', 1, 0, 'C')
        self.cell(25, 7, 'P. Unit.', 1, 0, 'C')
        self.cell(25, 7, 'Descuento', 1, 0, 'C')
        self.cell(25, 7, 'Importe', 1, 1, 'C')

        self.set_font('Arial', '', 9)
        for item in items:
            self.cell(100, 6, item.get('desc','').encode('latin-1', 'replace').decode('latin-1'), 'LR', 0, 'L')
            self.cell(15, 6, str(item.get('qty',0)), 'LR', 0, 'C')
            self.cell(25, 6, f"{item.get('price',0):.2f}", 'LR', 0, 'R')
            self.cell(25, 6, f"{item.get('discVal',0):.2f}", 'LR', 0, 'R')
            self.cell(25, 6, f"{item.get('total',0):.2f}", 'LR', 1, 'R')
        self.cell(190, 0, '', 'T', 1)
        self.ln(5)

    def totals_section(self, totals, currency):
        self.set_font('Arial', 'B', 10)
        self.cell(130, 6, '', 0, 0)
        self.cell(30, 6, 'Subtotal', 1, 0, 'R')
        self.cell(30, 6, f"{totals.get('subtotal',0):.2f}", 1, 1, 'R')
        self.cell(130, 6, '', 0, 0)
        self.cell(30, 6, 'Descuento', 1, 0, 'R')
        self.cell(30, 6, f"-{totals.get('descuento',0):.2f}", 1, 1, 'R')
        self.cell(130, 6, '', 0, 0)
        self.cell(30, 6, 'IVA (16%)', 1, 0, 'R')
        self.cell(30, 6, f"{totals.get('iva',0):.2f}", 1, 1, 'R')
        self.cell(130, 6, '', 0, 0)
        self.set_font('Arial', 'B', 12)
        self.cell(30, 8, 'Total', 1, 0, 'R')
        self.cell(30, 8, f"{totals.get('total',0):.2f} {currency}", 1, 1, 'R')

@app.route('/api/quotes/pdf', methods=['POST'])
def generate_quote_pdf():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    pdf = PDF('P', 'mm', 'Letter')
    pdf.add_page()
    pdf.quote_title(data.get('folio', 'N/A'), data.get('fecha', 'N/A'))
    pdf.customer_details(data)
    pdf.items_table(data.get('items', []))
    pdf.totals_section(data.get('totales', {}), data.get('moneda', 'MXN'))

    pdf_output = pdf.output(dest='S').encode('latin-1')

    response = make_response(pdf_output)
    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename=f"{data.get('folio', 'cotizacion')}.pdf")
    return response


# --- API Endpoints for Reports ---

@app.route('/api/reports/sales', methods=['GET'])
def get_sales_report():
    period = request.args.get('period', 'monthly') # daily, weekly, monthly

    if period == 'daily':
        date_format = '%Y-%m-%d'
        interval_days = 30
    elif period == 'weekly':
        # Using %x-%v for year-week number format
        date_format = '%x-%v'
        interval_days = 90
    else: # monthly
        date_format = '%Y-%m'
        interval_days = 365

    sql = f"""
        SELECT
            DATE_FORMAT(ot.fecha_fin, '{date_format}') AS period,
            SUM(c.total) AS total_sales
        FROM ordenes_trabajo ot
        JOIN cotizaciones c ON ot.cotizacion_id = c.id_cotizacion
        WHERE ot.estatus IN ('finalizada', 'entregada')
        AND ot.fecha_fin >= DATE_SUB(CURDATE(), INTERVAL {interval_days} DAY)
        GROUP BY period
        ORDER BY period ASC;
    """

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)
        report_data = cursor.fetchall()
        for row in report_data:
            if isinstance(row['total_sales'], decimal.Decimal):
                row['total_sales'] = float(row['total_sales'])
        return jsonify(report_data)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Failed to generate sales report: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/reports/top-items', methods=['GET'])
def get_top_items_report():
    item_type = request.args.get('type', 'refaccion') # refaccion or mano_obra
    if item_type not in ['refaccion', 'mano_obra']:
        return jsonify({"error": "Invalid item type"}), 400

    sql = """
        SELECT
            ci.descripcion,
            SUM(ci.cantidad) AS total_quantity
        FROM cotizacion_items ci
        JOIN cotizaciones c ON ci.cotizacion_id = c.id_cotizacion
        JOIN ordenes_trabajo ot ON c.id_cotizacion = ot.cotizacion_id
        WHERE ot.estatus IN ('finalizada', 'entregada')
        AND ci.tipo = %s
        AND ot.fecha_fin >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY ci.descripcion
        ORDER BY total_quantity DESC
        LIMIT 10;
    """

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (item_type,))
        report_data = cursor.fetchall()
        for row in report_data:
            if isinstance(row['total_quantity'], decimal.Decimal):
                row['total_quantity'] = float(row['total_quantity'])
        return jsonify(report_data)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Failed to generate top items report: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/users/technicians', methods=['GET'])
def get_technicians():
    """Fetches all users with the 'tecnico' role."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_usuario, nombre FROM usuarios WHERE rol = 'tecnico' AND activo = 1 ORDER BY nombre ASC")
        technicians = cursor.fetchall()
        return jsonify(technicians)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Failed to fetch technicians: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/clients', methods=['POST'])
def add_client():
    """Adds a new client to the database."""
    data = request.get_json()
    if not data or not data.get('nombre') or not data.get('correo'):
        return jsonify({"error": "Nombre y correo son campos obligatorios."}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        sql = """INSERT INTO clientes (nombre, rfc, correo, telefono, direccion)
                 VALUES (%s, %s, %s, %s, %s)"""
        params = (
            data.get('nombre'),
            data.get('rfc'),
            data.get('correo'),
            data.get('telefono'),
            data.get('direccion')
        )
        cursor.execute(sql, params)
        conn.commit()
        new_id = cursor.lastrowid

        cursor.execute("SELECT * FROM clientes WHERE id_cliente = %s", (new_id,))
        new_client = cursor.fetchone()

        # Serialize dates if any
        for key, value in new_client.items():
            if hasattr(value, 'isoformat'):
                new_client[key] = value.isoformat()

        return jsonify(new_client), 201
    except mysql.connector.Error as err:
        conn.rollback()
        # Handle duplicate entry for email
        if err.errno == 1062:
            return jsonify({"error": "Ya existe un cliente con ese correo electrónico."}), 409
        return jsonify({"error": f"Failed to add client: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# --- API Endpoints for Vehicles ---

@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    """Fetches all vehicles, joining with client name."""
    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT v.*, c.nombre as nombre_cliente
            FROM vehiculos v
            JOIN clientes c ON v.cliente_id = c.id_cliente
            ORDER BY c.nombre, v.marca, v.modelo
        """
        cursor.execute(sql)
        vehicles = cursor.fetchall()
        return jsonify(vehicles)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Failed to fetch vehicles: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/vehicles', methods=['POST'])
def add_vehicle():
    """Adds a new vehicle."""
    data = request.get_json()
    required = ['cliente_id', 'marca', 'modelo', 'anio']
    if not all(k in data and data[k] is not None for k in required):
        return jsonify({"error": "cliente_id, marca, modelo, y anio son obligatorios."}), 400

    sql = """INSERT INTO vehiculos (cliente_id, marca, modelo, anio, color, vin, placas, km)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    params = (
        data.get('cliente_id'), data.get('marca'), data.get('modelo'), data.get('anio'),
        data.get('color'), data.get('vin'), data.get('placas'), data.get('km')
    )

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        new_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT v.*, c.nombre as nombre_cliente FROM vehiculos v JOIN clientes c ON v.cliente_id = c.id_cliente WHERE v.id_vehiculo = %s", (new_id,))
        new_vehicle = cursor.fetchone()
        return jsonify(new_vehicle), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": f"Failed to add vehicle: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/vehicles/<int:vehicle_id>', methods=['PUT'])
def update_vehicle(vehicle_id):
    """Updates an existing vehicle."""
    data = request.get_json()
    if not data: return jsonify({"error": "No data provided"}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        update_fields = []
        params = []
        for key, value in data.items():
            if key in ['cliente_id', 'marca', 'modelo', 'anio', 'color', 'vin', 'placas', 'km']:
                update_fields.append(f"`{key}` = %s")
                params.append(value)

        if not update_fields: return jsonify({"error": "No valid fields to update"}), 400

        sql = f"UPDATE vehiculos SET {', '.join(update_fields)} WHERE id_vehiculo = %s"
        params.append(vehicle_id)

        cursor.execute(sql, tuple(params))
        conn.commit()

        cursor.execute("SELECT v.*, c.nombre as nombre_cliente FROM vehiculos v JOIN clientes c ON v.cliente_id = c.id_cliente WHERE v.id_vehiculo = %s", (vehicle_id,))
        updated_vehicle = cursor.fetchone()
        return jsonify(updated_vehicle)
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": f"Failed to update vehicle: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/vehicles/<int:vehicle_id>', methods=['DELETE'])
def delete_vehicle(vehicle_id):
    """Deletes a vehicle."""
    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vehiculos WHERE id_vehiculo = %s", (vehicle_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Vehicle not found"}), 404
        conn.commit()
        return jsonify({"message": "Vehicle deleted successfully"}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": f"Failed to delete vehicle: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# --- API Endpoints for Payrolls ---

@app.route('/api/mechanics/config/<int:user_id>', methods=['GET'])
def get_mechanic_config(user_id):
    """Gets the payment configuration for a specific mechanic."""
    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tecnicos_config WHERE usuario_id = %s", (user_id,))
        config = cursor.fetchone()
        if not config:
            return jsonify({"error": "Config not found for this user"}), 404

        # Serialize decimals
        for key, value in config.items():
            if isinstance(value, decimal.Decimal):
                config[key] = str(value)

        return jsonify(config)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Failed to fetch config: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/mechanics/config/<int:user_id>', methods=['POST'])
def set_mechanic_config(user_id):
    """Creates or updates the payment configuration for a mechanic."""
    data = request.get_json()
    if not data or not data.get('tipo_pago'):
        return jsonify({"error": "Missing required field: tipo_pago"}), 400

    sql = """
        INSERT INTO tecnicos_config (usuario_id, tipo_pago, monto_salario, porcentaje_comision)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        tipo_pago = VALUES(tipo_pago),
        monto_salario = VALUES(monto_salario),
        porcentaje_comision = VALUES(porcentaje_comision)
    """
    params = (
        user_id,
        data.get('tipo_pago'),
        data.get('monto_salario'),
        data.get('porcentaje_comision')
    )

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({"message": "Configuration saved successfully"}), 200
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": f"Failed to save config: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/payrolls/calculate', methods=['POST'])
def calculate_payroll():
    """Calculates a payroll for a given technician and date range without saving it."""
    data = request.get_json()
    user_id = data.get('user_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    if not all([user_id, start_date, end_date]):
        return jsonify({"error": "user_id, start_date, and end_date are required"}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Get technician config
        cursor.execute("SELECT * FROM tecnicos_config WHERE usuario_id = %s", (user_id,))
        config = cursor.fetchone()
        if not config:
            return jsonify({"error": "Payment configuration not found for this technician"}), 404

        # 2. Get technician name
        cursor.execute("SELECT nombre FROM usuarios WHERE id_usuario = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "Technician not found"}), 404
        tecnico_nombre = user['nombre']

        # 3. Calculate commissions from completed work
        sql_commissions = """
            SELECT SUM(ci.importe) as total_labor
            FROM ordenes_trabajo ot
            JOIN cotizaciones c ON ot.cotizacion_id = c.id_cotizacion
            JOIN cotizacion_items ci ON c.id_cotizacion = ci.cotizacion_id
            WHERE
                ot.tecnico_asignado = %s AND
                ot.estatus IN ('finalizada', 'entregada') AND
                ot.fecha_fin BETWEEN %s AND %s AND
                ci.tipo = 'mano_obra'
        """
        cursor.execute(sql_commissions, (tecnico_nombre, start_date, end_date))
        result = cursor.fetchone()
        total_labor = result['total_labor'] if result and result['total_labor'] else 0

        # 4. Calculate final pay
        salario_base = config.get('monto_salario', 0) or 0
        porcentaje_comision = config.get('porcentaje_comision', 0) or 0

        comisiones_ganadas = float(total_labor) * (float(porcentaje_comision) / 100.0)

        total_pagar = float(salario_base) + comisiones_ganadas

        return jsonify({
            "user_id": user_id,
            "tecnico_nombre": tecnico_nombre,
            "periodo": f"{start_date} a {end_date}",
            "salario_base": f"{float(salario_base):.2f}",
            "total_mano_obra": f"{float(total_labor):.2f}",
            "porcentaje_comision": f"{float(porcentaje_comision):.2f}",
            "comisiones_ganadas": f"{comisiones_ganadas:.2f}",
            "total_pagar": f"{total_pagar:.2f}"
        })

    except mysql.connector.Error as err:
        return jsonify({"error": f"Failed to calculate payroll: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


@app.route('/api/payrolls', methods=['POST'])
def save_payroll():
    """Saves a calculated payroll record to the database."""
    data = request.get_json()
    # Basic validation
    required_fields = ['user_id', 'start_date', 'end_date', 'salario_base', 'comisiones_ganadas', 'total_pagar']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields for saving payroll"}), 400

    sql = """
        INSERT INTO nominas (usuario_id, fecha_inicio_periodo, fecha_fin_periodo, salario_base, comisiones, total_pagar, estatus)
        VALUES (%s, %s, %s, %s, %s, %s, 'pagada')
    """
    params = (
        data['user_id'],
        data['start_date'],
        data['end_date'],
        data['salario_base'],
        data['comisiones_ganadas'],
        data['total_pagar']
    )

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({"message": "Payroll saved successfully", "id": cursor.lastrowid}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"error": f"Failed to save payroll: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/payrolls', methods=['GET'])
def get_payroll_history():
    """Retrieves the history of all saved payrolls."""
    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500

    sql = """
        SELECT n.*, u.nombre as tecnico_nombre
        FROM nominas n
        JOIN usuarios u ON n.usuario_id = u.id_usuario
        ORDER BY n.fecha_generacion DESC
    """
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)
        history = cursor.fetchall()
        # Serialize decimals and dates
        for row in history:
            for key, value in row.items():
                if isinstance(value, decimal.Decimal):
                    row[key] = str(value)
                elif hasattr(value, 'isoformat'):
                    row[key] = value.isoformat()
        return jsonify(history)
    except mysql.connector.Error as err:
        return jsonify({"error": f"Failed to fetch payroll history: {err}"}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# --- Punto de entrada de la aplicación ---

if __name__ == '__main__':
    # Usar host='0.0.0.0' para que el servidor sea accesible desde fuera del contenedor/sandbox
    app.run(host='0.0.0.0', port=5001, debug=True)
