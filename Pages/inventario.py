from nicegui import ui
from Db import database as db

def show():
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # Cabecera
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Inventario de Refacciones').classes('text-2xl font-bold text-gray-800')
            
            # --- NUEVO: BOTÓN DE CONFIGURACIÓN ---
            with ui.row().classes('items-center'):
                def abrir_config():
                    limite_actual = db.get_stock_minimo()
                    dialog_config.valor_input.value = limite_actual
                    dialog_config.open()
                
                ui.button('Configurar Alertas', icon='settings', on_click=abrir_config).classes('bg-slate-700 text-white')
                ui.icon('inventory_2', size='lg', color='primary').classes('ml-4')

        with ui.row().classes('w-full gap-6'):
            
            # --- PANEL IZQUIERDO ---
            with ui.card().classes('w-1/3 p-4 shadow-lg'):
                ui.label('Nuevo Producto').classes('text-lg font-semibold mb-2')
                codigo = ui.input('Código / SKU', placeholder='Escanea...').classes('w-full')
                descripcion = ui.input('Descripción').classes('w-full')
                categoria = ui.select(['General', 'Llantas', 'Frenos', 'Motor', 'Eléctrico'], label='Categoría').classes('w-full')
                with ui.row().classes('w-full'):
                    cantidad = ui.number('Stock Inicial', value=1, format='%.0f').classes('w-1/2 pr-1')
                    precio = ui.number('Precio Venta').classes('w-1/2 pl-1').props('prefix="$"')

                def guardar():
                    if not codigo.value or not descripcion.value: return
                    exito, msg = db.agregar_producto(codigo.value, descripcion.value, int(cantidad.value), float(precio.value or 0), categoria.value)
                    if exito:
                        ui.notify(msg, type='positive')
                        codigo.value = ''
                        descripcion.value = ''
                        actualizar_tabla()
                    else: ui.notify(msg, type='negative')

                ui.button('Guardar en Almacén', on_click=guardar).classes('w-full mt-4 bg-green-600 text-white')
                ui.markdown('**Tip:** Escanea el código de barras directamente.').classes('text-xs text-gray-500 mt-4')

            # --- PANEL DERECHO ---
            with ui.card().classes('w-2/3 p-4 shadow-lg'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('Existencias Actuales').classes('text-lg font-semibold')
                    buscar = ui.input(placeholder='Buscar...').props('dense outlined rounded icon=search')
                
                columns = [
                    {'name': 'codigo', 'label': 'SKU', 'field': 'codigo', 'align': 'left', 'classes': 'font-mono text-xs'},
                    {'name': 'descripcion', 'label': 'Producto', 'field': 'descripcion', 'align': 'left', 'sortable': True},
                    {'name': 'categoria', 'label': 'Cat.', 'field': 'categoria', 'align': 'center'},
                    {'name': 'cantidad', 'label': 'Stock', 'field': 'cantidad', 'align': 'center', 'sortable': True},
                    {'name': 'precio_venta', 'label': 'Precio', 'field': 'precio_formateado', 'align': 'right'},
                ]
                
                tabla_inv = ui.table(columns=columns, rows=[], row_key='id').classes('w-full')

                def actualizar_tabla():
                    datos_raw = db.obtener_inventario()
                    # Obtenemos el límite dinámico para saber qué pintar de rojo
                    limite_alerta = db.get_stock_minimo()
                    
                    datos_procesados = []
                    for row in datos_raw:
                        r = dict(row)
                        r['precio_formateado'] = f"${r['precio_venta']:,.2f}"
                        datos_procesados.append(r)
                    
                    tabla_inv.rows = datos_procesados
                    
                    # Actualizamos la regla visual dinámicamente
                    # Nota: Borramos slots anteriores y ponemos el nuevo con el límite actual
                    tabla_inv._props['slots'] = {} 
                    tabla_inv.add_slot('body-cell-cantidad', f'''
                        <q-td :props="props" :class="props.value < {limite_alerta} ? 'bg-red-100 text-red-700 font-bold' : ''">
                            {{{{ props.value }}}}
                        </q-td>
                    ''')
                    tabla_inv.update()
                
                actualizar_tabla()
                buscar.on('input', lambda e: setattr(tabla_inv, 'filter', e.value))

    # --- DIALOGO DE CONFIGURACION (Global en el módulo) ---
    with ui.dialog() as dialog_config, ui.card():
        ui.label('Configuración de Inventario').classes('text-lg font-bold')
        ui.label('Avisar cuando el stock sea menor a:').classes('text-sm text-gray-600')
        
        dialog_config.valor_input = ui.number('Cantidad Mínima', format='%.0f').classes('w-full')
        
        def guardar_config():
            nuevo_val = int(dialog_config.valor_input.value)
            db.set_stock_minimo(nuevo_val)
            ui.notify(f'Alerta configurada a < {nuevo_val} unidades', type='positive')
            actualizar_tabla() # Para que se repinten los rojos
            dialog_config.close()

        ui.button('Guardar Preferencia', on_click=guardar_config).classes('w-full bg-slate-800 text-white')