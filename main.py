from nicegui import ui, app
from multiprocessing import freeze_support
from Db import database as db
import interfaz
from datetime import timedelta
from starlette.requests import Request 
import asyncio
from Pages import tracking_publico #

# --- CONFIGURACIÓN ---
TIEMPO_INACTIVIDAD = 30 

async def check_login():
    user = db.verificar_credenciales(username.value, password.value)
    
    if user:
        app.storage.user['authenticated'] = True
        app.storage.user['username'] = user['username']
        app.storage.user['rol'] = user['rol']
        app.storage.user['user_id'] = user['id']
        # Guardamos el ID del trabajador vinculado para filtrar tareas
        app.storage.user['trabajador_id'] = user['trabajador_id']
        
        app.storage.user.expires = timedelta(minutes=TIEMPO_INACTIVIDAD)
        
        ui.notify(f'Bienvenido {user["username"]} ({user["rol"]})', type='positive')
        await asyncio.sleep(0.5) 
        ui.navigate.to('/') 
    else:
        ui.notify('Usuario o contraseña incorrectos', color='negative')
        password.value = '' 

def logout():
    """Cierra sesión y redirige."""
    app.storage.user.clear()
    # Eliminamos client.disconnect() que causaba error
    ui.navigate.to('/login') 

@ui.page('/')
def home_page():
    
    if not app.storage.user.get('authenticated', False):
        return ui.navigate.to('/login?expired=true')

    # --- WATCHDOG DE SESIÓN ---
    def check_session_validity():
        if not app.storage.user.get('authenticated', False):
            session_watchdog.deactivate() 
            ui.navigate.to('/login?expired=true')
            return

    session_watchdog = ui.timer(2.0, check_session_validity, active=True) # Aumenté a 2s para menos carga
    
    # 2. CABECERA
    rol_actual = app.storage.user.get('rol', 'tecnico').upper()
    usuario_actual = app.storage.user.get('username', '').capitalize()
    
    with ui.header().classes('bg-slate-900 text-white shadow-md items-center'):
        ui.label('TREGAL Tires System').classes('text-xl font-bold tracking-wider')
        ui.space()
        with ui.row().classes('items-center gap-2 mr-4'):
            ui.icon('account_circle')
            ui.label(f"{usuario_actual} | {rol_actual}").classes('text-sm font-light')
            
        ui.button('Salir', icon='logout', on_click=logout).props('flat color=white dense')

    # 3. CARGAR INTERFAZ
    interfaz.crear_paginas()


@ui.page('/login')
def login_page(request: Request): 
    if app.storage.user.get('authenticated', False):
        return ui.navigate.to('/')

    if request.query_params.get('expired'):
        ui.notification('⚠️ Sesión expirada.', position='top', color='negative')

    with ui.card().classes('absolute-center w-96 shadow-lg p-8'):
        ui.label('🚗 TREGAL System').classes('text-h5 text-center w-full mb-6 font-bold text-slate-700')
        
        global username, password
        username = ui.input('Usuario').classes('w-full mb-2').props('autofocus')
        password = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full mb-6').on('keydown.enter', check_login)
        
        ui.button('Iniciar Sesión', on_click=check_login).classes('w-full bg-slate-800 text-white')
        
        ui.label('Acceso exclusivo para personal autorizado').classes('text-xs text-gray-400 text-center w-full mt-4')

# --- RUTA PÚBLICA (Tracking Cliente) --- 
# ¡OJO! Esta ruta NO lleva verificación de login

@ui.page('/status/{uuid_publico}')
def track_service(uuid_publico: str):
    tracking_publico.show_page(uuid_publico)
if __name__ in {"__main__", "__mp_main__"}:
    freeze_support()
    db.init_db()
    
    try:
        TIEMPO_INACTIVIDAD = db.get_tiempo_expiracion_minutos()
    except:
        TIEMPO_INACTIVIDAD = 30
        
    ui.run(
        title='TREGAL Tires System',
        host='0.0.0.0',
        port=8080,
        native=False,
        reload=False,
        storage_secret='clave_super_secreta_tregal_2025'
    )