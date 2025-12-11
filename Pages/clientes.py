from nicegui import ui, app 
from Db import database as db

def show():
    # --- Variables de Estado (Para el Buscador) ---
    todos_los_clientes = []
    
    # --- Referencias UI (Declarar antes para usar en funciones) ---
    input_busqueda = None 

    # --- Definición de Funciones ---
    def filtrar(e):
        """Filtra la tabla en memoria por Nombre, Teléfono o Email"""
        # Validación robusta (Evento UI vs Diccionario manual)
        if isinstance(e, dict):
            val = e.get('value')
        else:
            val = e.value
            
        texto = str(val).lower() if val else ""
        
        if not texto:
            tabla_clientes.rows = todos_los_clientes
        else:
            # Filtramos por Nombre, Teléfono o Email
            tabla_clientes.rows = [
                c for c in todos_los_clientes
                if texto in str(c['nombre']).lower() 
                or texto in str(c['telefono']).lower()
                or texto in str(c['email']).lower()
            ]
        tabla_clientes.update()

    def actualizar_tabla():
        nonlocal todos_los_clientes
        # 1. Traemos todo de la DB a memoria
        todos_los_clientes = db.obtener_clientes()
        
        # 2. Si el buscador tiene texto, reaplicamos el filtro
        # (Usamos el 'safeguard' de diccionario para evitar errores)
        if input_busqueda and input_busqueda.value:
            filtrar({'value': input_busqueda.value})
        else:
            tabla_clientes.rows = todos_los_clientes
            tabla_clientes.update()
        
    def eliminar_cliente(cliente_id):
        # --- GUARDIA DE SEGURIDAD ---
        if not app.storage.user.get('authenticated', False):
            ui.notify('Sesión expirada. Acceso denegado.', type='negative')
            ui.navigate.to('/login?expired=true')
            return

        exito, msg = db.eliminar_cliente_por_id(cliente_id)
        if exito:
            ui.notify(msg, type='positive')
            actualizar_tabla()
        else:
            ui.notify(msg, type='negative')

    def confirmar_eliminacion(cliente_id):
        dialog_confirmar_eliminar.sid = cliente_id
        dialog_confirmar_eliminar.open()

    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. ENCABEZADO Y CONFIGURACIÓN
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('group', size='lg', color='primary')
                ui.label('Gestión de Clientes').classes('text-2xl font-bold text-gray-800')
            
            # Configuración de Alerta
            with ui.card().classes('flex-row items-center gap-2 p-2 bg-yellow-50 border-yellow-200 border shadow-sm'):
                ui.icon('notifications_active', color='orange')
                ui.label('Recordar servicio cada:').classes('text-sm font-bold text-gray-600')
                
                meses_input = ui.number(value=db.get_meses_alerta(), min=1, max=24, format='%.0f').props('dense outlined input-style="width: 40px; text-align: center"').classes('w-16')
                ui.label('meses').classes('text-sm text-gray-600')

                def actualizar_config():
                    if not app.storage.user.get('authenticated', False):
                        ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                        ui.navigate.to('/login?expired=true')
                        return
                        
                    if meses_input.value:
                        db.set_meses_alerta(int(meses_input.value))
                        actualizar_tabla()
                        ui.notify(f'Alertas configuradas a {int(meses_input.value)} meses', type='positive')

                meses_input.on('change', actualizar_config)

        # 2. CONTENEDOR SPLIT VIEW
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # 1. Panel Izquierdo: Formulario
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-blue-600'):
                ui.label('Nuevo Cliente').classes('text-lg font-bold text-slate-700 mb-2')
                
                nombre = ui.input('Nombre Completo').classes('w-full')
                telefono = ui.input('Teléfono').classes('w-full')
                email = ui.input('Email').classes('w-full')
                notas = ui.textarea('Notas').classes('w-full').props('rows=3')

                def guardar():
                    if not app.storage.user.get('authenticated', False):
                        ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                        ui.navigate.to('/login?expired=true')
                        return

                    if not nombre.value:
                        ui.notify('El nombre es obligatorio', type='warning'); return
                    
                    # Usamos argumentos posicionales según tu definición en database.py
                    db.agregar_cliente(nombre.value, telefono.value, email.value, notas.value)
                    ui.notify(f'Cliente {nombre.value} guardado!', type='positive')
                    
                    nombre.value = ''; telefono.value = ''; email.value = ''; notas.value = ''
                    actualizar_tabla()

                ui.button('Guardar Cliente', on_click=guardar).classes('w-full mt-4 bg-blue-600 text-white')

            # 2. Panel Derecho: Tabla de Clientes
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                
                # CABECERA CON BUSCADOR
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('Directorio & Estado').classes('text-lg font-bold text-slate-700')
                    
                    # --- BUSCADOR INTELIGENTE ---
                    with ui.row().classes('items-center gap-2'):
                        input_busqueda = ui.input(placeholder='Buscar por nombre o tel...').props('dense outlined rounded debounce="300"').classes('w-64').on('input', filtrar)
                        with input_busqueda.add_slot('append'):
                            ui.icon('search')
                            
                        ui.button(icon='refresh', on_click=lambda: actualizar_tabla()).props('flat round dense color=grey')
                
                columns = [
                    {'name': 'nombre', 'label': 'Cliente', 'field': 'nombre', 'align': 'left', 'sortable': True, 'classes': 'font-bold text-slate-700'},
                    {'name': 'telefono', 'label': 'Teléfono', 'field': 'telefono', 'align': 'left'},
                    {'name': 'ultimo_servicio_fmt', 'label': 'Última Visita', 'field': 'ultimo_servicio_fmt', 'align': 'center', 'sortable': True},
                    {'name': 'status_alerta', 'label': 'Estado', 'field': 'status_alerta', 'align': 'center', 'sortable': True, 'classes': 'font-bold'},
                    {'name': 'notas', 'label': 'Notas', 'field': 'notas', 'align': 'left', 'classes': 'text-gray-400 italic text-xs'},
                    {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'}, 
                ]
                
                # Inicializamos vacío, la función cargar_datos lo llenará
                rows = []
                tabla_clientes = ui.table(columns=columns, rows=rows, row_key='id', pagination=10).classes('w-full')

                # SLOTS
                tabla_clientes.add_slot('body-cell-acciones', r'''
                    <q-td :props="props">
                        <q-btn icon="delete" size="sm" color="negative" flat round 
                               @click="$parent.$emit('confirmar_eliminar', props.row.id)">
                            <q-tooltip>Eliminar Cliente</q-tooltip>
                        </q-btn>
                    </q-td>
                ''')
                
                tabla_clientes.add_slot('body-cell-status_alerta', r'''
                    <q-td :props="props">
                        <div v-if="props.value.includes('Vencido')" class="text-red-600 bg-red-50 px-2 py-1 rounded-full text-xs border border-red-200">
                            {{ props.value }}
                        </div>
                        <div v-else-if="props.value.includes('Al día')" class="text-green-600 bg-green-50 px-2 py-1 rounded-full text-xs border border-green-200">
                            {{ props.value }}
                        </div>
                        <div v-else class="text-gray-500 text-xs">
                            {{ props.value }}
                        </div>
                    </q-td>
                ''')
                
                tabla_clientes.on('confirmar_eliminar', lambda e: confirmar_eliminacion(e.args))
                
                # Carga inicial de datos
                actualizar_tabla()


    # --- DIALOGO DE CONFIRMACION ---
    with ui.dialog() as dialog_confirmar_eliminar, ui.card().classes('w-96'):
        ui.label('⚠️ Eliminación Crítica').classes('text-xl font-bold text-red-700')
        ui.label('ADVERTENCIA: ¿Estás seguro de eliminar este cliente?').classes('my-2 font-bold')
        ui.label('Se eliminarán TODOS los vehículos y registros de servicio asociados a este cliente.').classes('text-sm text-gray-600')
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancelar', on_click=dialog_confirmar_eliminar.close).props('flat')
            ui.button('Eliminar TODO', on_click=lambda: (eliminar_cliente(dialog_confirmar_eliminar.sid), dialog_confirmar_eliminar.close())).classes('bg-red-700 text-white')