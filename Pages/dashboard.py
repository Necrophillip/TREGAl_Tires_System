from nicegui import ui, app
from Db import database as db
from datetime import datetime

def show():
    
    # Referencias para actualizar la UI
    chart_flujo = None
    chart_top = None
    chart_eq = None
    chart_prox = None
    refs = {} 

    # ==========================================
    # 1. MOTOR DE DATOS
    # ==========================================
    def refrescar_datos():
        # --- A. KPIs ---
        try:
            kpis = db.obtener_kpis_dashboard()
            refs['ventas'].text = f"${kpis.get('ventas', 0):,.2f}"
            refs['autos'].text = f"{kpis.get('autos', 0)}"
            refs['listos'].text = f"{kpis.get('listos', 0)}"
            refs['stock'].text = f"{kpis.get('alertas', 0)}"
            
            # Alerta Stock
            if kpis.get('alertas', 0) > 0:
                refs['icon_stock'].props('color=red')
                refs['card_stock'].classes('border-red-500 bg-red-50', remove='border-gray-200')
            else:
                refs['icon_stock'].props('color=grey-4')
                refs['card_stock'].classes('border-gray-200', remove='border-red-500 bg-red-50')
        except: pass

        # --- B. META (SEMÁFORO DE COLOR 🚦) ---
        try:
            met = db.obtener_metricas_ventas_mensuales()
            ticket = db.obtener_ticket_promedio_mensual()
            actual = met.get('actual', 0); ant = met.get('anterior', 0)
            meta = max(ant * 1.10, 20000.0)
            prog = min(actual / meta if meta > 0 else 0, 1.0)
            
            refs['meta_act'].text = f"${actual:,.2f}"
            refs['meta_obj'].text = f"/ ${meta:,.0f}"
            refs['ticket'].text = f"Ticket: ${ticket:,.0f}"
            
            # Animación de ancho
            refs['bar_meta'].style(f'width: {prog*100}%')
            
            # LÓGICA DE COLORES
            color_nuevo = 'bg-red-500' # Por defecto (Inicio)
            if prog >= 1.0:
                color_nuevo = 'bg-green-500' # Éxito total
            elif prog >= 0.75:
                color_nuevo = 'bg-blue-600'  # Ya casi
            elif prog >= 0.40:
                color_nuevo = 'bg-orange-400' # Avanzando
            
            # IMPORTANTE: Removemos cualquier color viejo para que aplique el nuevo
            refs['bar_meta'].classes(color_nuevo, remove='bg-red-500 bg-orange-400 bg-blue-600 bg-green-500 bg-indigo-600')
            
        except: pass

        # --- C. GRÁFICO FLUJO ---
        try:
            flujo = db.obtener_datos_grafico_semanal()
            if flujo and chart_flujo:
                chart_flujo.options['xAxis'][0]['data'] = [d['dia'] for d in flujo]
                chart_flujo.options['series'][0]['data'] = [d['ingresos'] for d in flujo]
                chart_flujo.options['series'][1]['data'] = [d['salidas'] for d in flujo]
                chart_flujo.update()
        except: pass

        # --- D. GRÁFICOS SECUNDARIOS ---
        try:
            # Top
            top = db.obtener_top_servicios()
            if top and chart_top:
                chart_top.options['yAxis']['data'] = [x['name'] for x in top]
                chart_top.options['series'][0]['data'] = [x['value'] for x in top]
                chart_top.update()
            
            # Equipo
            eq = db.obtener_carga_tecnicos()
            if eq and chart_eq:
                chart_eq.options['series'][0]['data'] = eq
                chart_eq.update()
        except: pass

        # --- E. CRM (PROYECCIÓN) ---
        try:
            all_c = db.obtener_clientes()
            proximos = []
            meses = db.get_meses_alerta() or 6
            limite = meses * 30
            hoy = datetime.now()
            
            for c in all_c:
                try:
                    if c.get('ultimo_servicio_fmt') != '-':
                        dt = datetime.strptime(c['ultimo_servicio'][:10], "%Y-%m-%d")
                        delta = (hoy - dt).days
                        if delta >= (limite - 45) and delta < limite:
                            c['dias_restantes'] = limite - delta
                            proximos.append(c)
                except: pass
            
            proximos.sort(key=lambda x: x['dias_restantes'])
            proximos = proximos[:10]
            
            if chart_prox:
                if proximos:
                    chart_prox.visible = True
                    refs['prox_msg'].visible = False
                    
                    noms = [x['nombre'] for x in proximos]
                    vals = [{'value': x['dias_restantes'], 'itemStyle': {'color': '#ef4444' if x['dias_restantes']<=7 else '#6366f1'}} for x in proximos]
                    
                    chart_prox.options['yAxis']['data'] = noms
                    chart_prox.options['series'][0]['data'] = vals
                    chart_prox.update()
                else:
                    chart_prox.visible = False
                    refs['prox_msg'].visible = True
        except: pass

    # ==========================================
    # 2. INTERFAZ
    # ==========================================
    with ui.column().classes('w-full min-h-screen bg-slate-50 p-6 gap-6'):
        
        # --- HEADER ---
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-0'):
                u = app.storage.user.get('username', 'Admin').capitalize()
                ui.label(f'Hola, {u}').classes('text-2xl font-black text-slate-800')
                ui.label('Resumen Ejecutivo').classes('text-xs font-bold text-gray-400 uppercase tracking-widest')
            
            ui.button(icon='logout', on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login'))) \
                .props('flat round color=grey-7')

        # --- KPIS ---
        with ui.row().classes('w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4'):
            
            def card_kpi(titulo, icon, color, key):
                with ui.card().classes('p-4 shadow-sm border border-gray-200 rounded-xl flex-row items-center gap-4'):
                    with ui.element('div').classes(f'p-3 rounded-full bg-{color}-50'):
                        ui.icon(icon, color=color, size='md')
                    with ui.column().classes('gap-0'):
                        ui.label(titulo).classes('text-[10px] font-bold text-gray-400 uppercase')
                        refs[key] = ui.label('...').classes('text-xl font-black text-slate-700')

            card_kpi('Ventas Mes', 'payments', 'green', 'ventas')
            card_kpi('En Taller', 'garage', 'indigo', 'autos')
            card_kpi('Por Entregar', 'key', 'amber', 'listos')
            
            # Stock Especial
            with ui.card().classes('p-4 shadow-sm border border-gray-200 rounded-xl flex-row items-center gap-4') as cs:
                refs['card_stock'] = cs
                with ui.element('div').classes('p-3 rounded-full bg-gray-50'):
                    refs['icon_stock'] = ui.icon('inventory_2', color='grey-4', size='md')
                with ui.column().classes('gap-0'):
                    ui.label('STOCK BAJO').classes('text-[10px] font-bold text-gray-400 uppercase')
                    refs['stock'] = ui.label('...').classes('text-xl font-black text-slate-700')

        # --- META ---
        with ui.card().classes('w-full p-5 shadow-sm border border-gray-200 rounded-xl'):
            with ui.row().classes('w-full justify-between items-end mb-2'):
                with ui.column().classes('gap-0'):
                    ui.label('OBJETIVO DE VENTAS').classes('text-[10px] font-bold text-gray-400 uppercase')
                    with ui.row().classes('items-baseline gap-1'):
                        refs['meta_act'] = ui.label('$0').classes('text-2xl font-black text-slate-800')
                        refs['meta_obj'] = ui.label('/ $0').classes('text-sm text-gray-400 font-medium')
                refs['ticket'] = ui.label('Ticket: $0').classes('text-xs font-mono bg-slate-100 px-2 py-1 rounded text-slate-500')
            
            with ui.element('div').classes('w-full h-3 bg-gray-100 rounded-full overflow-hidden'):
                # Iniciamos con un color base, pero la lógica lo cambiará al cargar
                refs['bar_meta'] = ui.element('div').classes('h-full bg-gray-300 w-0 transition-all duration-1000')

        # --- GRÁFICOS (GRID ESTABLE) ---
        with ui.row().classes('w-full grid grid-cols-1 lg:grid-cols-3 gap-6'):
            
            # 1. IZQUIERDA: CRM (2 COLUMNAS)
            with ui.card().classes('lg:col-span-2 p-6 shadow-md border border-gray-200 rounded-xl'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.label('Proyección de Servicios (30 Días)').classes('text-lg font-bold text-slate-700')
                
                # Contenedor relativo para mensaje "Vacío"
                with ui.column().classes('w-full relative min-h-[350px]'):
                    refs['prox_msg'] = ui.label('Sin servicios próximos').classes('absolute-center text-gray-400 hidden')
                    
                    # ALTURA FIJA PARA EVITAR COLAPSO
                    chart_prox = ui.echart({
                        'tooltip': {'trigger': 'axis'},
                        'grid': {'left': '3%', 'right': '10%', 'bottom': '5%', 'containLabel': True},
                        'xAxis': {'type': 'value', 'splitLine': {'show': False}},
                        'yAxis': {'type': 'category', 'data': [], 'inverse': True, 'axisTick': {'show': False}, 'axisLine': {'show': False}},
                        'series': [{'type': 'bar', 'data': [], 'barWidth': 20, 'itemStyle': {'borderRadius': [0,4,4,0]}, 'label': {'show': True, 'position': 'right', 'formatter': '{c}d'}}]
                    }).classes('w-full h-[350px]') 

            # 2. DERECHA: TABS (1 COLUMNA)
            with ui.card().classes('p-0 shadow-md border border-gray-200 rounded-xl overflow-hidden'):
                with ui.tabs().classes('w-full bg-white text-gray-500 border-b') as tabs:
                    t1 = ui.tab('Flujo')
                    t2 = ui.tab('Top')
                    t3 = ui.tab('Equipo')
                
                with ui.tab_panels(tabs, value=t1).classes('w-full'):
                    
                    # Panel Flujo
                    with ui.tab_panel(t1).classes('p-0'):
                        chart_flujo = ui.echart({
                            'tooltip': {'trigger': 'axis'},
                            'legend': {'bottom': 0},
                            'grid': {'left': '5%', 'right': '5%', 'bottom': '15%', 'top': '10%', 'containLabel': True},
                            'xAxis': [{'type': 'category', 'data': [], 'axisTick': {'alignWithLabel': True}}],
                            'yAxis': [{'type': 'value'}],
                            'series': [
                                {'name': 'Ent', 'type': 'bar', 'data': [], 'itemStyle': {'color': '#6366f1'}},
                                {'name': 'Sal', 'type': 'bar', 'data': [], 'itemStyle': {'color': '#10b981'}}
                            ]
                        }).classes('w-full h-[350px]') # ALTURA FIJA

                    # Panel Top
                    with ui.tab_panel(t2).classes('p-0'):
                        chart_top = ui.echart({
                            'tooltip': {'trigger': 'axis'},
                            'grid': {'left': '3%', 'right': '15%', 'bottom': '5%', 'containLabel': True},
                            'xAxis': {'type': 'value', 'show': False},
                            'yAxis': {'type': 'category', 'data': [], 'inverse': True, 'axisTick': {'show': False}},
                            'series': [{'type': 'bar', 'data': [], 'itemStyle': {'color': '#8b5cf6', 'borderRadius': 4}, 'label': {'show': True, 'position': 'right'}}]
                        }).classes('w-full h-[350px]') # ALTURA FIJA

                    # Panel Equipo
                    with ui.tab_panel(t3).classes('p-0'):
                        chart_eq = ui.echart({
                            'tooltip': {'trigger': 'item'},
                            'legend': {'top': '5%', 'left': 'center'},
                            'series': [{'name': 'Autos', 'type': 'pie', 'radius': ['40%', '70%'], 'center': ['50%', '55%'], 'data': [], 'itemStyle': {'borderRadius': 5, 'borderColor': '#fff', 'borderWidth': 2}}]
                        }).classes('w-full h-[350px]') # ALTURA FIJA

    # Iniciar
    ui.timer(0.1, refrescar_datos, once=True)
    ui.timer(5.0, refrescar_datos)