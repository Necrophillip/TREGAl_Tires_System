from nicegui import ui, app # <-- Aseguramos la importación de 'app'
from Db import database as db
from datetime import datetime

def show():
    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. ENCABEZADO
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('engineering', size='lg', color='primary')
                ui.label('Equipo de Trabajo y Nómina').classes('text-2xl font-bold text-gray-800')

        # 2. CONTENEDOR SPLIT VIEW
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # =================================================
            # PANEL IZQUIERDO: ALTA DE TRABAJADOR (Formulario)
            # =================================================
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-purple-600'):
                ui.label('Nuevo Integrante').classes('text-lg font-bold text-slate-700 mb-2')
                
                nombre = ui.input('Nombre Completo').classes('w-full')
                fecha_ingreso = ui.input('Fecha Ingreso').classes('w-full').props('type=date')
                fecha_ingreso.value = datetime.now().strftime('%Y-%m-%d')
                
                sueldo_base = ui.number('Sueldo Base (Semanal)').classes('w-full').props('prefix="$"')

                def guardar_worker():
                    # --- GUARDIA DE SEGURIDAD (Contratar) ---
                    if not app.storage.user.get('authenticated', False):
                        ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                        ui.navigate.to('/login?expired=true')
                        return
                        
                    if not nombre.value:
                        ui.notify('Nombre obligatorio', type='warning'); return
                    
                    db.agregar_trabajador(nombre.value, fecha_ingreso.value, float(sueldo_base.value or 0))
                    ui.notify(f'Bienvenido {nombre.value}', type='positive')
                    nombre.value = ''; sueldo_base.value = None
                    actualizar_lista_empleados()

                ui.button('Contratar', on_click=guardar_worker).classes('w-full mt-4 bg-purple-700 text-white')
                ui.separator().classes('my-4')
                ui.label('Nota: El sueldo base es informativo.').classes('text-xs text-gray-400 italic text-center')

            # =================================================
            # PANEL DERECHO: VISOR DE RENDIMIENTO
            # =================================================
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Consulta de Rendimiento').classes('text-lg font-bold text-slate-700')
                    select_worker = ui.select(options={}, label='Seleccionar Trabajador').classes('w-64')

                stats_container = ui.column().classes('w-full gap-4')

                def cargar_estadisticas(e):
                    worker_id = e.value
                    if not worker_id: return
                    
                    # --- GUARDIA LIGERA (Solo para prevenir carga de datos si la sesión murió) ---
                    if not app.storage.user.get('authenticated', False):
                        ui.notify('Sesión inactiva. Recargue la página.', type='warning')
                        return
                        
                    datos = db.obtener_estadisticas_trabajador(worker_id)
                    stats_container.clear()
                    
                    # --- CÁLCULO ANTIGÜEDAD ---
                    texto_antiguedad = "N/A"
                    if datos['fecha_ingreso']:
                        try:
                            f_inicio = datetime.strptime(datos['fecha_ingreso'], "%Y-%m-%d")
                            dias = (datetime.now() - f_inicio).days
                            anios, meses = dias // 365, (dias % 365) // 30
                            if anios > 0: texto_antiguedad = f"{anios} Años, {meses} Meses"
                            elif meses > 0: texto_antiguedad = f"{meses} Meses"
                            else: texto_antiguedad = f"{dias} Días"
                        except: pass

                    # Formateo historial
                    historial_formateado = []
                    for h in datos['historial']:
                        item = dict(h)
                        item['monto_fmt'] = f"${item['monto_comision']:,.2f}"
                        historial_formateado.append(item)

                    with stats_container:
                        # 4 TARJETAS EN FILA
                        with ui.row().classes('w-full gap-4'):
                            
                            # 1. Especialidad
                            with ui.card().classes('w-1/4 p-3 bg-orange-50 border border-orange-200 shadow-sm'):
                                ui.label('Especialidad').classes('text-xs font-bold text-orange-800 uppercase')
                                ui.label(datos['especialidad']).classes('text-lg font-bold text-orange-700 leading-tight truncate').tooltip(datos['especialidad'])
                                ui.icon('stars').classes('absolute top-2 right-2 text-orange-200 text-3xl')

                            # 2. Antigüedad
                            with ui.card().classes('w-1/4 p-3 bg-purple-50 border border-purple-200 shadow-sm'):
                                ui.label('Antigüedad').classes('text-xs font-bold text-purple-800 uppercase')
                                ui.label(texto_antiguedad).classes('text-lg font-bold text-purple-700 truncate')
                                ui.icon('military_tech').classes('absolute top-2 right-2 text-purple-200 text-3xl')
                            
                            # 3. Hoy
                            with ui.card().classes('w-1/4 p-3 bg-green-50 border border-green-200 shadow-sm'):
                                ui.label('Ganado Hoy').classes('text-xs font-bold text-green-800 uppercase')
                                ui.label(f"${datos['hoy']:,.2f}").classes('text-xl font-bold text-green-700')
                                ui.icon('payments').classes('absolute top-2 right-2 text-green-200 text-3xl')
                            
                            # 4. Mes
                            with ui.card().classes('w-1/4 p-3 bg-blue-50 border border-blue-200 shadow-sm'):
                                ui.label('Acumulado Mes').classes('text-xs font-bold text-blue-800 uppercase')
                                ui.label(f"${datos['mes']:,.2f}").classes('text-xl font-bold text-blue-700')
                                ui.icon('savings').classes('absolute top-2 right-2 text-blue-200 text-3xl')

                        # Tabla Historial
                        ui.label('Últimos Trabajos Realizados').classes('text-md font-bold text-slate-600 mt-2')
                        
                        columns = [
                            {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'align': 'left', 'classes': 'text-gray-500 font-mono text-xs'},
                            {'name': 'desc', 'label': 'Tarea Realizada', 'field': 'descripcion_tarea', 'align': 'left', 'classes': 'font-semibold'},
                            {'name': 'monto', 'label': 'Comisión', 'field': 'monto_fmt', 'align': 'right', 'classes': 'text-green-700 font-bold'},
                        ]
                        
                        ui.table(columns=columns, rows=historial_formateado, row_key='fecha', pagination=5).classes('w-full')
                        
                        if not historial_formateado:
                             ui.label('Sin actividad reciente.').classes('w-full text-center text-gray-400 italic py-4')


                select_worker.on_value_change(cargar_estadisticas)

                def actualizar_lista_empleados():
                    select_worker.options = db.obtener_trabajadores_select()
                    select_worker.update()
                
                actualizar_lista_empleados()