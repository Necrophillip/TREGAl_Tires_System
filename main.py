from nicegui import ui, app
from multiprocessing import freeze_support
from Db import database as db
import interfaz
from datetime import timedelta
from starlette.requests import Request 
import asyncio
from Pages import tracking_publico 
from Pages import reports_ui
import sys # <--- Asegúrate de importar sys

# ✅ SILENCIADOR v2.0: Se conecta al bucle REAL cuando la app arranca
async def silenciar_errores_windows():
    if sys.platform == 'win32':
        loop = asyncio.get_running_loop()
        def handler(loop, context):
            msg = context.get("exception", context.get("message"))
            # Filtramos el error 10054 y el ConnectionResetError
            if "WinError 10054" in str(msg) or "ConnectionResetError" in str(msg):
                return 
            # Si es otro error, usar el manejador por defecto
            loop.default_exception_handler(context)
        
        loop.set_exception_handler(handler)

# Conectamos la función al inicio de la app
app.on_startup(silenciar_errores_windows)

# ... ui.run(...)
# --- CONFIGURACIÓN ---
TIEMPO_INACTIVIDAD = 30 

# ... (El resto de tu código sigue igual hacia abajo) ...
async def check_login():
    user = db.verificar_credenciales(username.value, password.value)
    
    if user:
        app.storage.user['authenticated'] = True
        app.storage.user['username'] = user['username']
        app.storage.user['rol'] = user['rol']
        app.storage.user['id'] = user['id'] # Corregido para consistencia
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
    ui.navigate.to('/login') 

# --- COMPONENTE DE CABECERA (Header) ---
# Lo extraje a una función para poder reusarlo en el Home y en Reportes
def crear_header():
    rol_actual = app.storage.user.get('rol', 'tecnico').upper()
    usuario_actual = app.storage.user.get('username', '').capitalize()
    
    with ui.header().classes('bg-slate-900 text-white shadow-md items-center'):
        # Al hacer click en el título nos lleva al Home
        ui.label('TREGAL Tires System').classes('text-xl font-bold tracking-wider cursor-pointer').on('click', lambda: ui.navigate.to('/'))
        ui.space()
        
        with ui.row().classes('items-center gap-2 mr-4'):
            # ✅ NUEVO: Botón de Reportes (Solo Admin)
            if rol_actual == 'ADMIN':
                ui.button('Reportes', icon='bar_chart', on_click=lambda: ui.navigate.to('/admin/reportes')).props('flat color=white dense')
            
            ui.separator().props('vertical spaced color=grey-7')
            
            ui.icon('account_circle')
            ui.label(f"{usuario_actual} | {rol_actual}").classes('text-sm font-light')
            
        ui.button('Salir', icon='logout', on_click=logout).props('flat color=white dense')


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

    session_watchdog = ui.timer(2.0, check_session_validity, active=True)
    
    # 2. CABECERA (Usamos la función nueva)
    crear_header()

    # 3. CARGAR INTERFAZ PRINCIPAL
    interfaz.crear_paginas()


# ✅ NUEVO: RUTA DE REPORTES
@ui.page('/admin/reportes')
def reports_page():
    # 1. Seguridad: Verificar Login
    if not app.storage.user.get('authenticated', False):
        return ui.navigate.to('/login')
    
    # 2. Seguridad: Verificar Permisos (Solo Admin)
    if app.storage.user.get('rol') != 'admin':
        ui.notify('⛔ Acceso Denegado: Solo Administradores', type='negative')
        return ui.navigate.to('/')

    # 3. Header
    crear_header() # Reutilizamos el header para que tenga el botón de "Salir" y Navegación
    
    # 4. Cargar el Módulo de Reportes
    reports_ui.show_reports()


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