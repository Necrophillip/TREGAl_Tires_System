from nicegui import ui, app 
from Db import database as db

def show():
    # --- Definición de funciones ---
    
    def actualizar_tabla():
        datos_raw = db.obtener_inventario()
        limite_alerta = db.get_stock_minimo()
        
        datos_procesados = []
        for row in datos_raw:
            r = dict(row)
            r['id'] = row['id']
            r['precio_formateado'] = f"${r['precio_venta']:,.2f}"
            
            # Formato visual del Stock: "5 Pza" o "10 Lt"
            umo = r.get('umo', 'Pza') or 'Pza' # Protección por si viene null
            r['stock_visual'] = f"{r['cantidad']} {umo}"
            
            datos_procesados.append(r)
        
        tabla_inv.rows = datos_procesados
        
        # Slot para pintar rojo si el stock es bajo
        tabla_inv.add_slot('body-cell-stock_visual', f'''
            <q-td :props="props" :class="props.row.cantidad < {limite_alerta} ? 'bg-red-50 text-red-600 border border-red-200 rounded font-bold' : 'text-slate-700 font-bold'">
                {{{{ props.value }}}}
            </q-td>
        ''')
        
        # Slot acciones
        tabla_inv.add_slot('body-cell-acciones', '''
            <q-td :props="props">
                <q-btn icon="delete" size="sm" color="negative" flat round 
                       @click="$parent.$emit('eliminar', props.row.id)"><q-tooltip>Eliminar</q-tooltip></q-btn>
            </q-td>
        ''')
        
        tabla_inv.update()

    def eliminar_producto(producto_id):
        if not app.storage.user.get('authenticated', False):
            ui.notify('Acceso denegado', type='negative'); return

        exito, msg = db.eliminar_producto_por_id(producto_id)
        if exito:
            ui.notify(f'Producto eliminado.', type='positive')
            actualizar_tabla()
        else:
            ui.notify(msg, type='negative')


    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. ENCABEZADO
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('inventory_2', size='lg', color='primary')
                ui.label('Almacén y Refacciones').classes('text-2xl font-bold text-gray-800')
            
            with ui.row().classes('items-center'):
                def abrir_config():
                    limite_actual = db.get_stock_minimo()
                    dialog_config.valor_input.value = limite_actual
                    dialog_config.open()
                ui.button('Configurar Alertas', icon='settings', on_click=abrir_config).props('outline color=slate-700')

        # 2. CONTENEDOR SPLIT VIEW
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # =================================================
            # PANEL IZQUIERDO: FORMULARIO (Alta/Edición)
            # =================================================
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-green-600'):
                lbl_titulo = ui.label('Gestión de Producto').classes('text-lg font-bold text-slate-700 mb-2')
                
                # Campos
                codigo = ui.input('Código / SKU', placeholder='Escanea...').classes('w-full font-mono font-bold')
                descripcion = ui.input('Descripción').classes('w-full')
                
                # Fila Categoría + UMO
                with ui.row().classes('w-full gap-2'):
                    cats = ['General', 'Llantas', 'Frenos', 'Motor', 'Eléctrico', 'Suspensión', 'Fluidos']
                    categoria = ui.select(cats, label='Categoría').classes('w-3/5')
                    
                    # --- NUEVO CAMPO UMO ---
                    umos = ['Pza', 'Lt', 'Juego', 'Kit', 'Par', 'Galón', 'Metro']
                    umo = ui.select(umos, label='Unidad', value='Pza').classes('w-2/5')
                
                with ui.row().classes('w-full gap-2'):
                    cantidad = ui.number('Cantidad (+)', value=1, format='%.0f').classes('w-1/2 pr-1')
                    precio = ui.number('Precio Venta').classes('w-1/2 pl-1').props('prefix="$"')

                # --- LÓGICA DE AUTOCOMPLETADO ---
                def buscar_sku():
                    sku = codigo.value
                    if not sku: return
                    
                    prod = db.obtener_producto_por_codigo(sku)
                    if prod:
                        # Rellenar formulario con datos existentes
                        descripcion.value = prod['descripcion']
                        categoria.value = prod['categoria']
                        precio.value = prod['precio_venta']
                        umo.value = prod.get('umo', 'Pza') # Cargar UMO guardada
                        
                        ui.notify(f'Encontrado: {prod["cantidad"]} {umo.value} en stock', type='info')
                        lbl_titulo.text = f'Editar / Sumar Stock'
                        cantidad.label = 'Cantidad a Sumar (+)'
                        cantidad.value = 1
                    else:
                        # Limpiar para nuevo
                        lbl_titulo.text = 'Nuevo Producto'
                        cantidad.label = 'Stock Inicial'
                        descripcion.value = ''
                        categoria.value = 'General'
                        precio.value = None
                        umo.value = 'Pza'

                codigo.on('change', buscar_sku)

                def guardar():
                    if not app.storage.user.get('authenticated', False): return

                    if not codigo.value or not descripcion.value:
                        ui.notify('Datos incompletos', type='warning'); return
                    
                    # Llamamos a DB con el nuevo campo UMO
                    exito, msg = db.gestionar_producto(
                        codigo.value, 
                        descripcion.value, 
                        int(cantidad.value), 
                        float(precio.value or 0), 
                        categoria.value,
                        umo.value # <--- Pasamos la UMO
                    )
                    
                    if exito:
                        ui.notify(msg, type='positive')
                        # Reset parcial
                        codigo.value = ''; descripcion.value = ''; cantidad.value = 1; precio.value = None
                        lbl_titulo.text = 'Gestión de Producto'
                        actualizar_tabla()
                        codigo.run_method('focus') # Regresar foco para seguir escaneando
                    else: 
                        ui.notify(msg, type='negative')

                ui.button('Guardar / Actualizar', on_click=guardar).classes('w-full mt-4 bg-green-700 text-white')
                
                with ui.row().classes('w-full items-center gap-2 mt-4 text-gray-400 justify-center'):
                    ui.icon('qr_code_scanner')
                    ui.label('Listo para lector de código de barras').classes('text-xs italic')

            # =================================================
            # PANEL DERECHO: TABLA DE STOCK
            # =================================================
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('Existencias').classes('text-lg font-bold text-slate-700')
                    buscar = ui.input(placeholder='Buscar...').props('dense outlined rounded icon=search').classes('w-64')
                
                columns = [
                    {'name': 'codigo', 'label': 'SKU', 'field': 'codigo', 'align': 'left', 'classes': 'font-mono text-xs text-gray-500 font-bold'},
                    {'name': 'descripcion', 'label': 'Producto', 'field': 'descripcion', 'align': 'left', 'sortable': True, 'classes': 'font-semibold'},
                    {'name': 'categoria', 'label': 'Cat.', 'field': 'categoria', 'align': 'center', 'classes': 'text-xs bg-gray-100 rounded px-2'},
                    # Usamos el campo combinado stock_visual
                    {'name': 'stock_visual', 'label': 'Stock', 'field': 'stock_visual', 'align': 'center', 'sortable': True}, 
                    {'name': 'precio_venta', 'label': 'Precio', 'field': 'precio_formateado', 'align': 'right', 'classes': 'text-green-700 font-bold'},
                    {'name': 'acciones', 'label': '', 'field': 'acciones', 'align': 'center'}, 
                ]
                
                tabla_inv = ui.table(columns=columns, rows=[], row_key='id', pagination=10).classes('w-full')
                tabla_inv.on('eliminar', lambda e: eliminar_producto(e.args))
                
                actualizar_tabla()
                buscar.on('input', lambda e: setattr(tabla_inv, 'filter', e.value))

    # --- DIALOGO CONFIGURACIÓN ALERTAS ---
    with ui.dialog() as dialog_config, ui.card():
        ui.label('Configuración de Alertas').classes('text-lg font-bold')
        dialog_config.valor_input = ui.number('Mínimo Global', format='%.0f').classes('w-full')
        
        def guardar_config():
            if dialog_config.valor_input.value is not None:
                db.set_stock_minimo(int(dialog_config.valor_input.value))
                ui.notify('Actualizado', type='positive'); actualizar_tabla(); dialog_config.close()

        ui.button('Guardar', on_click=guardar_config).classes('w-full bg-slate-800 text-white')