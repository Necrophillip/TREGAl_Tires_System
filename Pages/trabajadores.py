from nicegui import ui, app 
from Db import database as db
from datetime import datetime

def show():
    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. ENCABEZADO
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('engineering', size='lg', color='primary')
                ui.label('Equipo de Trabajo y Usuarios').classes('text-2xl font-bold text-gray-800')

        # 2. CONTENEDOR SPLIT VIEW
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # =================================================
            # PANEL IZQUIERDO: GESTIÓN DE ALTA Y USUARIOS
            # =================================================
            with ui.column().classes('w-1/3 min-w-[350px] gap-4'):
                
                # --- TARJETA 1: CONTRATAR EMPLEADO (Mantenido) ---
                with ui.card().classes('w-full p-4 shadow-lg border-t-4 border-purple-600'):
                    ui.label('1. Nuevo Integrante (Nómina)').classes('text-lg font-bold text-slate-700 mb-2')
                    
                    nombre = ui.input('Nombre Completo').classes('w-full')
                    fecha_ingreso = ui.input('Fecha Ingreso').classes('w-full').props('type=date')
                    fecha_ingreso.value = datetime.now().strftime('%Y-%m-%d')
                    sueldo_base = ui.number('Sueldo Base (Semanal)').classes('w-full').props('prefix="$"')

                    def guardar_worker():
                        if not app.storage.user.get('authenticated', False):
                            ui.notify('Sesión expirada.', type='negative'); ui.navigate.to('/login?expired=true'); return
                            
                        if not nombre.value:
                            ui.notify('Nombre obligatorio', type='warning'); return
                        
                        db.agregar_trabajador(nombre.value, fecha_ingreso.value, float(sueldo_base.value or 0))
                        ui.notify(f'Bienvenido {nombre.value}', type='positive')
                        nombre.value = ''; sueldo_base.value = None
                        actualizar_todas_las_listas() # <--- Actualiza todo

                    ui.button('Contratar Empleado', on_click=guardar_worker).classes('w-full mt-2 bg-purple-700 text-white')

                # --- TARJETA 2: CREAR USUARIO DE SISTEMA (NUEVO) ---
                # Solo visible si eres ADMIN
                rol_actual = app.storage.user.get('rol', 'tecnico')
                
                if rol_actual == 'admin':
                    with ui.card().classes('w-full p-4 shadow-lg border-t-4 border-slate-800'):
                        ui.label('2. Crear Acceso al Sistema').classes('text-lg font-bold text-slate-700 mb-2')
                        ui.label('Asigna usuario y contraseña a un empleado.').classes('text-xs text-gray-400 mb-2')

                        # Selector para vincular con un trabajador existente
                        sel_worker_user = ui.select(options={}, label='Vincular a Trabajador').classes('w-full')
                        
                        txt_user = ui.input('Usuario (Login)').classes('w-full')
                        txt_pass = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full')
                        sel_rol = ui.select(options=['tecnico', 'admin'], value='tecnico', label='Nivel de Permisos').classes('w-full')

                        def crear_usuario_sistema():
                            if not app.storage.user.get('authenticated', False): return
                            
                            if not txt_user.value or not txt_pass.value:
                                ui.notify('Usuario y contraseña requeridos', type='warning'); return

                            # Llamamos a la nueva función de DB
                            # sel_worker_user.value envía el ID del trabajador (o None si es admin puro)
                            exito, msg = db.crear_usuario(txt_user.value, txt_pass.value, sel_rol.value, sel_worker_user.value)
                            
                            if exito:
                                ui.notify(f'Usuario {txt_user.value} creado exitosamente.', type='positive')
                                txt_user.value = ''; txt_pass.value = ''; sel_worker_user.value = None
                            else:
                                ui.notify(msg, type='negative')

                        ui.button('Generar Credenciales', on_click=crear_usuario_sistema).classes('w-full mt-4 bg-slate-800 text-white')

            # =================================================
            # PANEL DERECHO: VISOR DE RENDIMIENTO (Mantenido)
            # =================================================
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Consulta de Rendimiento').classes('text-lg font-bold text-slate-700')
                    select_worker = ui.select(options={}, label='Seleccionar Trabajador').classes('w-64')

                stats_container = ui.column().classes('w-full gap-4')

                def cargar_estadisticas(e):
                    worker_id = e.value
                    if not worker_id: return
                    if not app.storage.user.get('authenticated', False): return
                        
                    datos = db.obtener_estadisticas_trabajador(worker_id)
                    stats_container.clear()
                    
                    # Formateo historial
                    historial_formateado = []
                    for h in datos['historial']:
                        item = dict(h)
                        item['monto_fmt'] = f"${item['monto_comision']:,.2f}"
                        historial_formateado.append(item)

                    with stats_container:
                        # TARJETAS EN FILA
                        with ui.row().classes('w-full gap-4'):
                            with ui.card().classes('w-1/4 p-3 bg-orange-50 border border-orange-200 shadow-sm'):
                                ui.label('Especialidad').classes('text-xs font-bold text-orange-800 uppercase')
                                ui.label(datos['especialidad']).classes('text-lg font-bold text-orange-700 leading-tight truncate').tooltip(datos['especialidad'])
                                ui.icon('stars').classes('absolute top-2 right-2 text-orange-200 text-3xl')

                            with ui.card().classes('w-1/4 p-3 bg-purple-50 border border-purple-200 shadow-sm'):
                                ui.label('Antigüedad').classes('text-xs font-bold text-purple-800 uppercase')
                                texto_antiguedad = datos['fecha_ingreso'] if datos['fecha_ingreso'] else "Nuevo"
                                ui.label(texto_antiguedad).classes('text-lg font-bold text-purple-700 truncate')
                                ui.icon('military_tech').classes('absolute top-2 right-2 text-purple-200 text-3xl')
                            
                            with ui.card().classes('w-1/4 p-3 bg-green-50 border border-green-200 shadow-sm'):
                                ui.label('Ganado Hoy').classes('text-xs font-bold text-green-800 uppercase')
                                ui.label(f"${datos['hoy']:,.2f}").classes('text-xl font-bold text-green-700')
                                ui.icon('payments').classes('absolute top-2 right-2 text-green-200 text-3xl')
                            
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

                select_worker.on_value_change(cargar_estadisticas)

                def actualizar_todas_las_listas():
                    """Actualiza tanto el selector de estadísticas como el de creación de usuarios"""
                    trabajadores = db.obtener_trabajadores_select()
                    select_worker.options = trabajadores
                    select_worker.update()
                    
                    # Solo actualizamos el selector de usuarios si existe (si somos admin)
                    if 'sel_worker_user' in locals():
                        sel_worker_user.options = trabajadores
                        sel_worker_user.update()
                
                actualizar_todas_las_listas()