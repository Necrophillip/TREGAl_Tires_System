from nicegui import ui, app
from Db import database as db
from datetime import datetime

def show():
    # --- Contenedor Principal con fondo suave ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-slate-50'):
        
        # ==========================================
        # 1. ENCABEZADO (Bienvenida + Logout)
        # ==========================================
        with ui.row().classes('w-full justify-between items-center mb-2'):
            with ui.column().classes('gap-0'):
                # Intenta obtener el usuario, si no hay session usa "Usuario"
                user = app.storage.user.get('username', 'Admin')
                ui.label(f'Hola, {user} 👋').classes('text-2xl font-bold text-slate-800')
                ui.label(datetime.now().strftime('%A, %d de %B %Y')).classes('text-sm text-slate-500 capitalize')
            
            # Botón Logout Rápido
            ui.button('Cerrar Sesión', icon='logout', 
                      on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login'))) \
                      .props('outline color=grey-7 size=sm round')

        # ==========================================
        # 2. TARJETAS KPI (Indicadores Clave)
        # ==========================================
        resumen = db.obtener_resumen_mensual()
        
        with ui.row().classes('w-full gap-4 no-wrap'):
            # Tarjeta 1: Cobrado
            with ui.card().classes('w-1/4 p-3 shadow-sm border-l-4 border-green-500'):
                ui.label('Ingresos Mes').classes('text-xs font-bold text-gray-400 uppercase')
                ui.label(f"${resumen['cobrado_mes']:,.2f}").classes('text-xl font-bold text-slate-700')
                ui.icon('payments', color='green').classes('absolute top-2 right-2 text-xl opacity-20')

            # Tarjeta 2: Por Cobrar
            with ui.card().classes('w-1/4 p-3 shadow-sm border-l-4 border-orange-400'):
                ui.label('Por Cobrar').classes('text-xs font-bold text-gray-400 uppercase')
                ui.label(f"${resumen['pendiente_mes']:,.2f}").classes('text-xl font-bold text-slate-700')
                ui.icon('pending_actions', color='orange').classes('absolute top-2 right-2 text-xl opacity-20')

            # Tarjeta 3: Autos Activos
            with ui.card().classes('w-1/4 p-3 shadow-sm border-l-4 border-blue-500'):
                ui.label('En Taller').classes('text-xs font-bold text-gray-400 uppercase')
                ui.label(f"{resumen['autos_activos']} autos").classes('text-xl font-bold text-slate-700')
                ui.icon('garage', color='blue').classes('absolute top-2 right-2 text-xl opacity-20')

            # Tarjeta 4: Alertas Stock
            with ui.card().classes('w-1/4 p-3 shadow-sm border-l-4 border-red-500'):
                ui.label('Stock Bajo').classes('text-xs font-bold text-gray-400 uppercase')
                ui.label(f"{resumen['alertas_stock']} items").classes('text-xl font-bold text-slate-700')
                ui.icon('inventory_2', color='red').classes('absolute top-2 right-2 text-xl opacity-20')

        # ==========================================
        # 3. SECCIÓN DIVIDIDA (CRM vs Gráfico)
        # ==========================================
        with ui.row().classes('w-full gap-4 items-start'):
            
            # --- IZQUIERDA: ALERTA DE RETENCIÓN (Clientes Vencidos) ---
            # Ocupa 2/3 del espacio (w-2/3)
            with ui.card().classes('w-2/3 shadow-md'):
                with ui.row().classes('w-full justify-between items-center border-b pb-2 mb-2'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('notifications_active', color='orange').classes('text-lg')
                        ui.label('Recordatorios de Servicio').classes('text-md font-bold text-slate-700')
                    
                    # Filtramos clientes vencidos
                    todos_clientes = db.obtener_clientes()
                    vencidos = [c for c in todos_clientes if "Vencido" in c.get('status_alerta', '')]
                    
                    if vencidos:
                        ui.badge(f'{len(vencidos)}', color='red').props('floating')

                if not vencidos:
                    with ui.column().classes('w-full items-center justify-center py-6 text-gray-400'):
                        ui.icon('check_circle', size='3em', color='green')
                        ui.label('¡Excelente! Todos los clientes están al día.')
                else:
                    # Tabla Compacta
                    columns_crm = [
                        {'name': 'nombre', 'label': 'Cliente', 'field': 'nombre', 'align': 'left', 'classes': 'font-semibold text-sm'},
                        {'name': 'telefono', 'label': 'Teléfono', 'field': 'telefono', 'align': 'left', 'classes': 'text-sm'},
                        {'name': 'ultimo_servicio_fmt', 'label': 'Última Visita', 'field': 'ultimo_servicio_fmt', 'align': 'center', 'classes': 'text-sm'},
                        {'name': 'status_alerta', 'label': 'Estado', 'field': 'status_alerta', 'align': 'center', 'classes': 'text-red-600 font-bold text-xs bg-red-50 rounded px-1'},
                    ]
                    ui.table(columns=columns_crm, rows=vencidos, pagination=5).classes('w-full').props('dense flat')

            # --- DERECHA: GRÁFICO DONA (Optimizado) ---
            # Ocupa 1/3 del espacio (w-1/3)
            with ui.card().classes('w-1/3 shadow-md flex flex-col items-center p-4'):
                ui.label('Estado del Taller').classes('text-sm font-bold text-gray-500 w-full text-center mb-2')
                
                datos_grafico = db.obtener_conteo_estados_servicios()
                
                if not datos_grafico:
                    ui.label('Sin datos aún').classes('text-gray-400 py-10')
                else:
                    # Gráfico ECharts optimizado
                    ui.echart({
                        'tooltip': {'trigger': 'item'},
                        'legend': {'bottom': '0%', 'left': 'center', 'itemWidth': 10, 'itemHeight': 10},
                        'series': [
                            {
                                'name': 'Servicios',
                                'type': 'pie',
                                'radius': ['50%', '70%'], # <--- ESTO LO HACE DONA
                                'center': ['50%', '45%'],
                                'avoidLabelOverlap': False,
                                'itemStyle': {'borderRadius': 4, 'borderColor': '#fff', 'borderWidth': 2},
                                'label': {'show': False, 'position': 'center'},
                                'emphasis': {
                                    'label': {'show': True, 'fontSize': '16', 'fontWeight': 'bold'}
                                },
                                'data': datos_grafico
                            }
                        ]
                    }).classes('w-full h-48') # Altura fija pequeña