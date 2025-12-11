from nicegui import ui, app
from Db import database as db
# Importamos TODAS las páginas
from Pages import dashboard, clientes, autos, servicios, inventario, trabajadores, servicios_catalogo

def crear_paginas():
    
    # 1. Recuperamos el Rol
    rol_usuario = app.storage.user.get('rol', 'tecnico')
    es_admin = (rol_usuario == 'admin')

    # Estilo de fondo global
    ui.query('.q-page').classes('bg-gray-100')

    # 2. DEFINICIÓN DE TABS (MENÚ SUPERIOR)
    with ui.tabs().classes('w-full bg-slate-900 text-white shadow-md') as tabs:
        
        # --- ZONA OPERATIVA (Todos) ---
        tab_dashboard = ui.tab('Inicio', icon='dashboard')
        tab_servicios = ui.tab('Taller Activo', icon='handyman') # MES / Pizza Tracker
        
        # --- ZONA ADMINISTRATIVA (Solo Admin) ---
        if es_admin:
            # Gestión de Activos
            tab_autos = ui.tab('Vehículos', icon='directions_car')
            tab_clientes = ui.tab('Clientes', icon='person')
            
            # Gestión de Recursos
            tab_inventario = ui.tab('Refacciones', icon='inventory_2')
            tab_catalogo = ui.tab('Catálogo Servicios', icon='design_services') # <--- NUEVO RC3
            
            # Gestión Humana
            tab_trabajadores = ui.tab('RRHH / Nómina', icon='engineering')

    # 3. PANELES DE CONTENIDO
    with ui.tab_panels(tabs, value=tab_dashboard).classes('w-full h-full bg-transparent p-0'):
        
        # Paneles Comunes
        with ui.tab_panel(tab_dashboard): dashboard.show()
        with ui.tab_panel(tab_servicios): servicios.show()
        
        # Paneles de Admin (Solo se renderizan si es admin)
        if es_admin:
            with ui.tab_panel(tab_autos): autos.show()
            with ui.tab_panel(tab_clientes): clientes.show()
            
            with ui.tab_panel(tab_inventario): inventario.show()
            with ui.tab_panel(tab_catalogo): servicios_catalogo.show()
            
            with ui.tab_panel(tab_trabajadores): trabajadores.show()