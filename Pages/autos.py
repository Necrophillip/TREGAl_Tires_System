from nicegui import ui
from Db import database as db
def show():
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # Cabecera
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Gestión de Vehículos').classes('text-2xl font-bold text-gray-800')
            ui.icon('directions_car', size='lg', color='primary')

        with ui.row().classes('w-full gap-6'):
            
            # --- FORMULARIO (Izquierda) ---
            with ui.card().classes('w-1/3 p-4 shadow-lg'):
                ui.label('Registrar Vehículo').classes('text-lg font-semibold mb-2')
                
                # 1. Selector de Dueño (Dropdown)
                # Obtenemos los clientes actuales de la DB
                opciones_clientes = db.obtener_clientes_para_select()
                select_cliente = ui.select(options=opciones_clientes, label='Seleccionar Dueño', with_input=True).classes('w-full')
                
                # 2. Datos del auto
                placas = ui.input('Placas / Patente').classes('w-full')
                modelo = ui.input('Modelo (Ej. Nissan Versa)').classes('w-full')
                
                with ui.row().classes('w-full'):
                    anio = ui.number('Año', format='%.0f').classes('w-1/2 pr-1')
                    color = ui.input('Color').classes('w-1/2 pl-1')

                def guardar():
                    # Validaciones básicas
                    if not select_cliente.value:
                        ui.notify('Debes seleccionar un dueño', type='warning')
                        return
                    if not placas.value or not modelo.value:
                        ui.notify('Placas y Modelo son obligatorios', type='warning')
                        return

                    # Guardar en DB
                    db.agregar_vehiculo(
                        placas=placas.value,
                        modelo=modelo.value,
                        anio=int(anio.value) if anio.value else 0,
                        color=color.value,
                        cliente_id=select_cliente.value
                    )
                    
                    ui.notify(f'Vehículo {placas.value} agregado!', type='positive')
                    
                    # Limpiar y recargar tabla
                    placas.value = ''
                    modelo.value = ''
                    anio.value = None
                    color.value = ''
                    # Recargar tabla
                    tabla_autos.rows = db.obtener_vehiculos_con_dueno()
                    tabla_autos.update()

                ui.button('Guardar Vehículo', on_click=guardar).classes('w-full mt-4 bg-slate-700 text-white')
                
                # Botón pequeño para refrescar la lista de dueños (por si acabas de agregar uno nuevo en la otra pestaña)
                def actualizar_lista_duenos():
                    select_cliente.options = db.obtener_clientes_para_select()
                    select_cliente.update()
                    ui.notify('Lista de clientes actualizada')
                
                ui.button('Refrescar Lista Clientes', on_click=actualizar_lista_duenos, icon='refresh').classes('w-full mt-2 text-xs')

            # --- TABLA (Derecha) ---
            with ui.card().classes('w-2/3 p-4 shadow-lg'):
                ui.label('Parque Vehicular').classes('text-lg font-semibold mb-2')
                
                columns = [
                    {'name': 'placas', 'label': 'Placas', 'field': 'placas', 'sortable': True, 'align': 'left'},
                    {'name': 'modelo', 'label': 'Modelo', 'field': 'modelo', 'align': 'left'},
                    {'name': 'color', 'label': 'Color', 'field': 'color', 'align': 'left'},
                    {'name': 'anio', 'label': 'Año', 'field': 'anio', 'align': 'center'},
                    {'name': 'dueno_nombre', 'label': 'Dueño', 'field': 'dueno_nombre', 'align': 'left', 'classes': 'font-bold text-blue-600'},
                ]
                
                rows = db.obtener_vehiculos_con_dueno()
                tabla_autos = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full')