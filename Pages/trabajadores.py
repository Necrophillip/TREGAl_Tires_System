from nicegui import ui
from Db import database as db
from datetime import datetime

def show():
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # Cabecera
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Equipo de Trabajo y Nómina').classes('text-2xl font-bold text-gray-800')
            ui.icon('engineering', size='lg', color='primary')

        with ui.row().classes('w-full gap-6'):
            
            # --- PANEL IZQUIERDO: ALTA DE TRABAJADOR ---
            with ui.card().classes('w-1/3 p-4 shadow-lg'):
                ui.label('Nuevo Integrante').classes('text-lg font-semibold mb-2')
                
                nombre = ui.input('Nombre Completo').classes('w-full')
                fecha_ingreso = ui.input('Fecha Ingreso').classes('w-full').props('type=date')
                fecha_ingreso.value = datetime.now().strftime('%Y-%m-%d')
                
                # CORRECCIÓN: Usamos prefix para el signo de pesos, es más seguro que format
                sueldo_base = ui.number('Sueldo Base (Semanal)').classes('w-full').props('prefix="$"')

                def guardar_worker():
                    if not nombre.value:
                        ui.notify('Nombre obligatorio', type='warning')
                        return
                    
                    db.agregar_trabajador(nombre.value, fecha_ingreso.value, float(sueldo_base.value or 0))
                    ui.notify(f'Bienvenido {nombre.value}', type='positive')
                    nombre.value = ''
                    sueldo_base.value = None
                    actualizar_lista_empleados()

                ui.button('Contratar', on_click=guardar_worker).classes('w-full mt-4 bg-slate-800 text-white')

            # --- PANEL DERECHO: VISOR DE RENDIMIENTO ---
            with ui.card().classes('w-2/3 p-4 shadow-lg'):
                ui.label('Consulta de Rendimiento').classes('text-lg font-semibold mb-2')
                
                select_worker = ui.select(options={}, label='Seleccionar Trabajador').classes('w-full mb-4')
                
                stats_container = ui.column().classes('w-full')

                def cargar_estadisticas(e):
                    worker_id = e.value
                    if not worker_id: return
                    
                    datos = db.obtener_estadisticas_trabajador(worker_id)
                    stats_container.clear()
                    
                    # PROCESAMIENTO PREVIO: Formateamos el historial aquí para evitar lambdas en la tabla
                    historial_formateado = []
                    for h in datos['historial']:
                        # Convertimos a dict editable y agregamos campo de texto
                        item = dict(h)
                        item['monto_fmt'] = f"${item['monto_comision']:,.2f}"
                        historial_formateado.append(item)

                    with stats_container:
                        # Tarjetas de dinero
                        with ui.row().classes('w-full justify-around mb-4'):
                            with ui.card().classes('bg-green-100 p-2'):
                                ui.label('Comisiones Hoy').classes('text-xs text-green-800')
                                ui.label(f"${datos['hoy']:,.2f}").classes('text-xl font-bold text-green-900')
                            
                            with ui.card().classes('bg-blue-100 p-2'):
                                ui.label('Comisiones Mes').classes('text-xs text-blue-800')
                                ui.label(f"${datos['mes']:,.2f}").classes('text-xl font-bold text-blue-900')

                        ui.separator()
                        ui.label('Últimos Trabajos Realizados:').classes('font-bold mt-2')
                        
                        # Tabla de historial CORREGIDA (Sin lambdas)
                        ui.table(
                            columns=[
                                {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'align': 'left'},
                                {'name': 'desc', 'label': 'Tarea', 'field': 'descripcion_tarea', 'align': 'left'},
                                # Apuntamos al campo ya formateado 'monto_fmt'
                                {'name': 'monto', 'label': 'Comisión Ganada', 'field': 'monto_fmt', 'align': 'right'}
                            ],
                            rows=historial_formateado,
                            row_key='fecha'
                        ).classes('w-full')

                select_worker.on_value_change(cargar_estadisticas)

                def actualizar_lista_empleados():
                    select_worker.options = db.obtener_trabajadores_select()
                    select_worker.update()
                
                actualizar_lista_empleados()
                