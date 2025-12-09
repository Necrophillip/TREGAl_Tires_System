from nicegui import ui, app, client # 'client' ya debe estar importado
from multiprocessing import freeze_support
from Db import database as db
import interfaz
from datetime import timedelta
from starlette.requests import Request 
import asyncio

# --- COSA 1: OBTENER TIEMPO DE EXPIRACIÓN ---
TIEMPO_INACTIVIDAD = 30 

# --- CONFIGURACIÓN DE ACCESO ---
USUARIO_SECRETO = "Tregal"
PASSWORD_SECRETO = "Tregal3105#"

async def check_login():
    # ... (Lógica de Login, se mantiene)
    if username.value == USUARIO_SECRETO and password.value == PASSWORD_SECRETO:
        app.storage.user['authenticated'] = True
        app.storage.user.expires = timedelta(minutes=TIEMPO_INACTIVIDAD)
        await asyncio.sleep(0.5) 
        ui.navigate.to('/') 
    else:
        ui.notify('Contraseña incorrecta', color='negative')

def logout():
    """Cierra sesión, desconecta el WebSocket y redirige."""
    app.storage.user.clear()
    client.disconnect() 
    ui.navigate.to('/login') 

@ui.page('/')
def home_page():
    
    # 1. VERIFICACIÓN CRÍTICA DE SEGURIDAD (PRIMER FILTRO)
    if not app.storage.user.get('authenticated', False):
        return ui.navigate.to('/login?expired=true')

    # --- WATCHDOG DE SESIÓN (FILTRO ACTIVO Y CONSTANTE) ---
    def check_session_validity():
        """Verifica la bandera de autenticación cada 0.5s."""
        if not app.storage.user.get('authenticated', False):
            # 1. Detener el temporizador inmediatamente (crucial para evitar bucles)
            session_watchdog.deactivate() 
            # 2. Forzar la desconexión del WebSocket y redirigir
            client.disconnect()
            ui.navigate.to('/login?expired=true')
            return

    # Creamos y activamos el temporizador global
    session_watchdog = ui.timer(0.5, check_session_validity, active=True)
    # ----------------------------------------------------
    
    # 2. BOTÓN DE SALIDA (Se mantiene)
    with ui.header().classes('bg-slate-900 text-white shadow-md'):
        ui.label('TREGAL Tires System').classes('text-xl font-bold tracking-wider')
        ui.space()
        ui.button('Salir', icon='logout', on_click=logout).props('flat color=white')

    # 3. CARGAR TU INTERFAZ (Tabs)
    interfaz.crear_paginas()

@ui.page('/login')
def login_page(request: Request): 
    # ... (Lógica de Login Page, se mantiene)
    # ...
    # Se mantiene igual que la última versión funcional
    # ...
    
    # LÓGICA DEL POPUP
    if request.query_params.get('expired'):
        ui.notification('⚠️ Sesión expirada. Debes iniciar sesión primero.', 
                        position='top', 
                        color='negative', 
                        timeout=5000).classes('shadow-lg border border-red-500') 

    # REDIRECCIÓN AL INICIO (Si la sesión sigue activa)
    if app.storage.user.get('authenticated', False):
        return ui.navigate.to('/')
        
    with ui.card().classes('absolute-center w-96 shadow-lg'):
        ui.label('🚗 TREGAL System').classes('text-h5 text-center w-full mb-4')
        
        global username, password
        username = ui.input('Usuario').classes('w-full')
        password = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full').on('keydown.enter', check_login)
        
        ui.button('Entrar', on_click=check_login).classes('w-full mt-4 bg-primary')


if __name__ in {"__main__", "__mp_main__"}:
    freeze_support()
    db.init_db()
    
    # Leemos el tiempo de expiración de la DB
    try:
        TIEMPO_INACTIVIDAD = db.get_tiempo_expiracion_minutos()
    except Exception:
        # Fallback si falla la DB
        TIEMPO_INACTIVIDAD = 30
        
    ui.run(
        title='TREGAL Tires System',
        host='0.0.0.0',
        port=80,
        native=False,
        reload=False,
        storage_secret='clave_super_secreta_tregal_2025'
    )