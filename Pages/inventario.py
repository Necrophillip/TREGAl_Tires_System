from nicegui import ui, app # <--- Aseguramos la importación de 'app'
from Db import database as db

def show():
    # --- Definición de funciones ---
    
    def actualizar_tabla():
        datos_raw = db.obtener_inventario()
        limite_alerta = db.get_stock_minimo()
        
        datos_procesados = []
        for row in datos_raw:
            r = dict(row)
            # Asegurar que el ID esté en el diccionario para la acción de eliminar
            r['id'] = row['id'] 
            r['precio_formateado'] = f"${r['precio_venta']:,.2f}"
            datos_procesados.append(r)
        
        tabla_inv.rows = datos_procesados
        
        # Slot para pintar rojo (stock bajo)
        tabla_inv._props['slots'] = {} 
        tabla_inv.add_slot('body-cell-cantidad', f'''
            <q-td :props="props" :class="props.value < {limite_alerta} ? 'bg-red-50 text-red-600 border border-red-200 rounded' : 'text-slate-700'">
                {{{{ props.value }}}}
            </q-td>
        ''')
        
        # Slot para el nuevo botón de ELIMINAR
        tabla_inv.add_slot('body-cell-acciones', '''
            <q-td :props="props">
                <q-btn icon="delete" size="sm" color="negative" flat round 
                       @click="$parent.$emit('eliminar', props.row.id)" />
            </q-td>
        ''')
        
        tabla_inv.update()

    def eliminar_producto(producto_id):
        # --- GUARDIA DE SEGURIDAD (Eliminar Producto) ---
        if not app.storage.user.get('authenticated', False):
            ui.notify('Sesión expirada. Acceso denegado.', type='negative')
            ui.navigate.to('/login?expired=true')
            return

        exito, msg = db.eliminar_producto_por_id(producto_id)
        if exito:
            ui.notify(f'Producto ID {producto_id} eliminado.', type='positive')
            actualizar_tabla()
        else:
            ui.notify(msg, type='negative')


    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. ENCABEZADO
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('inventory_2', size='lg', color='primary')
                ui.label('Inventario de Refacciones').classes('text-2xl font-bold text-gray-800')
            
            # Botón Configuración
            with ui.row().classes('items-center'):
                def abrir_config():
                    limite_actual = db.get_stock_minimo()
                    dialog_config.valor_input.value = limite_actual
                    dialog_config.open()
                ui.button('Configurar Alertas', icon='settings', on_click=abrir_config).props('outline color=slate-700')

        # 2. CONTENEDOR SPLIT VIEW
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # =================================================
            # PANEL IZQUIERDO: FORMULARIO INTELIGENTE
            # =================================================
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-green-600'):
                lbl_titulo = ui.label('Gestión de Producto').classes('text-lg font-bold text-slate-700 mb-2')
                
                # Campos del formulario
                codigo = ui.input('Código / SKU', placeholder='Escanea...').classes('w-full font-mono font-bold')
                descripcion = ui.input('Descripción').classes('w-full')
                categoria = ui.select(['General', 'Llantas', 'Frenos', 'Motor', 'Eléctrico', 'Suspensión'], label='Categoría').classes('w-full')
                
                with ui.row().classes('w-full gap-2'):
                    cantidad = ui.number('Cantidad (+)', value=1, format='%.0f').classes('w-1/2 pr-1')
                    precio = ui.number('Precio Venta').classes('w-1/2 pl-1').props('prefix="$"')

                # --- LÓGICA DE AUTOCOMPLETADO ---
                def buscar_sku():
                    sku = codigo.value
                    if not sku: return
                    
                    prod = db.obtener_producto_por_codigo(sku)
                    if prod:
                        descripcion.value = prod['descripcion']
                        categoria.value = prod['categoria']
                        precio.value = prod['precio_venta']
                        
                        ui.notify(f'Producto encontrado. Stock actual: {prod["cantidad"]}', type='info')
                        lbl_titulo.text = f'Editar / Sumar Stock (Actual: {prod["cantidad"]})'
                        cantidad.label = 'Cantidad a Sumar (+)'
                        cantidad.value = 1
                    else:
                        lbl_titulo.text = 'Nuevo Producto'
                        cantidad.label = 'Stock Inicial'
                        descripcion.value = ''
                        categoria.value = 'General'
                        precio.value = None

                codigo.on('change', buscar_sku)

                def guardar():
                    # --- GUARDIA DE SEGURIDAD (Guardar/Upsert) ---
                    if not app.storage.user.get('authenticated', False):
                        ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                        ui.navigate.to('/login?expired=true')
                        return

                    if not codigo.value or not descripcion.value:
                        ui.notify('Código y Descripción obligatorios', type='warning'); return
                    
                    exito, msg = db.gestionar_producto(
                        codigo.value, 
                        descripcion.value, 
                        int(cantidad.value), 
                        float(precio.value or 0), 
                        categoria.value
                    )
                    
                    if exito:
                        ui.notify(msg, type='positive')
                        codigo.value = ''; descripcion.value = ''; cantidad.value = 1; precio.value = None
                        lbl_titulo.text = 'Gestión de Producto'
                        cantidad.label = 'Cantidad (+)'
                        
                        actualizar_tabla()
                        codigo.run_method('focus')
                    else: 
                        ui.notify(msg, type='negative')

                ui.button('Guardar / Actualizar', on_click=guardar).classes('w-full mt-4 bg-green-700 text-white')
                
                # Tip visual
                with ui.row().classes('w-full items-center gap-2 mt-4 text-gray-400 justify-center'):
                    ui.icon('qr_code_scanner')
                    ui.label('Escanea para autocompletar').classes('text-xs italic')

            # =================================================
            # PANEL DERECHO: TABLA
            # =================================================
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('Existencias Actuales').classes('text-lg font-bold text-slate-700')
                    buscar = ui.input(placeholder='Buscar...').props('dense outlined rounded icon=search').classes('w-64')
                
                columns = [
                    {'name': 'codigo', 'label': 'SKU', 'field': 'codigo', 'align': 'left', 'classes': 'font-mono text-xs text-gray-500 font-bold'},
                    {'name': 'descripcion', 'label': 'Producto', 'field': 'descripcion', 'align': 'left', 'sortable': True, 'classes': 'font-semibold'},
                    {'name': 'categoria', 'label': 'Cat.', 'field': 'categoria', 'align': 'center', 'classes': 'text-xs bg-gray-100 rounded px-2'},
                    {'name': 'cantidad', 'label': 'Stock', 'field': 'cantidad', 'align': 'center', 'sortable': True, 'classes': 'font-bold text-lg'},
                    {'name': 'precio_venta', 'label': 'Precio', 'field': 'precio_formateado', 'align': 'right', 'classes': 'text-green-700 font-bold'},
                    {'name': 'acciones', 'label': '', 'field': 'acciones', 'align': 'center'}, 
                ]
                
                tabla_inv = ui.table(columns=columns, rows=[], row_key='id', pagination=10).classes('w-full')
                
                # Conexión del evento 'eliminar' del slot de la tabla a la función Python
                tabla_inv.on('eliminar', lambda e: eliminar_producto(e.args))
                
                actualizar_tabla()
                buscar.on('input', lambda e: setattr(tabla_inv, 'filter', e.value))

    # --- DIALOGO CONFIGURACIÓN ---
    with ui.dialog() as dialog_config, ui.card():
        ui.label('Configuración de Inventario').classes('text-lg font-bold text-slate-700')
        ui.label('Avisar cuando el stock sea menor a:').classes('text-sm text-gray-500')
        
        dialog_config.valor_input = ui.number('Cantidad Mínima', format='%.0f').classes('w-full')
        
        def guardar_config():
            # --- GUARDIA DE SEGURIDAD (Configuración de Alerta) ---
            if not app.storage.user.get('authenticated', False):
                ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                ui.navigate.to('/login?expired=true')
                return

            if dialog_config.valor_input.value is not None:
                nuevo_val = int(dialog_config.valor_input.value)
                db.set_stock_minimo(nuevo_val)
                ui.notify(f'Alerta configurada a < {nuevo_val} unidades', type='positive')
                actualizar_tabla()
                dialog_config.close()

        ui.button('Guardar Preferencia', on_click=guardar_config).classes('w-full bg-slate-800 text-white')