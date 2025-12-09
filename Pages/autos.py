from nicegui import ui, app
from nicegui import ui
from Db import database as db

def show():
    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. ENCABEZADO
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('directions_car', size='lg', color='primary')
                ui.label('Gestión de Vehículos').classes('text-2xl font-bold text-gray-800')

        # 2. CONTENEDOR SPLIT VIEW (Misma lógica que Servicios)
        # 'flex-nowrap': Prohíbe que se bajen los elementos
        # 'items-start': Alineación superior
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # =================================================
            # PANEL IZQUIERDO: FORMULARIO (Fijo y Sticky)
            # =================================================
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-blue-500'):
                ui.label('Registrar Vehículo').classes('text-lg font-bold text-slate-700 mb-2')
                
                # 1. Selector de Dueño
                opciones_clientes = db.obtener_clientes_para_select()
                select_cliente = ui.select(options=opciones_clientes, label='Seleccionar Dueño', with_input=True).classes('w-full')
                
                # Botón refrescar clientes (pequeño y alineado)
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

                # --- NUEVOS CAMPOS (Integrados) ---
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

                    # Guardar en DB
                    db.agregar_vehiculo(
                        placas=placas.value.upper(), # Forzamos mayúsculas
                        modelo=modelo.value,
                        anio=int(anio.value) if anio.value else 0,
                        color=color.value,
                        cliente_id=select_cliente.value,
                        num_economico=num_economico.value or "",
                        vin=vin.value or "",
                        kilometraje=kilometraje.value or ""
                    )
                    
                    ui.notify(f'Vehículo {placas.value} agregado!', type='positive')
                    
                    # Limpiar
                    placas.value = ''; modelo.value = ''; anio.value = None
                    color.value = ''; num_economico.value = ''; vin.value = ''; kilometraje.value = ''
                    
                    # Recargar tabla derecha
                    tabla_autos.rows = db.obtener_vehiculos_con_dueno()
                    tabla_autos.update()

                ui.button('Guardar Vehículo', on_click=guardar).classes('w-full mt-4 bg-slate-800 text-white')

            # =================================================
            # PANEL DERECHO: TABLA (Espacio Restante)
            # =================================================
            # 'flex-grow' + 'w-0': Ocupa todo el espacio sobrante perfectamente
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('Parque Vehicular').classes('text-lg font-bold text-slate-700')
                    # Botón refresh tabla
                    ui.button(icon='refresh', on_click=lambda: (
                        setattr(tabla_autos, 'rows', db.obtener_vehiculos_con_dueno()), 
                        tabla_autos.update()
                    )).props('flat round dense')
                
                # Definición de columnas (Estilizadas)
                columns = [
                    {'name': 'placas', 'label': 'Placas', 'field': 'placas', 'sortable': True, 'align': 'left', 'classes': 'font-bold bg-slate-100 rounded px-2'},
                    {'name': 'num_economico', 'label': 'No. Eco', 'field': 'num_economico', 'align': 'center', 'sortable': True},
                    {'name': 'modelo', 'label': 'Modelo', 'field': 'modelo', 'align': 'left', 'classes': 'font-semibold'},
                    {'name': 'kilometraje', 'label': 'Kms', 'field': 'kilometraje', 'align': 'right', 'classes': 'text-gray-500'},
                    {'name': 'anio', 'label': 'Año', 'field': 'anio', 'align': 'center'},
                    {'name': 'vin', 'label': 'VIN', 'field': 'vin', 'align': 'left', 'classes': 'text-gray-400 text-xs italic'},
                    {'name': 'dueno_nombre', 'label': 'Dueño', 'field': 'dueno_nombre', 'align': 'left', 'classes': 'text-blue-600 font-bold'},
                ]
                
                rows = db.obtener_vehiculos_con_dueno()
                
                tabla_autos = ui.table(columns=columns, rows=rows, row_key='id', pagination=8).classes('w-full')