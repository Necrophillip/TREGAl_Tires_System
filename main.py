from nicegui import ui
from Db import database as db
# Importamos el nuevo dashboard
from Pages import dashboard, clientes, autos, servicios, inventario
from Pages import trabajadores # <--- Importar

db.init_db()

ui.query('.q-page').classes('bg-gray-100')

with ui.header().classes('bg-slate-900 text-white shadow-md'):
    with ui.row().classes('items-center gap-2'):
        ui.icon('build_circle', size='lg')
        ui.label('TALLER DASHBOARD v1.0').classes('text-xl font-bold tracking-wider')

with ui.tabs().classes('w-full bg-white text-slate-900 shadow-sm') as tabs:
    # 1. Ponemos el Dashboard PRIMERO
    tab_dashboard = ui.tab('Inicio', icon='dashboard')
    tab_servicios = ui.tab('Servicios', icon='handyman') # Servicios es lo 2do más importante
    tab_clientes = ui.tab('Clientes', icon='person')
    tab_autos = ui.tab('Vehículos', icon='directions_car')
    tab_inventario = ui.tab('Inventario', icon='inventory_2')
    tab_trabajadores = ui.tab('Equipo', icon='engineering')

# Hacemos que 'value' sea el dashboard para que inicie ahí
with ui.tab_panels(tabs, value=tab_dashboard).classes('w-full bg-transparent p-0'):
    
    # Panel del Dashboard
    with ui.tab_panel(tab_dashboard):
        dashboard.show()

    with ui.tab_panel(tab_servicios):
        servicios.show()
        
    with ui.tab_panel(tab_clientes):
        clientes.show()
    
    with ui.tab_panel(tab_autos):
        autos.show()

    with ui.tab_panel(tab_inventario):
        inventario.show()
        
    with ui.tab_panel(tab_trabajadores):
        trabajadores.show()    

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title='Gestor de Taller',
        native=True,
        window_size=(1280, 800),
        reload=True,
        language='es'
    )