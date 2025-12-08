from nicegui import ui
from Db import database as db
def show():
    # Contenedor principal de la pestaña con padding y fondo gris muy claro
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # --- Título y Cabecera ---
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Gestión de Clientes').classes('text-2xl font-bold text-gray-800')
            ui.icon('group', size='lg', color='primary')

        # --- Área de Trabajo (Dividida en 2 columnas: Formulario y Tabla) ---
        with ui.row().classes('w-full gap-6'):
            
            # 1. Panel Izquierdo: Formulario de Registro
            with ui.card().classes('w-1/3 p-4 shadow-lg'):
                ui.label('Nuevo Cliente').classes('text-lg font-semibold mb-2')
                
                nombre = ui.input('Nombre Completo').classes('w-full')
                telefono = ui.input('Teléfono').classes('w-full')
                email = ui.input('Email').classes('w-full')
                notas = ui.textarea('Notas').classes('w-full')

                def guardar():
                    if not nombre.value:
                        ui.notify('El nombre es obligatorio', type='warning')
                        return
                    
                    db.agregar_cliente(nombre.value, telefono.value, email.value, notas.value)
                    ui.notify(f'Cliente {nombre.value} guardado!', type='positive')
                    
                    # Limpiar campos y recargar tabla
                    nombre.value = ''
                    telefono.value = ''
                    email.value = ''
                    notas.value = ''
                    tabla_clientes.rows = db.obtener_clientes()
                    tabla_clientes.update()

                ui.button('Guardar Cliente', on_click=guardar).classes('w-full mt-4 bg-blue-600 text-white')

            # 2. Panel Derecho: Tabla de Clientes
            with ui.card().classes('w-2/3 p-4 shadow-lg'):
                ui.label('Directorio').classes('text-lg font-semibold mb-2')
                
                # Definición de columnas
                columns = [
                    {'name': 'nombre', 'label': 'Nombre', 'field': 'nombre', 'align': 'left', 'sortable': True},
                    {'name': 'telefono', 'label': 'Teléfono', 'field': 'telefono', 'align': 'left'},
                    {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left'},
                    {'name': 'notas', 'label': 'Notas', 'field': 'notas', 'align': 'left'},
                    {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
                ]
                
                # Carga inicial de datos
                rows = db.obtener_clientes()
                
                tabla_clientes = ui.table(columns=columns, rows=rows, row_key='nombre').classes('w-full')
                
                # Agregar slots para botones de borrar (Opcional avanzado, por ahora simple)
                # Nota: NiceGUI permite slots personalizados, lo veremos si lo necesitas.