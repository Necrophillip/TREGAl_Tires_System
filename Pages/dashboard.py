from nicegui import ui
from Db import database as db

def show():
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        with ui.row().classes('items-center gap-2 mb-4'):
            ui.label('Resumen Financiero (En Vivo)').classes('text-2xl font-bold text-gray-800')
            # Un spinner chiquito para que se vea que está "vivo"
            ui.spinner('dots', size='lg', color='green')

        # --- 1. DEFINIR VARIABLES DE UI (ELEMENTOS VACÍOS PRIMERO) ---
        
        # Tarjetas KPI
        lbl_ingreso_real = None
        lbl_pendiente = None
        lbl_autos = None
        lbl_alertas = None
        
        # Gráfica y Tabla
        chart_estado = None
        tabla_alertas = None

        # --- 2. ESTRUCTURA VISUAL ---
        
        with ui.row().classes('w-full gap-4 justify-between'):
            
            # Tarjeta 1: INGRESOS REALES
            with ui.card().classes('w-1/4 p-4 shadow-md border-l-8 border-green-600 items-center bg-white'):
                ui.label('Ingresos Reales (Caja)').classes('text-gray-500 font-medium')
                # Guardamos la referencia en la variable
                lbl_ingreso_real = ui.label('$ 0.00').classes('text-4xl font-bold text-green-700')
                ui.label('Ordenes cerradas este mes').classes('text-xs text-green-400')
                ui.icon('paid', size='md').classes('text-green-200 absolute top-2 right-2')

            # Tarjeta 2: POR COBRAR
            with ui.card().classes('w-1/4 p-4 shadow-md border-l-8 border-orange-400 items-center bg-white'):
                ui.label('Pendiente por Cobrar').classes('text-gray-500 font-medium')
                lbl_pendiente = ui.label('$ 0.00').classes('text-3xl font-bold text-orange-600')
                ui.label('Trabajos en curso').classes('text-xs text-orange-400')
                ui.icon('pending_actions', size='md').classes('text-orange-200 absolute top-2 right-2')

            # Tarjeta 3: Autos Activos
            with ui.card().classes('w-1/4 p-4 shadow-md border-l-8 border-blue-500 items-center'):
                ui.label('Autos en Patio').classes('text-gray-500 font-medium')
                lbl_autos = ui.label('0').classes('text-3xl font-bold text-blue-700')
                ui.icon('garage', size='md').classes('text-blue-200 absolute top-2 right-2')

        # --- GRAFICAS ---
        with ui.row().classes('w-full gap-6 mt-4'):
            
            with ui.card().classes('w-2/3 p-4 shadow-lg'):
                ui.label('Estado del Taller').classes('text-lg font-bold text-gray-700 mb-2')
                
                # Inicializamos la gráfica vacía
                chart_estado = ui.echart({
                    'tooltip': {'trigger': 'item'},
                    'legend': {'orient': 'vertical', 'left': 'left'},
                    'series': [
                        {
                            'name': 'Ordenes',
                            'type': 'pie',
                            'radius': '70%',
                            'data': [], # Vacío al inicio
                            'emphasis': {'itemStyle': {'shadowBlur': 10, 'shadowOffsetX': 0, 'shadowColor': 'rgba(0, 0, 0, 0.5)'}}
                        }
                    ]
                }).classes('h-64 w-full')

            # Mini tabla alertas
            with ui.card().classes('w-1/3 p-4 shadow-lg border-red-100 border'):
                ui.label('Alertas de Stock').classes('text-lg font-bold text-red-700')
                lbl_alertas = ui.label('').classes('text-sm italic mb-1')
                tabla_alertas = ui.table(
                    columns=[{'name': 'd', 'label': 'Producto', 'field': 'descripcion'}, {'name': 'c', 'label': 'Cant', 'field': 'cantidad'}],
                    rows=[]
                ).classes('w-full mt-2')

        # --- 3. LA FUNCIÓN MÁGICA DE REFRESH ---
        def refrescar_datos():
            # A. Obtener datos frescos de la DB
            metrics = db.obtener_resumen_mensual()
            data_grafica = db.obtener_conteo_estados_servicios()
            faltantes = db.obtener_productos_bajo_stock()

            # B. Actualizar Textos de Etiquetas
            lbl_ingreso_real.text = f"${metrics['cobrado_mes']:,.2f}"
            lbl_pendiente.text = f"${metrics['pendiente_mes']:,.2f}"
            lbl_autos.text = str(metrics['autos_activos'])
            
            # C. Actualizar Gráfica
            # ECharts requiere actualizar el diccionario 'options' y llamar update()
            chart_estado.options['series'][0]['data'] = data_grafica
            chart_estado.update()

            # D. Actualizar Tabla de Stock
            if not faltantes:
                tabla_alertas.visible = False
                lbl_alertas.text = "Stock Saludable 👍"
            else:
                tabla_alertas.visible = True
                lbl_alertas.text = "Urge reponer:"
                tabla_alertas.rows = faltantes
                tabla_alertas.update()

        # --- 4. ACTIVAR EL TIMER ---
        # Llamamos una vez al inicio para que no empiece vacío
        refrescar_datos()
        
        # Configuramos el timer para que corra cada 5 segundos
        ui.timer(5.0, refrescar_datos)