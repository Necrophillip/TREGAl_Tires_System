from nicegui import ui, app, run # <--- 1. AGREGAMOS 'run' AQUÍ
from Db import database as db
from datetime import datetime

def show():
    
    # Referencias UI
    chart_flujo = None
    chart_top = None
    chart_eq = None
    chart_prox = None
    refs = {} 

    # ==========================================
    # 1. LOGICA AUTOMÁTICA (Background)
    # ==========================================
    async def checar_recordatorios_fondo():
        try:
            if db.get_resend_api_key():
                # <--- 2. CORREGIDO: run.io_bound en vez de ui.run_io_bound
                n = await run.io_bound(db.procesar_recordatorios_automaticos)
                if n > 0:
                    ui.notify(f'🤖 Auto-Mailer: Se enviaron {n} recordatorios', type='positive')
        except Exception as e:
            print(f"Error automailer: {e}")

    # ==========================================
    # 2. MOTOR DE DATOS
    # ==========================================
    def refrescar_datos():
        # [A. KPIs]
        try:
            kpis = db.obtener_kpis_dashboard()
            refs['ventas'].text = f"${kpis.get('ventas', 0):,.2f}"
            refs['autos'].text = f"{kpis.get('autos', 0)}"
            refs['listos'].text = f"{kpis.get('listos', 0)}"
            refs['stock'].text = f"{kpis.get('alertas', 0)}"
            
            if kpis.get('alertas', 0) > 0:
                refs['icon_stock'].props('color=red')
                refs['card_stock'].classes('border-red-500 bg-red-50', remove='border-gray-200')
            else:
                refs['icon_stock'].props('color=grey-4')
                refs['card_stock'].classes('border-gray-200', remove='border-red-500 bg-red-50')
        except: pass

        # [B. META]
        try:
            met = db.obtener_metricas_ventas_mensuales()
            ticket = db.obtener_ticket_promedio_mensual()
            actual = met.get('actual', 0); ant = met.get('anterior', 0)
            meta = max(ant * 1.10, 20000.0)
            prog = min(actual / meta if meta > 0 else 0, 1.0)
            
            refs['meta_act'].text = f"${actual:,.2f}"
            refs['meta_obj'].text = f"/ ${meta:,.0f}"
            refs['ticket'].text = f"Ticket: ${ticket:,.0f}"
            refs['bar_meta'].style(f'width: {prog*100}%')
            
            c = 'bg-indigo-600'
            if prog >= 1: c = 'bg-emerald-500'
            elif prog < 0.4: c = 'bg-rose-500'
            refs['bar_meta'].classes(c, remove='bg-indigo-600 bg-emerald-500 bg-rose-500')
        except: pass

        # [C. GRÁFICOS]
        try:
            flujo = db.obtener_datos_grafico_semanal()
            if flujo and chart_flujo:
                chart_flujo.options['xAxis'][0]['data'] = [d['dia'] for d in flujo]
                chart_flujo.options['series'][0]['data'] = [d['ingresos'] for d in flujo]
                chart_flujo.options['series'][1]['data'] = [d['salidas'] for d in flujo]
                chart_flujo.update()
            
            top = db.obtener_top_servicios()
            if top and chart_top:
                chart_top.options['yAxis']['data'] = [x['name'] for x in top]
                chart_top.options['series'][0]['data'] = [x['value'] for x in top]
                chart_top.update()
            
            eq = db.obtener_carga_tecnicos()
            if eq and chart_eq:
                chart_eq.options['series'][0]['data'] = eq
                chart_eq.update()

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
    # 3. DIÁLOGOS Y GESTORES
    # ==========================================
    
    # --- Gestor de Marketing ---
    with ui.dialog() as d_marketing, ui.card().classes('w-[600px] h-auto p-6 rounded-xl'):
        with ui.row().classes('w-full justify-between items-center mb-4'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('campaign', color='indigo', size='md')
                ui.label('Gestor de Promociones').classes('text-xl font-bold')
            ui.button(icon='close', on_click=d_marketing.close).props('flat round dense')
        
        ui.label('Envía correos masivos a tu base de clientes.').classes('text-gray-400 text-sm mb-4')
        
        asunto_input = ui.input('Asunto del Correo').classes('w-full mb-2')
        mensaje_input = ui.textarea('Mensaje (Soporta HTML básico)').classes('w-full mb-4').props('rows=6')
        
        filtros = ui.select(['Todos los Clientes', 'Clientes Vencidos', 'Clientes Nuevos'], value='Todos los Clientes', label='Destinatarios').classes('w-full mb-4')
        
        async def enviar_campana():
            ui.notify('Iniciando envío...', type='info')
            clientes = db.obtener_clientes()
            
            target = []
            for c in clientes:
                if not c.get('email'): continue
                if filtros.value == 'Todos los Clientes': target.append(c)
                elif filtros.value == 'Clientes Vencidos' and 'Vencido' in c.get('status_alerta',''): target.append(c)
            
            if not target:
                ui.notify('No hay destinatarios con email válido', type='warning')
                return

            exitos = 0
            for c in target:
                body = mensaje_input.value.replace('{nombre}', c['nombre'])
                # <--- 3. CORREGIDO: run.io_bound aquí también
                ok, _ = await run.io_bound(db.enviar_email_resend, c['email'], asunto_input.value, body, c['id'], 'Promocion')
                if ok: exitos += 1
            
            ui.notify(f'Campaña finalizada: {exitos}/{len(target)} enviados', type='positive')
            d_marketing.close()

        ui.button('Enviar Campaña', on_click=enviar_campana).classes('w-full bg-indigo-600 text-white')

    # --- Configuración General ---
    with ui.dialog() as d_conf, ui.card().classes('w-96 rounded-xl'):
        ui.label('Configuración').classes('text-xl font-bold mb-4')
        
        with ui.tabs().classes('w-full') as tabs_conf:
            tc_gral = ui.tab('General')
            tc_mail = ui.tab('Correo / API')
        
        with ui.tab_panels(tabs_conf, value=tc_gral).classes('w-full'):
            with ui.tab_panel(tc_gral):
                t_iva = ui.number('IVA %', value=db.get_tasa_iva()).classes('w-full')
                t_wa = ui.input('WhatsApp', value=db.get_whatsapp_taller()).classes('w-full')
                t_mes = ui.number('Ciclo Servicio (Meses)', value=db.get_meses_alerta() or 6).classes('w-full')
            
            with ui.tab_panel(tc_mail):
                t_key = ui.input('Resend API Key', password=True, value=db.get_resend_api_key()).classes('w-full')
                t_from = ui.input('Remitente (Email)', value=db.get_email_remitente()).classes('w-full')
                ui.label('Nota: El remitente debe estar verificado en Resend.').classes('text-xs text-gray-400 mt-1')

        def guardar_config():
            db.set_tasa_iva(t_iva.value or 0)
            db.set_whatsapp_taller(t_wa.value)
            db.set_meses_alerta(int(t_mes.value or 6))
            db.set_resend_api_key(t_key.value)
            db.set_email_remitente(t_from.value)
            ui.notify('Configuración guardada')
            d_conf.close()
            ui.open('/')

        ui.button('Guardar Cambios', on_click=guardar_config).classes('w-full bg-slate-900 text-white mt-4')

    # ==========================================
    # 4. INTERFAZ PRINCIPAL
    # ==========================================
    with ui.column().classes('w-full min-h-screen bg-slate-50 p-6 gap-6'):
        
        # HEADER
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-0'):
                u = app.storage.user.get('username', 'Admin').capitalize()
                ui.label(f'Hola, {u}').classes('text-2xl font-black text-slate-800')
                ui.label('Panel de Control & Marketing').classes('text-xs font-bold text-gray-400 uppercase tracking-widest')
            
            with ui.row().classes('gap-2'):
                ui.button('Marketing', icon='campaign', on_click=d_marketing.open).props('flat color=indigo')
                ui.button(icon='settings', on_click=d_conf.open).props('flat round color=grey-7')
                ui.button(icon='logout', on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login'))).props('flat round color=grey-7')

        # KPIS
        with ui.row().classes('w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4'):
            def card_kpi(t, i, c, k):
                with ui.card().classes('p-4 shadow-sm border border-gray-200 rounded-xl flex-row items-center gap-4'):
                    with ui.element('div').classes(f'p-3 rounded-full bg-{c}-50'): ui.icon(i, color=c, size='md')
                    with ui.column().classes('gap-0'):
                        ui.label(t).classes('text-[10px] font-bold text-gray-400 uppercase')
                        refs[k] = ui.label('...').classes('text-xl font-black text-slate-700')
            card_kpi('Ventas', 'payments', 'green', 'ventas'); card_kpi('Taller', 'garage', 'indigo', 'autos')
            card_kpi('Entrega', 'key', 'amber', 'listos')
            with ui.card().classes('p-4 shadow-sm border border-gray-200 rounded-xl flex-row items-center gap-4') as cs:
                refs['card_stock'] = cs
                with ui.element('div').classes('p-3 rounded-full bg-gray-50'): refs['icon_stock'] = ui.icon('inventory_2', color='grey-4', size='md')
                with ui.column().classes('gap-0'):
                    ui.label('STOCK').classes('text-[10px] font-bold text-gray-400 uppercase')
                    refs['stock'] = ui.label('...').classes('text-xl font-black text-slate-700')

        # META
        with ui.card().classes('w-full p-5 shadow-sm border border-gray-200 rounded-xl'):
            with ui.row().classes('w-full justify-between items-end mb-2'):
                with ui.column().classes('gap-0'):
                    ui.label('OBJETIVO DE VENTAS').classes('text-[10px] font-bold text-gray-400 uppercase')
                    with ui.row().classes('items-baseline gap-1'):
                        refs['meta_act'] = ui.label('$0').classes('text-2xl font-black text-slate-800')
                        refs['meta_obj'] = ui.label('/ $0').classes('text-sm text-gray-400 font-medium')
                refs['ticket'] = ui.label('Ticket: $0').classes('text-xs font-mono bg-slate-100 px-2 py-1 rounded text-slate-500')
            with ui.element('div').classes('w-full h-3 bg-gray-100 rounded-full overflow-hidden'):
                refs['bar_meta'] = ui.element('div').classes('h-full bg-gray-300 w-0 transition-all duration-1000')

        # GRÁFICOS
        with ui.row().classes('w-full grid grid-cols-1 lg:grid-cols-3 gap-6'):
            # CRM
            with ui.card().classes('lg:col-span-2 p-6 shadow-md border border-gray-200 rounded-xl'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('event_upcoming', color='indigo').classes('text-xl')
                    ui.label('Proyección de Servicios').classes('text-lg font-bold text-slate-700')
                with ui.column().classes('w-full relative min-h-[350px]'):
                    refs['prox_msg'] = ui.label('Agenda Limpia').classes('absolute-center text-gray-400 hidden')
                    chart_prox = ui.echart({'tooltip':{'trigger':'axis'},'grid':{'left':'3%','right':'10%','bottom':'5%','containLabel':True},'xAxis':{'type':'value','splitLine':{'show':False}},'yAxis':{'type':'category','data':[],'inverse':True,'axisTick':{'show':False},'axisLine':{'show':False}},'series':[{'type':'bar','data':[],'barWidth':20,'itemStyle':{'borderRadius':[0,4,4,0]},'label':{'show':True,'position':'right','formatter':'{c}d'}}]}).classes('w-full h-[350px]')

            # TABS
            with ui.card().classes('p-0 shadow-md border border-gray-200 rounded-xl overflow-hidden'):
                with ui.tabs().classes('w-full bg-white text-gray-500 border-b') as tabs:
                    t1=ui.tab('Flujo'); t2=ui.tab('Top'); t3=ui.tab('Equipo')
                with ui.tab_panels(tabs, value=t1).classes('w-full'):
                    with ui.tab_panel(t1).classes('p-0'):
                        chart_flujo = ui.echart({'tooltip':{'trigger':'axis'},'legend':{'bottom':0},'grid':{'left':'5%','right':'5%','bottom':'15%','top':'10%','containLabel':True},'xAxis':[{'type':'category','data':[],'axisTick':{'alignWithLabel':True}}],'yAxis':[{'type':'value'}],'series':[{'name':'Ent','type':'bar','data':[],'itemStyle':{'color':'#6366f1'}},{'name':'Sal','type':'bar','data':[],'itemStyle':{'color':'#10b981'}}]}).classes('w-full h-[350px]')
                    with ui.tab_panel(t2).classes('p-0'):
                        chart_top = ui.echart({'tooltip':{'trigger':'axis'},'grid':{'left':'3%','right':'15%','bottom':'5%','containLabel':True},'xAxis':{'type':'value','show':False},'yAxis':{'type':'category','data':[],'inverse':True,'axisTick':{'show':False}},'series':[{'type':'bar','data':[],'itemStyle':{'color':'#8b5cf6','borderRadius':4},'label':{'show':True,'position':'right'}}]}).classes('w-full h-[350px]')
                    with ui.tab_panel(t3).classes('p-0'):
                        chart_eq = ui.echart({'tooltip':{'trigger':'item'},'legend':{'top':'5%','left':'center'},'series':[{'name':'Autos','type':'pie','radius':['40%','70%'],'center':['50%','55%'],'data':[],'itemStyle':{'borderRadius':5,'borderColor':'#fff','borderWidth':2}}]}).classes('w-full h-[350px]')

    # TIMERS
    ui.timer(0.1, refrescar_datos, once=True)
    ui.timer(5.0, refrescar_datos)
    ui.timer(3600.0, checar_recordatorios_fondo) 
    ui.timer(10.0, checar_recordatorios_fondo, once=True)