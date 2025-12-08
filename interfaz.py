# Archivo: interfaz.py
from nicegui import ui
from Db import database as db
from Pages import dashboard, clientes, autos, servicios, inventario, trabajadores

def crear_paginas():
    # Definimos la página principal
    @ui.page('/')
    def inicio():
        ui.query('.q-page').classes('bg-gray-100')

        # Cabecera
        with ui.header().classes('bg-slate-900 text-white shadow-md'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('build_circle', size='lg')
                ui.label('TREGAL TIRES - SISTEMA v1.0').classes('text-xl font-bold tracking-wider')

        # Tabs
        with ui.tabs().classes('w-full bg-white text-slate-900 shadow-sm') as tabs:
            tab_dashboard = ui.tab('Inicio', icon='dashboard')
            tab_servicios = ui.tab('Servicios', icon='handyman')
            tab_clientes = ui.tab('Clientes', icon='person')
            tab_autos = ui.tab('Vehículos', icon='directions_car')
            tab_inventario = ui.tab('Inventario', icon='inventory_2')
            tab_trabajadores = ui.tab('Equipo', icon='engineering')

        # Paneles
        with ui.tab_panels(tabs, value=tab_dashboard).classes('w-full bg-transparent p-0'):
            with ui.tab_panel(tab_dashboard): dashboard.show()
            with ui.tab_panel(tab_servicios): servicios.show()
            with ui.tab_panel(tab_clientes): clientes.show()
            with ui.tab_panel(tab_autos): autos.show()
            with ui.tab_panel(tab_inventario): inventario.show()
            with ui.tab_panel(tab_trabajadores): trabajadores.show()