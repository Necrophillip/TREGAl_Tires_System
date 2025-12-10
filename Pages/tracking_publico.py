from nicegui import ui
from Db import database as db

# --- 1. CONFIGURACIÓN DE TRADUCCIÓN ROBUSTA ---
# Ahora entiende tanto texto limpio (Nuevo) como emojis (Viejo)
MAPA_ESTATUS = {
    # Lo que guarda el Dashboard actual (Texto limpio)
    'Recibido': 'Recibido',
    'Diagnóstico': 'Diagnóstico',
    'Piezas': 'Piezas',
    'Reparación': 'Reparación',
    'Listo': 'Listo',
    'Entregado': 'Entregado',
    
    # Variaciones con Emojis (Por si acaso quedó alguno viejo)
    '🔍 Diagnóstico': 'Diagnóstico',
    '📦 Esperando Piezas': 'Piezas',
    '🔧 Reparación': 'Reparación',
    '✅ Listo p/Entrega': 'Listo',
    '✅ PAGADO': 'Entregado' 
}

# El orden visual del Stepper
PASOS_ORDENADOS = ['Recibido', 'Diagnóstico', 'Piezas', 'Reparación', 'Listo', 'Entregado']

def show_page(uuid_publico: str):
    
    contenedor_dinamico = ui.column().classes('w-full items-center p-0')
    estado_anterior = {'val': None} 

    async def actualizar_interfaz():
        # 1. Consultar DB
        datos = db.obtener_info_publica_servicio(uuid_publico)
        
        if not datos:
            if estado_anterior['val'] != 'error': # Evitar redibujar error infinitamente
                contenedor_dinamico.clear()
                with contenedor_dinamico:
                    with ui.column().classes('h-screen justify-center items-center text-gray-400'):
                        ui.icon('cloud_off', size='4em')
                        ui.label('Enlace no encontrado.')
                estado_anterior['val'] = 'error'
            return

        # 2. Traducir Estatus (Mapeo)
        estatus_crudo = datos.get('estatus_detalle', 'Recibido')
        estatus_limpio = MAPA_ESTATUS.get(estatus_crudo, 'Recibido') 
        
        # DEBUG: Ver en consola qué está pasando (Solo para ti)
        print(f"🔄 Tracker Check | DB: '{estatus_crudo}' -> Mapped: '{estatus_limpio}'")

        # 3. Optimización: Si no cambió, no tocar la UI
        if estatus_limpio == estado_anterior['val']:
            return 
        
        estado_anterior['val'] = estatus_limpio
        
        # 4. Calcular índice
        try:
            indice_actual = PASOS_ORDENADOS.index(estatus_limpio)
        except ValueError:
            indice_actual = 0

        # 5. REDIBUJAR
        contenedor_dinamico.clear()
        
        with contenedor_dinamico:
            # HEADER
            with ui.row().classes('w-full bg-slate-900 p-4 justify-center shadow-md'):
                ui.icon('tire_repair', size='2em', color='white') 
                ui.label('TREGAL Tracker').classes('text-xl font-bold text-white tracking-widest')

            # TARJETA INFO
            with ui.card().classes('w-full max-w-md mt-6 p-6 shadow-sm border-t-4 border-blue-600 mx-4'):
                ui.label(f"{datos['modelo']}").classes('text-2xl font-bold text-slate-800')
                ui.label(f"Placas: {datos['placas']}").classes('text-md text-gray-500 font-mono bg-gray-100 px-2 rounded w-fit mt-1')
                
                ui.separator().classes('my-4')
                
                # Estatus Gigante
                color = 'text-green-600' if estatus_limpio == 'Listo' else 'text-blue-600'
                ui.label('Estatus Actual:').classes('text-xs font-bold text-gray-400 uppercase')
                ui.label(estatus_limpio).classes(f'text-3xl font-black {color} transition-all duration-500')
                
                ui.label(f"Ingreso: {datos['fecha']}").classes('text-xs text-gray-400 mt-2')

            # STEPPER
            with ui.card().classes('w-full max-w-md mt-4 p-4 shadow-sm mx-4'):
                ui.label('Línea de Tiempo').classes('font-bold text-slate-700 mb-4')
                
                with ui.stepper().props('vertical flat color=blue').classes('w-full'):
                    for i, paso in enumerate(PASOS_ORDENADOS):
                        # Lógica visual de iconos
                        if i < indice_actual:
                            props = 'done icon=check color=green'
                        elif i == indice_actual:
                            props = 'active icon=edit color=blue'
                        else:
                            props = 'icon=fiber_manual_record color=grey-4'
                        
                        # Render del paso
                        with ui.step(paso, title=paso).props(props):
                            if i == indice_actual:
                                ui.label('En proceso...').classes('text-xs text-blue-500 italic')

            # FOOTER
            with ui.column().classes('w-full max-w-md mt-8 p-4 items-center gap-2 mb-8'):
                ui.button('WhatsApp Taller', icon='whatsapp', color='green').classes('w-full shadow-lg')
                ui.label('TREGAL Tires & Services').classes('text-xs text-gray-300 mt-2')
            with ui.column().classes('w-full max-w-md mt-8 p-4 items-center gap-2 mb-8'):
                
                # 1. Leer número actualizado
                telefono_taller = db.get_whatsapp_taller()
                
                # 2. Construir Link API WhatsApp
                # Mensaje predefinido para que el cliente no tenga que escribir
                mensaje = f"Hola, estoy consultando el estatus de mi vehículo (Folio: {datos.get('modelo', 'Auto')})"
                link_wa = f"https://wa.me/{telefono_taller}?text={mensaje}"
                
                # 3. Botón con link dinámico
                ui.button('WhatsApp Taller', icon='whatsapp', color='green', on_click=lambda: ui.open(link_wa, new_tab=True)).classes('w-full shadow-lg')
                
                ui.label('TREGAL Tires & Services').classes('text-xs text-gray-300 mt-2')

    # Timer de actualización (cada 3 seg)
    ui.timer(0.1, actualizar_interfaz, once=True)
    ui.timer(3.0, actualizar_interfaz)