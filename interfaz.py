from nicegui import ui, app
from Db import database as db
from Pages import dashboard, clientes, autos, servicios, inventario, trabajadores

def crear_paginas():
    
    rol_usuario = app.storage.user.get('rol', 'tecnico')
    es_admin = (rol_usuario == 'admin')

    ui.query('.q-page').classes('bg-gray-100')

    with ui.tabs().classes('w-full bg-white text-slate-900 shadow-sm') as tabs:
        
        # 1. Tabs Comunes (Todos ven esto)
        tab_dashboard = ui.tab('Inicio', icon='dashboard')
        tab_servicios = ui.tab('Taller Activo', icon='handyman') # Tu MES
        
        # 2. Tabs EXCLUSIVOS DE ADMIN (Aquí ocultamos Vehículos e Inventario)
        if es_admin:
            tab_autos = ui.tab('Vehículos', icon='directions_car')
            tab_inventario = ui.tab('Refacciones', icon='inventory_2')
            tab_clientes = ui.tab('Clientes', icon='person')
            tab_trabajadores = ui.tab('RRHH / Nómina', icon='engineering')

    with ui.tab_panels(tabs, value=tab_dashboard).classes('w-full bg-transparent p-0'):
        
        with ui.tab_panel(tab_dashboard): dashboard.show()
        with ui.tab_panel(tab_servicios): servicios.show()
        
        # Solo renderizamos el contenido si es Admin
        if es_admin:
            with ui.tab_panel(tab_autos): autos.show()
            with ui.tab_panel(tab_inventario): inventario.show()
            with ui.tab_panel(tab_clientes): clientes.show()
            with ui.tab_panel(tab_trabajadores): trabajadores.show()