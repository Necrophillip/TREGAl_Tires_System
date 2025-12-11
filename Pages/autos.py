from nicegui import ui, app
from Db import database as db

def show():
    # --- Variables de Estado ---
    todos_los_autos = []

    # --- Funciones de Lógica ---
    def filtrar_autos(e):
        # CORRECCIÓN BUG: Detectamos si 'e' es un Evento (UI) o un Diccionario (Manual)
        if isinstance(e, dict):
            val = e.get('value') # Es un diccionario manual
        else:
            val = e.value # Es un evento de NiceGUI
            
        texto = str(val).lower() if val else ""
        
        if not texto:
            tabla_autos.rows = todos_los_autos
        else:
            # Filtro multi-campo poderoso
            tabla_autos.rows = [
                row for row in todos_los_autos
                if texto in str(row['placas']).lower() 
                or texto in str(row['modelo']).lower() 
                or texto in str(row['dueno_nombre']).lower()
                or texto in str(row['num_economico']).lower()
                or texto in str(row['vin']).lower()
            ]
        tabla_autos.update()

    def cargar_datos_tabla():
        nonlocal todos_los_autos
        todos_los_autos = db.obtener_vehiculos_con_dueno()
        
        # Re-aplicar filtro si ya había algo escrito
        if input_busqueda.value:
            # Pasamos un diccionario, pero ahora filtrar_autos ya sabe leerlo
            filtrar_autos({'value': input_busqueda.value})
        else:
            tabla_autos.rows = todos_los_autos
            tabla_autos.update()

    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. ENCABEZADO
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('directions_car', size='lg', color='primary')
                ui.label('Gestión de Vehículos').classes('text-2xl font-bold text-gray-800')

        # 2. CONTENEDOR SPLIT VIEW
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # =================================================
            # PANEL IZQUIERDO: FORMULARIO
            # =================================================
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-blue-500'):
                ui.label('Registrar Vehículo').classes('text-lg font-bold text-slate-700 mb-2')
                
                # 1. Selector de Dueño
                opciones_clientes = db.obtener_clientes_para_select()
                select_cliente = ui.select(options=opciones_clientes, label='Seleccionar Dueño', with_input=True).classes('w-full')
                
                # Botón refrescar clientes
                def actualizar_lista_duenos():
                    select_cliente.options = db.obtener_clientes_para_select()
                    select_cliente.update()
                    ui.notify('Lista de clientes actualizada', type='positive')
                
                with ui.row().classes('w-full justify-end mt-[-8px] mb-2'):
                     ui.button('Actualizar lista', on_click=actualizar_lista_duenos, icon='refresh').props('flat dense size=sm color=blue')

                ui.separator().classes('mb-4')

                # 2. Datos del auto
                placas = ui.input('Placas / Patente').classes('w-full font-bold')
                modelo = ui.input('Modelo (Ej. Nissan Versa)').classes('w-full')
                
                with ui.row().classes('w-full gap-2'):
                    anio = ui.number('Año', format='%.0f').classes('w-1/3 pr-1')
                    color = ui.input('Color').classes('w-2/3 pl-1')

                with ui.row().classes('w-full gap-2'):
                    num_economico = ui.input('No. Eco').classes('w-1/3')
                    vin = ui.input('VIN / Serie').classes('w-2/3')
                
                kilometraje = ui.input('Kilometraje Actual').classes('w-full').props('type=number suffix="km"')

                def guardar():
                    # Validaciones
                    if not app.storage.user.get('authenticated', False):
                        ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                        ui.navigate.to('/login?expired=true')
                        return
                    if not select_cliente.value:
                        ui.notify('Debes seleccionar un dueño', type='warning'); return
                    if not placas.value or not modelo.value:
                        ui.notify('Placas y Modelo son obligatorios', type='warning'); return

                    # Guardar en DB (CORREGIDO: Usando los nombres de argumentos de database.py)
                    db.agregar_vehiculo(
                        placas=placas.value.upper(),
                        modelo=modelo.value,
                        anio=int(anio.value) if anio.value else 0,
                        color=color.value,
                        cid=select_cliente.value,       # <--- Antes decía cliente_id
                        num=num_economico.value or "",  # <--- Antes decía num_economico
                        vin=vin.value or "",
                        km=kilometraje.value or ""      # <--- Antes decía kilometraje
                    )
                    ui.notify(f'Vehículo {placas.value} agregado!', type='positive')
                    
                    # Limpiar
                    placas.value = ''; modelo.value = ''; anio.value = None
                    color.value = ''; num_economico.value = ''; vin.value = ''; kilometraje.value = ''
                    
                    # Recargar tabla derecha
                    cargar_datos_tabla()

                ui.button('Guardar Vehículo', on_click=guardar).classes('w-full mt-4 bg-slate-800 text-white')

            # =================================================
            # PANEL DERECHO: TABLA
            # =================================================
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                # CABECERA CON BUSCADOR
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('Parque Vehicular').classes('text-lg font-bold text-slate-700')
                    
                    # --- BUSCADOR ---
                    with ui.row().classes('items-center gap-2'):
                        input_busqueda = ui.input(placeholder='Buscar placa, modelo, dueño...').props('dense outlined rounded debounce="300"').classes('w-72').on('input', filtrar_autos)
                        with input_busqueda.add_slot('append'):
                            ui.icon('search')
                            
                        ui.button(icon='refresh', on_click=cargar_datos_tabla).props('flat round dense')
                
                columns = [
                    {'name': 'placas', 'label': 'Placas', 'field': 'placas', 'sortable': True, 'align': 'left', 'classes': 'font-bold bg-slate-100 rounded px-2'},
                    {'name': 'num_economico', 'label': 'No. Eco', 'field': 'num_economico', 'align': 'center', 'sortable': True},
                    {'name': 'modelo', 'label': 'Modelo', 'field': 'modelo', 'align': 'left', 'classes': 'font-semibold'},
                    {'name': 'kilometraje', 'label': 'Kms', 'field': 'kilometraje', 'align': 'right', 'classes': 'text-gray-500'},
                    {'name': 'anio', 'label': 'Año', 'field': 'anio', 'align': 'center'},
                    {'name': 'vin', 'label': 'VIN', 'field': 'vin', 'align': 'left', 'classes': 'text-gray-400 text-xs italic'},
                    {'name': 'dueno_nombre', 'label': 'Dueño', 'field': 'dueno_nombre', 'align': 'left', 'classes': 'text-blue-600 font-bold'},
                ]
                
                rows = []
                tabla_autos = ui.table(columns=columns, rows=rows, row_key='id', pagination=8).classes('w-full')
                
                # Carga inicial
                cargar_datos_tabla()