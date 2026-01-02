from nicegui import ui, app, run
from Db import database as db
import pdf_generator
from services import email_service
from datetime import datetime
import base64 
import os

def show():
    # ==========================================
    # 1. CONTEXTO Y PERMISOS
    # ==========================================
    rol_usuario = app.storage.user.get('rol', 'tecnico')
    user_worker_id = app.storage.user.get('trabajador_id')
    es_admin = (rol_usuario == 'admin')
    
    # Variable de Estado
    filtro_estado = {'valor': 'Todos'} 
    
    # Diccionario para controlar los botones
    refs_botones = {}

    # --- NUEVO: Función para copiar link al portapapeles ---
    async def copiar_link_tracker(uuid_publico):
        if not uuid_publico:
            ui.notify('Este servicio no tiene enlace generado', type='warning')
            return
        
        # Usamos JS para copiar la URL completa del navegador
        js_code = f"navigator.clipboard.writeText(window.location.origin + '/status/{uuid_publico}')"
        await ui.run_javascript(js_code)
        ui.notify('🔗 Enlace copiado al portapapeles', type='positive')

    # ==========================================
    # 2. GESTIÓN DE TABLAS
    # ==========================================
    def actualizar_tablas():
        # --- A. COTIZACIONES ---
        if es_admin:
            raw_cots = db.obtener_cotizaciones()
            rows_cot = [dict(r) for r in raw_cots] 
            for r in rows_cot:
                r['costo_fmt'] = f"${r['costo_estimado']:,.2f}"
            tabla_cotizaciones.rows = rows_cot
            tabla_cotizaciones.update()
        
        # --- B. TALLER ACTIVO ---
        filtro_user = None if es_admin else user_worker_id
        raw_servicios = db.obtener_servicios_activos(filtro_trabajador_id=filtro_user)
        rows_ord = [dict(r) for r in raw_servicios]

        # Contadores
        conteo = {'Todos': 0, 'Diagnóstico': 0, 'Reparación': 0, 'Piezas': 0, 'Listo': 0}
        
        for r in rows_ord:
            # Formatos
            r['costo_fmt'] = f"${r['costo_estimado']:,.2f}" if es_admin else "***"
            r['asignado_str'] = r.get('nombre_tecnico') or 'Sin Asignar'
            st = r.get('estatus_detalle', 'Diagnóstico')
            r['estatus_detalle'] = st
            
            # Conteo
            conteo['Todos'] += 1
            if st in conteo: conteo[st] += 1

            # Semáforo de Tiempo 🚦
            try:
                fecha_str = str(r['fecha'])[:16] # Cortar segundos
                fecha_ingreso = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
                dias = (datetime.now() - fecha_ingreso).days
            except:
                dias = 0
            
            r['dias_taller'] = dias
            if dias < 3:
                r['clase_tiempo'] = 'text-green-600 font-bold'
                r['icon_tiempo'] = 'sentiment_satisfied'
            elif dias < 6:
                r['clase_tiempo'] = 'text-orange-500 font-bold'
                r['icon_tiempo'] = 'warning'
            else:
                r['clase_tiempo'] = 'text-red-600 font-black'
                r['icon_tiempo'] = 'local_fire_department'

        # Filtrado
        if filtro_estado['valor'] != 'Todos':
            rows_filtradas = [r for r in rows_ord if r['estatus_detalle'] == filtro_estado['valor']]
        else:
            rows_filtradas = rows_ord

        tabla_servicios.rows = rows_filtradas
        tabla_servicios.update()
        
        # Actualizar texto de botones con contadores
        if refs_botones:
            try:
                refs_botones['Todos'].text = f"Todos ({conteo['Todos']})"
                refs_botones['Diagnóstico'].text = f"Diagnóstico ({conteo['Diagnóstico']})"
                refs_botones['Reparación'].text = f"Reparación ({conteo['Reparación']})"
                refs_botones['Piezas'].text = f"Piezas ({conteo['Piezas']})"
                refs_botones['Listo'].text = f"Listos ({conteo['Listo']})"
                # Pequeño update para refrescar texto
                for btn in refs_botones.values(): btn.update()
            except: pass

    # ==========================================
    # 3. ACCIONES
    # ==========================================
    
    def cambiar_filtro(nuevo_filtro):
        filtro_estado['valor'] = nuevo_filtro
        
        # LÓGICA BLINDADA DE ESTILOS 🛡️
        for nombre, btn in refs_botones.items():
            if nombre == nuevo_filtro:
                # ACTIVO
                btn.props('unelevated no-caps rounded') 
                btn.classes('bg-slate-800 text-white', remove='text-slate-500 bg-transparent')
            else:
                # INACTIVO
                btn.props('flat no-caps rounded') 
                btn.classes('text-slate-500 bg-transparent', remove='bg-slate-800 text-white')
            
            btn.update() 
            
        actualizar_tablas()

    def crear_nueva_entrada():
        if not select_auto.value or not descripcion.value:
            ui.notify('Faltan datos obligatorios', type='warning'); return
        tipo = tipo_entrada.value if es_admin else 'Orden'
        c_ini = costo_inicial.value if es_admin else 0.0
        id_asignado = select_asignacion.value if (es_admin and select_asignacion) else user_worker_id 
        
        db.crear_servicio(select_auto.value, descripcion.value, c_ini, id_asignado, tipo_doc=tipo)
        ui.notify(f'{tipo} creada exitosamente', type='positive')
        select_auto.value = None; descripcion.value = ''
        if es_admin: costo_inicial.value = 0
        actualizar_tablas()

    def aprobar_cotizacion(sid):
        ok, msg = db.convertir_cotizacion_a_orden(sid, tecnico_id=(None if es_admin else user_worker_id))
        ui.notify(msg, type='positive' if ok else 'negative')
        if ok: actualizar_tablas()

    def cambiar_estatus_flujo(sid, st):
        db.actualizar_estatus_servicio(sid, st)
        ui.notify(f'Estatus: {st}', type='positive')
        actualizar_tablas()

    async def enviar_nota_por_correo(sid):
        info = db.obtener_email_cliente_por_servicio(sid)
        if not info or not info['email']: ui.notify('Cliente sin email', type='warning'); return
        
        datos = db.obtener_datos_completos_pdf(sid)
        if not datos: return
        ruta = pdf_generator.generar_pdf_cotizacion(datos, 0, titulo="NOTA DE SERVICIO")
        
        n = ui.notification('Enviando...', spinner=True)
        try:
            ok, msg = await run.io_bound(email_service.enviar_correo_con_pdf, 
                                       info['email'], f"Servicio #{sid}", 
                                       f"Hola {info['nombre']},\nAdjunto detalle.\nAtte TREGAL", ruta)
            n.dismiss()
            ui.notify(msg, type='positive' if ok else 'negative')
        except Exception as e:
            n.dismiss(); ui.notify(f"Error: {e}", type='negative')
        finally:
            if os.path.exists(ruta): os.remove(ruta)

    # ==========================================
    # 4. DIÁLOGOS
    # ==========================================
    
    # VISOR PDF
    with ui.dialog() as dialog_visor_pdf, ui.card().classes('w-[90vw] h-[90vh] p-0'):
        with ui.row().classes('w-full bg-slate-800 text-white p-2 justify-between items-center'):
            ui.label('Vista Previa').classes('ml-2 font-bold')
            ui.button(icon='close', on_click=dialog_visor_pdf.close).props('flat round dense text-color=white')
        
        visor_container = ui.html('', sanitize=False).classes('w-full h-full')

    def previsualizar_documento(sid, es_cotizacion=False):
        datos = db.obtener_datos_completos_pdf(sid)
        if not datos: return
        try:
            ruta = pdf_generator.generar_pdf_cotizacion(datos, 15, titulo=("COTIZACIÓN" if es_cotizacion else "NOTA"))
            with open(ruta, "rb") as f: b64 = base64.b64encode(f.read()).decode('utf-8')
            visor_container.content = f'<iframe src="data:application/pdf;base64,{b64}#toolbar=1" width="100%" height="100%" style="border:none;"></iframe>'
            dialog_visor_pdf.open()
        except Exception as e: ui.notify(f"Error PDF: {e}", type='negative')

    # MODALES GESTIÓN
    with ui.dialog() as d_serv, ui.card().classes('w-96'):
        ui.label('Agregar Servicio').classes('text-xl font-bold text-indigo-700')
        sel_s = ui.select(db.obtener_servicios_para_select(), label='Servicio', with_input=True).classes('w-full')
        sel_t = ui.select(db.obtener_trabajadores_select(), label='Técnico').classes('w-full')
        num_c = ui.number('Precio', prefix='$').classes('w-full').bind_visibility_from(sel_s, 'value')
        
        def add_s_click():
            txt = "Manual"; c = float(num_c.value or 0)
            if sel_s.value: 
                opts = db.obtener_servicios_para_select()
                if sel_s.value in opts: txt = opts[sel_s.value].split(' - $')[0]
            
            wd = db.obtener_trabajador_detalle(sel_t.value)
            pct = wd['pct_mano_obra'] if wd else 0
            db.agregar_tarea_comision(d_serv.sid, sel_t.value, txt, c, pct)
            ui.notify('Agregado', type='positive'); d_serv.close(); actualizar_tablas()
            
        ui.button('Agregar', on_click=add_s_click).classes('w-full bg-indigo-600 text-white')
        def on_s_change(e): 
            if e.value and es_admin: 
                cats = db.obtener_catalogo_servicios()
                for x in cats: 
                    if x['id']==e.value: num_c.value=x['precio_base']
        sel_s.on_value_change(on_s_change)

    def abrir_add_serv(sid):
        sel_s.set_options(db.obtener_servicios_para_select()); sel_s.value=None; num_c.value=0
        sel_t.value = user_worker_id; sel_t.disable() if not es_admin else sel_t.enable()
        if not es_admin: num_c.visible=False
        d_serv.sid=sid; d_serv.open()

    with ui.dialog() as d_ref, ui.card():
        ui.label('Refacción').classes('text-xl font-bold text-orange-700')
        sel_r = ui.select(db.obtener_inventario_select(), label='Pieza', with_input=True).classes('w-full')
        num_r = ui.number('Cant', value=1).classes('w-full')
        def add_r_click():
            ok, m = db.agregar_refaccion_a_servicio(d_ref.sid, sel_r.value, int(num_r.value))
            ui.notify(m, type='positive' if ok else 'negative'); d_ref.close(); actualizar_tablas()
        ui.button('Descontar', on_click=add_r_click).classes('w-full bg-orange-600 text-white')
    def abrir_add_ref(sid):
        sel_r.set_options(db.obtener_inventario_select()); sel_r.value=None; num_r.value=1
        d_ref.sid=sid; d_ref.open()

    with ui.dialog() as d_cobro, ui.card().classes('w-96'):
        ui.label('Cobrar').classes('text-xl font-bold text-green-700')
        lbl_tot = ui.label().classes('text-2xl font-black self-center my-2')
        sel_met = ui.select(['Efectivo', 'Tarjeta', 'Transferencia'], value='Efectivo', label='Método').classes('w-full')
        txt_ref = ui.input('Referencia').classes('w-full')
        sel_caj = ui.select(db.obtener_trabajadores_select(), label='Recibe').classes('w-full')
        def cobro_click():
            db.cerrar_servicio(d_cobro.sid, f"T-{d_cobro.sid}", sel_caj.value, d_cobro.monto, sel_met.value, txt_ref.value)
            ui.notify('Cobrado', type='positive'); d_cobro.close(); actualizar_tablas()
        ui.button('Confirmar', on_click=cobro_click).classes('w-full bg-green-700 text-white')
    def abrir_cobro(row):
        sel_caj.value = user_worker_id; d_cobro.sid=row['id']; d_cobro.monto=row['costo_estimado']
        lbl_tot.text=row['costo_fmt']; d_cobro.open()

    with ui.dialog() as d_edit, ui.card().classes('w-[600px]'):
        with ui.row().classes('w-full justify-between'):
            ui.label('Editar Ítems').classes('text-xl font-bold'); ui.button(icon='close', on_click=d_edit.close).props('flat dense')
        cont_items = ui.column().classes('w-full gap-2')
    def load_items(sid):
        d_edit.sid=sid; cont_items.clear(); items = db.obtener_items_editables(sid)
        with cont_items:
            if not items: ui.label('Vacío').classes('italic text-gray-400')
            for i in items:
                with ui.row().classes('w-full justify-between p-2 border rounded items-center'):
                    ui.label(f"{i['desc']} (x{i['cant']})").classes('font-bold')
                    ui.button(icon='delete', color='red', on_click=lambda e, x=i: del_item(x)).props('flat dense')
        d_edit.open()
    def del_item(i):
        ok, m = db.eliminar_item_orden(i['tipo'], i['id'], d_edit.sid)
        if ok: load_items(d_edit.sid); actualizar_tablas()
        else: ui.notify(m, type='negative')

    # ==========================================
    # 5. ESTRUCTURA VISUAL PRINCIPAL
    # ==========================================
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # --- FILTROS RÁPIDOS ---
        with ui.row().classes('w-full justify-start gap-2 bg-white p-2 rounded shadow-sm border border-gray-200'):
            ui.icon('filter_alt', color='gray').classes('self-center ml-2')
            ui.label('Filtros:').classes('self-center font-bold text-gray-500 mr-2')
            
            refs_botones['Todos'] = ui.button('Todos', on_click=lambda: cambiar_filtro('Todos')) \
                .props('unelevated no-caps rounded') \
                .classes('bg-slate-800 text-white')
            
            refs_botones['Diagnóstico'] = ui.button('Diagnóstico', on_click=lambda: cambiar_filtro('Diagnóstico')) \
                .props('flat no-caps rounded') \
                .classes('text-slate-500')
                
            refs_botones['Reparación'] = ui.button('Reparación', on_click=lambda: cambiar_filtro('Reparación')) \
                .props('flat no-caps rounded') \
                .classes('text-slate-500')
                
            refs_botones['Piezas'] = ui.button('Piezas', on_click=lambda: cambiar_filtro('Piezas')) \
                .props('flat no-caps rounded') \
                .classes('text-slate-500')
                
            refs_botones['Listo'] = ui.button('Listos', on_click=lambda: cambiar_filtro('Listo')) \
                .props('flat no-caps rounded') \
                .classes('text-slate-500')

        # Split View
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # PANEL IZQ: FORM
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-blue-500'):
                ui.label('📍 Nueva Entrada').classes('text-lg font-bold text-slate-700 mb-2')
                tipo_entrada = ui.toggle(['Orden', 'Cotizacion'], value='Orden').props('spread no-caps').classes('w-full border rounded mb-4')
                if not es_admin: tipo_entrada.visible = False 
                with ui.row().classes('w-full items-center gap-2'):
                    select_auto = ui.select(db.obtener_vehiculos_select_format(), label='Vehículo', with_input=True).classes('flex-grow')
                    ui.button(icon='refresh', on_click=lambda: select_auto.set_options(db.obtener_vehiculos_select_format())).props('flat round dense')
                descripcion = ui.textarea('Falla / Solicitud').classes('w-full').props('rows=3')
                select_asignacion = None
                if es_admin:
                    with ui.column().classes('w-full').bind_visibility_from(tipo_entrada, 'value', value='Orden'):
                        select_asignacion = ui.select(db.obtener_trabajadores_select(), label='Asignar Técnico').classes('w-full')
                        costo_inicial = ui.number('Costo Rev.', value=0, prefix='$').classes('w-full')
                ui.button('Crear Registro', icon='save', on_click=crear_nueva_entrada).classes('w-full mt-4 bg-slate-800 text-white')

            # PANEL DER: TABLA
            with ui.card().classes('flex-grow w-0 p-0 shadow-lg overflow-hidden'):
                with ui.tabs().classes('w-full text-grey') as tabs_control:
                    tab_taller = ui.tab('tab_taller', label='Taller Activo', icon='build').classes('text-blue-700')
                    if es_admin: tab_cots = ui.tab('tab_cots', label='Cotizaciones', icon='request_quote').classes('text-orange-700')

                with ui.tab_panels(tabs_control, value='tab_taller').classes('w-full p-0'):
                    
                    with ui.tab_panel(tab_taller).classes('p-0'):
                        cols = [
                            {'name': 'id', 'label': '#', 'field': 'id', 'align': 'center', 'classes': 'text-gray-400 font-bold'},
                            {'name': 'tiempo', 'label': 'Días', 'field': 'dias_taller', 'align': 'center', 'sortable': True},
                            {'name': 'estatus', 'label': 'Estado', 'field': 'estatus_detalle', 'align': 'center'},
                            {'name': 'vehiculo', 'label': 'Auto', 'field': 'modelo', 'classes': 'font-bold'},
                            {'name': 'desc', 'label': 'Trabajo', 'field': 'descripcion', 'classes': 'italic text-xs max-w-[200px] truncate'},
                        ]
                        if es_admin: cols.append({'name': 'monto', 'label': 'Total', 'field': 'costo_fmt', 'align': 'right', 'classes': 'text-green-700 font-bold'})
                        cols.append({'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'})

                        tabla_servicios = ui.table(columns=cols, rows=[], row_key='id', pagination=10).classes('w-full remove-padding')
                        
                        # SLOT TIEMPO
                        tabla_servicios.add_slot('body-cell-tiempo', r'''
                            <q-td :props="props">
                                <div class="flex items-center justify-center gap-1">
                                    <q-icon :name="props.row.icon_tiempo" size="xs" :class="props.row.clase_tiempo" />
                                    <span :class="props.row.clase_tiempo">{{ props.value }}d</span>
                                </div>
                            </q-td>
                        ''')
                        # SLOT ESTATUS
                        tabla_servicios.add_slot('body-cell-estatus', r'''
                            <q-td :props="props">
                                <q-btn-dropdown auto-close flat dense size="sm" :label="props.value" 
                                    :color="props.value == 'Listo' ? 'green' : (props.value == 'Piezas' ? 'orange' : 'primary')">
                                    <q-list>
                                        <q-item clickable @click="$parent.$emit('cambiar_status', {id: props.row.id, st: 'Diagnóstico'})"><q-item-section>🔍 Diagnóstico</q-item-section></q-item>
                                        <q-item clickable @click="$parent.$emit('cambiar_status', {id: props.row.id, st: 'Reparación'})"><q-item-section>🔧 Reparación</q-item-section></q-item>
                                        <q-item clickable @click="$parent.$emit('cambiar_status', {id: props.row.id, st: 'Piezas'})"><q-item-section>📦 Esperando Piezas</q-item-section></q-item>
                                        <q-item clickable @click="$parent.$emit('cambiar_status', {id: props.row.id, st: 'Listo'})"><q-item-section>✅ Listo p/Entrega</q-item-section></q-item>
                                    </q-list>
                                </q-btn-dropdown>
                            </q-td>
                        ''')
                        # SLOT ACCIONES (CON BOTÓN LINK AGREGADO 🔗)
                        btn_c = '<q-btn v-if="props.row.estatus_detalle==\'Listo\'" icon="payments" size="sm" round color="green" @click="$parent.$emit(\'cobrar\', props.row)"><q-tooltip>Cobrar</q-tooltip></q-btn>' if es_admin else ''
                        tabla_servicios.add_slot('body-cell-acciones', f'''
                            <q-td :props="props">
                                <div class="flex items-center gap-1 justify-center">
                                    <q-btn icon="edit_note" size="sm" flat round color="slate" @click="$parent.$emit('edit', props.row.id)"><q-tooltip>Editar</q-tooltip></q-btn>
                                    <q-btn icon="print" size="sm" flat round color="red" @click="$parent.$emit('pdf', props.row.id)"><q-tooltip>PDF</q-tooltip></q-btn>
                                    <q-btn icon="post_add" size="sm" flat round color="indigo" @click="$parent.$emit('serv', props.row.id)"><q-tooltip>+MO</q-tooltip></q-btn>
                                    <q-btn icon="inventory_2" size="sm" flat round color="orange" @click="$parent.$emit('ref', props.row.id)"><q-tooltip>+Ref</q-tooltip></q-btn>
                                    <q-btn icon="link" size="sm" flat round color="teal" @click="$parent.$emit('link', props.row.uuid_publico)"><q-tooltip>Copiar Link</q-tooltip></q-btn>
                                    <q-btn icon="email" size="sm" flat round color="blue" @click="$parent.$emit('email', props.row.id)"><q-tooltip>Enviar</q-tooltip></q-btn>
                                    {btn_c}
                                </div>
                            </q-td>
                        ''')
                        tabla_servicios.on('edit', lambda e: load_items(e.args))
                        tabla_servicios.on('pdf', lambda e: previsualizar_documento(e.args, False))
                        tabla_servicios.on('serv', lambda e: abrir_add_serv(e.args))
                        tabla_servicios.on('ref', lambda e: abrir_add_ref(e.args))
                        tabla_servicios.on('link', lambda e: copiar_link_tracker(e.args)) # <--- Handler del link
                        tabla_servicios.on('email', lambda e: enviar_nota_por_correo(e.args))
                        tabla_servicios.on('cambiar_status', lambda e: cambiar_estatus_flujo(e.args['id'], e.args['st']))
                        if es_admin: tabla_servicios.on('cobrar', lambda e: abrir_cobro(e.args))

                    if es_admin:
                        with ui.tab_panel(tab_cots):
                            cols_cot = [{'name': 'modelo', 'label': 'Auto', 'field': 'modelo'}, {'name': 'dueno', 'label': 'Cliente', 'field': 'dueno_nombre'}, {'name': 'total', 'label': 'Total', 'field': 'costo_fmt'}, {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones'}]
                            tabla_cotizaciones = ui.table(columns=cols_cot, rows=[], row_key='id').classes('w-full')
                            tabla_cotizaciones.add_slot('body-cell-acciones', r'''
                                <q-td :props="props">
                                    <q-btn icon="edit" size="sm" flat @click="$parent.$emit('serv', props.row.id)" />
                                    <q-btn icon="print" size="sm" flat color="red" @click="$parent.$emit('pdf', props.row.id)" />
                                    <q-btn icon="check_circle" size="sm" color="green" @click="$parent.$emit('ok', props.row.id)" />
                                </q-td>
                            ''')
                            tabla_cotizaciones.on('serv', lambda e: abrir_add_serv(e.args))
                            tabla_cotizaciones.on('pdf', lambda e: previsualizar_documento(e.args, True))
                            tabla_cotizaciones.on('ok', lambda e: aprobar_cotizacion(e.args))

    ui.timer(0.1, actualizar_tablas, once=True)
    ui.timer(5.0, actualizar_tablas)