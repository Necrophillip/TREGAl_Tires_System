from nicegui import ui
from Db import database as db

# --- CONFIGURACIÓN VISUAL ---
# Mapeo de colores y textos para cada estado
CONFIG_ESTADOS = {
    'Recibido':    {'color': 'slate',  'icon': 'garage',       'msg': 'Tu auto ha ingresado al taller.'},
    'Diagnóstico': {'color': 'blue',   'icon': 'search',       'msg': 'Estamos evaluando los puntos de seguridad.'},
    'Piezas':      {'color': 'orange', 'icon': 'inventory_2',  'msg': 'Esperando refacciones de alta calidad.'},
    'Reparación':  {'color': 'indigo', 'icon': 'handyman',     'msg': 'Nuestros técnicos están trabajando en tu unidad.'},
    'Listo':       {'color': 'green',  'icon': 'check_circle', 'msg': '¡Tu vehículo está listo! Puedes pasar a recogerlo.'},
    'Entregado':   {'color': 'green',  'icon': 'done_all',     'msg': 'Servicio completado. ¡Gracias por tu confianza!'}
}

# Orden lógico del proceso
PASOS_ORDENADOS = ['Recibido', 'Diagnóstico', 'Piezas', 'Reparación', 'Listo']

def show_page(uuid_publico: str):
    
    # Contenedor principal centrado y con fondo suave
    # Usamos 'items-center' para que en PC se vea centrado tipo App móvil
    contenedor = ui.column().classes('w-full min-h-screen items-center bg-gray-100 p-0 gap-0')
    estado_previo = {'val': None}

    async def refrescar_interfaz():
        datos = db.obtener_info_publica_servicio(uuid_publico)
        
        # 1. Manejo de Error (Link inválido)
        if not datos:
            if estado_previo['val'] != 'error':
                contenedor.clear()
                with contenedor:
                    with ui.column().classes('h-screen justify-center items-center text-gray-400 p-4 text-center'):
                        ui.icon('broken_image', size='4em')
                        ui.label('No encontramos este servicio.').classes('text-lg font-bold')
                        ui.label('El enlace podría haber expirado.').classes('text-sm')
                estado_previo['val'] = 'error'
            return

        # 2. Normalización de Datos
        estatus_raw = datos.get('estatus_detalle', 'Recibido')
        # Limpieza simple por si vienen emojis antiguos en la DB
        estatus = next((k for k in CONFIG_ESTADOS if k in estatus_raw), 'Recibido')
        
        # Si no ha cambiado nada, no redibujamos (ahorra batería al cliente)
        if estatus == estado_previo['val']: return
        estado_previo['val'] = estatus

        # Configuración del estado actual
        cfg = CONFIG_ESTADOS.get(estatus, CONFIG_ESTADOS['Recibido'])
        indice_actual = PASOS_ORDENADOS.index(estatus) if estatus in PASOS_ORDENADOS else 0
        mecanico = datos.get('mecanico') or 'Equipo TREGAL'
        total_pagar = datos.get('costo_estimado', 0)

        # 3. REDIBUJADO DE LA INTERFAZ
        contenedor.clear()
        with contenedor:
            
            # --- A. HEADER DE MARCA ---
            with ui.row().classes('w-full bg-slate-900 p-4 justify-between items-center shadow-md'):
                ui.label('TREGAL TIRES').classes('text-lg font-black text-white tracking-widest')
                ui.icon('verified', color='green', size='sm')

            # --- B. TARJETA DE ESTADO (HERO) ---
            with ui.card().classes('w-full max-w-md -mt-2 rounded-none rounded-b-xl shadow-lg p-6 bg-white z-10'):
                # Icono animado del estado
                with ui.row().classes(f'w-full justify-center mb-2'):
                    with ui.element('div').classes(f'p-4 rounded-full bg-{cfg["color"]}-100'):
                        ui.icon(cfg['icon'], size='3em', color=cfg['color'])
                
                # Texto de Estado
                ui.label(estatus.upper()).classes(f'w-full text-center text-2xl font-black text-{cfg["color"]}-700 mb-1')
                ui.label(cfg['msg']).classes('w-full text-center text-gray-500 text-sm leading-tight')

                # Barra de Progreso
                if estatus != 'Entregado':
                    progreso = (indice_actual + 1) / len(PASOS_ORDENADOS)
                    ui.linear_progress(progreso).props(f'color={cfg["color"]}').classes('mt-6 rounded-full h-2')
                    ui.label(f'Paso {indice_actual + 1} de {len(PASOS_ORDENADOS)}').classes('w-full text-right text-xs text-gray-400 mt-1')

            # --- C. DETALLES DEL VEHÍCULO ---
            with ui.column().classes('w-full max-w-md p-4 gap-3'):
                ui.label('DETALLES DEL SERVICIO').classes('text-xs font-bold text-gray-400 ml-1 mt-4')
                
                with ui.card().classes('w-full p-4 shadow-sm border border-gray-200 flex-row gap-4 items-center'):
                    ui.icon('directions_car', size='2em', color='slate')
                    with ui.column().classes('gap-0'):
                        ui.label(datos['modelo']).classes('font-bold text-slate-800 text-lg leading-none')
                        ui.label(f"Placas: {datos['placas']} • {datos.get('color', 'S/C')}").classes('text-sm text-gray-500 uppercase mt-1')

                # Tarjeta del Mecánico (Toque Humano) 👨‍🔧
                with ui.card().classes('w-full p-4 shadow-sm border border-gray-200 flex-row gap-4 items-center'):
                    ui.avatar(icon='engineering', color='grey-2', text_color='slate-700')
                    with ui.column().classes('gap-0'):
                        ui.label('Técnico Asignado').classes('text-xs text-gray-400 uppercase font-bold')
                        ui.label(mecanico).classes('font-bold text-slate-700')

            # --- D. SECCIÓN DE PAGO (SOLO SI ESTÁ LISTO) 💰 ---
            if estatus in ['Listo', 'Entregado']:
                with ui.card().classes('w-full max-w-md mx-4 mb-4 bg-green-50 border border-green-200 p-4 items-center'):
                    ui.label('TOTAL A PAGAR').classes('text-xs font-bold text-green-700 tracking-widest')
                    ui.label(f"${total_pagar:,.2f}").classes('text-4xl font-black text-green-800 my-2')
                    if estatus == 'Listo':
                        ui.label('Puedes pasar a caja para retirar tu unidad.').classes('text-center text-xs text-green-600')

            # --- E. FOOTER CON ACCIONES ---
            with ui.column().classes('w-full max-w-md p-6 mt-auto gap-3'):
                # Botón WhatsApp
                telefono = db.get_whatsapp_taller()
                msg_wa = f"Hola, vi en el portal que mi {datos['modelo']} está en *{estatus}*. ¿Me podrían dar más detalles?"
                link_wa = f"https://wa.me/{telefono}?text={msg_wa}"
                
                ui.button('Contactar por WhatsApp', icon='whatsapp', on_click=lambda: ui.open(link_wa, new_tab=True)) \
                    .classes('w-full bg-green-600 text-white font-bold h-12 shadow-md rounded-lg')
                
                ui.label('TREGAL Tires & Services © 2025').classes('text-xs text-gray-300 text-center w-full mt-4')

    # Timer de actualización (Polling cada 5s)
    # Se ejecuta al inicio (0.1s) y luego cíclicamente
    ui.timer(0.1, refrescar_interfaz, once=True)
    ui.timer(5.0, refrescar_interfaz)