from nicegui import ui, app
from Db import database as db

def show():
    
    # --- FUNCIONES DE ACTUALIZACIÓN ---
    def actualizar_tabla():
        # Obtenemos datos
        servicios = db.obtener_catalogo_servicios()
        
        # Formateo visual
        rows = []
        for s in servicios:
            row = dict(s)
            row['precio_fmt'] = f"${row['precio_base']:,.2f}"
            rows.append(row)
            
        tabla_servicios.rows = rows
        tabla_servicios.update()

    def guardar_servicio():
        # Validación básica
        if not nombre.value or not precio.value:
            ui.notify('Nombre y Precio son obligatorios', type='warning')
            return

        # Guardar en DB
        ok, msg = db.crear_servicio_catalogo(
            nombre.value,
            float(precio.value),
            categoria.value,
            descripcion.value or ""
        )

        if ok:
            ui.notify(msg, type='positive')
            # Limpiar formulario
            nombre.value = ''
            precio.value = None
            descripcion.value = ''
            actualizar_tabla()
        else:
            ui.notify(msg, type='negative')

    def eliminar_servicio(id_servicio):
        db.eliminar_servicio_catalogo(id_servicio)
        ui.notify('Servicio eliminado del catálogo', type='info')
        actualizar_tabla()

    # --- INTERFAZ ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-slate-50'):
        
        # 1. ENCABEZADO
        with ui.row().classes('items-center gap-2 mb-2'):
            ui.icon('design_services', size='lg', color='indigo')
            with ui.column().classes('gap-0'):
                ui.label('Catálogo de Mano de Obra').classes('text-2xl font-bold text-slate-800')
                ui.label('Define los precios base para servicios estandarizados.').classes('text-sm text-gray-500')

        # 2. CONTENEDOR SPLIT
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # --- PANEL IZQUIERDO: ALTA ---
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg border-t-4 border-indigo-600'):
                ui.label('Nuevo Servicio').classes('text-lg font-bold text-slate-700 mb-2')
                
                nombre = ui.input('Nombre del Servicio').props('placeholder="Ej: Afinación Mayor 4 Cil"').classes('w-full font-bold')
                
                with ui.row().classes('w-full'):
                    categoria = ui.select(['Mantenimiento', 'Reparación', 'Diagnóstico', 'Instalación', 'Hojalatería'], 
                                          label='Categoría', value='Mantenimiento').classes('w-1/2 pr-1')
                    precio = ui.number('Precio Base', format='%.2f').props('prefix="$"').classes('w-1/2 pl-1')
                
                descripcion = ui.textarea('Detalles / Alcance').props('rows=3 placeholder="Incluye lavado de inyectores..."').classes('w-full')
                
                ui.button('Guardar en Catálogo', icon='save', on_click=guardar_servicio).classes('w-full mt-4 bg-indigo-700 text-white')

            # --- PANEL DERECHO: TABLA ---
            with ui.card().classes('flex-grow p-4 shadow-lg'):
                ui.label('Servicios Activos').classes('text-lg font-bold text-slate-700 mb-2')
                
                columns = [
                    {'name': 'nombre', 'label': 'Servicio', 'field': 'nombre', 'align': 'left', 'classes': 'font-bold'},
                    {'name': 'categoria', 'label': 'Tipo', 'field': 'categoria', 'align': 'center', 'classes': 'text-xs bg-indigo-50 text-indigo-700 rounded px-2 uppercase'},
                    {'name': 'precio', 'label': 'Precio Sugerido', 'field': 'precio_fmt', 'align': 'right', 'classes': 'text-green-700 font-mono font-bold'},
                    {'name': 'descripcion', 'label': 'Detalles', 'field': 'descripcion', 'align': 'left', 'classes': 'text-gray-400 italic text-xs truncate max-w-[200px]'},
                    {'name': 'acciones', 'label': '', 'field': 'acciones', 'align': 'center'}
                ]
                
                tabla_servicios = ui.table(columns=columns, rows=[], row_key='id', pagination=8).classes('w-full')
                
                # Slot de borrar
                tabla_servicios.add_slot('body-cell-acciones', '''
                    <q-td :props="props">
                        <q-btn icon="delete" size="sm" color="grey-4" text-color="red" flat round 
                               @click="$parent.$emit('borrar', props.row.id)">
                            <q-tooltip>Eliminar</q-tooltip>
                        </q-btn>
                    </q-td>
                ''')
                
                tabla_servicios.on('borrar', lambda e: eliminar_servicio(e.args))
                actualizar_tabla()