from nicegui import ui, app 
from Db import database as db
import pdf_generator
from datetime import datetime

def show():
    # --- CONTEXTO DE USUARIO ---
    rol_usuario = app.storage.user.get('rol', 'tecnico')
    user_worker_id = app.storage.user.get('trabajador_id')
    es_admin = (rol_usuario == 'admin')

    # --- FUNCIONES DE ACTUALIZACIÓN ---
    def actualizar_tablas():
        # --- TABLA COTIZACIONES ---
        if es_admin:
            # PASO 1: Convertimos a dict para poder editar (evita error de "read-only")
            raw_cots = db.obtener_cotizaciones()
            rows_cot = [dict(r) for r in raw_cots] 

            for r in rows_cot:
                # Ahora sí podemos agregar campos nuevos sin error
                r['costo_fmt'] = f"${r['costo_estimado']:,.2f}"
            
            tabla_cotizaciones.rows = rows_cot
            tabla_cotizaciones.update()
        
        # --- TABLA TALLER ACTIVO ---
        filtro = None if es_admin else user_worker_id
        
        # PASO 1: Convertimos a dict (Crucial para que no falle)
        raw_servicios = db.obtener_servicios_activos(filtro_trabajador_id=filtro)
        rows_ord = [dict(r) for r in raw_servicios]

        for r in rows_ord:
            # Formato de dinero seguro
            if es_admin:
                r['costo_fmt'] = f"${r['costo_estimado']:,.2f}"
            else:
                r['costo_fmt'] = "***"
            
            # Asegurar campos opcionales para evitar errores en el Frontend
            r['asignado_str'] = r.get('nombre_tecnico') or 'Sin Asignar'
            if 'estatus_detalle' not in r: r['estatus_detalle'] = 'Diagnóstico'
            # Convertimos fechas a string por si acaso vienen como objetos datetime
            if 'fecha' in r and not isinstance(r['fecha'], str):
                r['fecha'] = str(r['fecha'])

        tabla_servicios.rows = rows_ord
        tabla_servicios.update()
        
        # 2. Cargar Órdenes Activas
        filtro = None if es_admin else user_worker_id
        
        # Obtenemos los datos crudos
        raw_rows = db.obtener_servicios_activos(filtro_trabajador_id=filtro)
        
        # --- CORRECCIÓN 2: Convertir a lista de dicts puros para evitar errores de serialización ---
        rows_ord = [dict(row) for row in raw_rows] 

        for r in rows_ord:
            r['costo_fmt'] = f"${r['costo_estimado']:,.2f}" if es_admin else "***"
            r['asignado_str'] = r.get('nombre_tecnico') or 'Sin Asignar'
            # Asegurar que estatus_detalle exista, si no, poner un default
            if 'estatus_detalle' not in r: r['estatus_detalle'] = 'Diagnóstico'

        tabla_servicios.rows = rows_ord
        tabla_servicios.update()
        # 2. Cargar Órdenes Activas (Filtrado por permisos)
        filtro = None if es_admin else user_worker_id
        rows_ord = db.obtener_servicios_activos(filtro_trabajador_id=filtro)
        for r in rows_ord:
            r['costo_fmt'] = f"${r['costo_estimado']:,.2f}" if es_admin else "***"
            r['asignado_str'] = r.get('nombre_tecnico') or 'Sin Asignar'
        tabla_servicios.rows = rows_ord
        tabla_servicios.update()

    # --- ACCIONES DEL WORKFLOW ---
    
    def crear_nueva_entrada():
        if not select_auto.value or not descripcion.value:
            ui.notify('Faltan datos obligatorios', type='warning'); return
        
        tipo = tipo_entrada.value # 'Cotizacion' o 'Orden'
        # Seguridad: Técnico no puede crear Cotizaciones, forzamos Orden
        if not es_admin: tipo = 'Orden'

        c_ini = costo_inicial.value if es_admin else 0.0
        
        id_asignado = None
        if tipo == 'Orden':
            if es_admin and select_asignacion: id_asignado = select_asignacion.value 
            elif not es_admin: id_asignado = user_worker_id 

        db.crear_servicio(select_auto.value, descripcion.value, c_ini, id_asignado, tipo_doc=tipo)
        
        ui.notify(f'{tipo} creada exitosamente', type='positive')
        select_auto.value = None; descripcion.value = ''
        if es_admin: costo_inicial.value = 0
        actualizar_tablas()

    def aprobar_cotizacion(id_servicio):
        tech_id = user_worker_id if not es_admin else None
        db.convertir_cotizacion_a_orden(id_servicio, tecnico_id=tech_id)
        ui.notify('✅ Cotización Aprobada -> Pasó a Taller', type='positive')
        actualizar_tablas()
        if es_admin: tabs_control.value = 'tab_taller' # Auto-cambiar tab

    def cambiar_estatus_flujo(id_servicio, nuevo_estatus):
        # Esta función faltaba conectar en la versión anterior
        db.actualizar_estatus_servicio(id_servicio, nuevo_estatus)
        ui.notify(f'Estatus actualizado: {nuevo_estatus}', type='positive')
        actualizar_tablas()

    # --- DIALOGOS ---

    # 1. AGREGAR SERVICIO DE CATÁLOGO
    with ui.dialog() as dialog_servicio_cat, ui.card().classes('w-96'):
        ui.label('Agregar Servicio').classes('text-xl font-bold text-indigo-700')
        opciones_cat = db.obtener_servicios_para_select()
        sel_servicio = ui.select(options=opciones_cat, label='Servicio del Catálogo', with_input=True).classes('w-full')
        
        # Selección de técnico (Admin elige, Técnico se auto-asigna)
        sel_trab_com = ui.select(options=db.obtener_trabajadores_select(), label='Técnico Realiza').classes('w-full')
        if not es_admin: sel_trab_com.disable()

        num_costo = ui.number('Precio Venta').classes('w-full').props('prefix="$"').bind_visibility_from(sel_servicio, 'value')
        if not es_admin: num_costo.visible = False # Técnico no ve precios

        def al_seleccionar_servicio(e):
            if e.value and es_admin:
                cats = db.obtener_catalogo_servicios()
                for c in cats:
                    if c['id'] == e.value: num_costo.value = c['precio_base']; break
        sel_servicio.on_value_change(al_seleccionar_servicio)

        def guardar_servicio_orden():
            txt_servicio = "Servicio Manual"
            if sel_servicio.value:
                for cid, cname in opciones_cat.items():
                    if cid == sel_servicio.value: txt_servicio = cname.split(' - $')[0]; break
            
            # Si es técnico, el precio es 0 (se ajustará luego o queda oculto)
            costo_final = float(num_costo.value or 0) if es_admin else 0
            
            # Calculamos comisión básica (Módulo 2 placeholder)
            worker_data = db.obtener_trabajador_detalle(sel_trab_com.value)
            pct = worker_data['pct_mano_obra'] if worker_data else 0
            
            db.agregar_tarea_comision(dialog_servicio_cat.sid, sel_trab_com.value, txt_servicio, costo_final, pct)
            ui.notify('Servicio agregado', type='positive'); dialog_servicio_cat.close(); actualizar_tablas()

        ui.button('Agregar a la Orden', on_click=guardar_servicio_orden).classes('w-full bg-indigo-600 text-white')

    def abrir_agregar_servicio(sid):
        sel_servicio.value = None; num_costo.value = 0
        sel_trab_com.value = user_worker_id 
        dialog_servicio_cat.sid = sid
        dialog_servicio_cat.open()

    # 2. REFACCIONES
    with ui.dialog() as dialog_refaccion, ui.card():
        ui.label('Refacción de Inventario').classes('text-xl font-bold text-orange-700')
        sel_prod = ui.select(options=db.obtener_inventario_select(), label='Pieza', with_input=True).classes('w-full')
        num_cant = ui.number('Cantidad', value=1).classes('w-full')
        def guardar_refaccion():
            ok, msg = db.agregar_refaccion_a_servicio(dialog_refaccion.sid, sel_prod.value, int(num_cant.value))
            if ok: ui.notify(msg, type='positive'); dialog_refaccion.close(); actualizar_tablas()
            else: ui.notify(msg, type='negative')
        ui.button('Descontar de Inventario', on_click=guardar_refaccion).classes('w-full bg-orange-600 text-white')
    def abrir_refaccion(sid): dialog_refaccion.sid = sid; dialog_refaccion.open()

    # 3. COBRO (Solo Admin)
    with ui.dialog() as dialog_cierre, ui.card().classes('w-96'):
        ui.label('Cierre de Caja').classes('text-xl font-bold text-green-700')
        lbl_total_cobrar = ui.label('').classes('text-2xl font-black self-center my-2')
        sel_metodo = ui.select(['Efectivo', 'Tarjeta Débito', 'Tarjeta Crédito', 'Transferencia'], label='Método de Pago', value='Efectivo').classes('w-full')
        txt_ref = ui.input('Referencia / Voucher / Folio').classes('w-full')
        sel_cajero = ui.select(options=db.obtener_trabajadores_select(), label='Recibe el Pago').classes('w-full')
        
        def confirmar_cobro():
            db.cerrar_servicio(dialog_cierre.sid, f"T-{dialog_cierre.sid}", sel_cajero.value, dialog_cierre.monto, metodo_pago=sel_metodo.value, ref_pago=txt_ref.value)
            ui.notify('💰 Cobro registrado y Ticket generado', type='positive'); dialog_cierre.close(); actualizar_tablas()
        ui.button('Confirmar Pago', on_click=confirmar_cobro).classes('bg-green-700 text-white w-full')

    def abrir_cierre(row):
        if not es_admin: return # Seguridad extra
        sel_cajero.value = user_worker_id
        dialog_cierre.sid = row['id']
        dialog_cierre.monto = row['costo_estimado']
        lbl_total_cobrar.text = row['costo_fmt']
        dialog_cierre.open()

    # 4. PDF
    def generar_pdf_click(sid):
        d = db.obtener_datos_completos_pdf(sid)
        if d: ui.download(pdf_generator.generar_pdf_cotizacion(d, 15))

    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # Header
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('handyman', size='lg', color='primary')
                titulo = 'Gestión de Taller' if es_admin else 'Mis Asignaciones'
                ui.label(titulo).classes('text-2xl font-bold text-gray-800')

        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # --- PANEL IZQUIERDO: NUEVA ENTRADA ---
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-blue-500'):
                ui.label('📍 Nueva Entrada').classes('text-lg font-bold text-slate-700 mb-2')
                
                # Switch Tipo (Solo visible para Admin, Técnico solo ve Orden)
                tipo_entrada = ui.toggle(['Orden', 'Cotizacion'], value='Orden').props('spread no-caps active-class="bg-blue-700 text-white"').classes('w-full border rounded mb-4')
                if not es_admin: tipo_entrada.visible = False # Técnico siempre crea Orden

                # Auto
                with ui.row().classes('w-full items-center gap-2'):
                    opciones_autos = db.obtener_vehiculos_select_format()
                    select_auto = ui.select(options=opciones_autos, label='Vehículo', with_input=True).classes('flex-grow')
                    ui.button(icon='refresh', on_click=lambda: select_auto.set_options(db.obtener_vehiculos_select_format())).props('flat round dense')

                descripcion = ui.textarea('Falla / Solicitud').classes('w-full').props('rows=3')
                
                # Asignación (Solo Admin)
                select_asignacion = None
                if es_admin:
                    with ui.column().classes('w-full').bind_visibility_from(tipo_entrada, 'value', value='Orden'):
                        select_asignacion = ui.select(options=db.obtener_trabajadores_select(), label='Asignar Técnico').classes('w-full')
                        costo_inicial = ui.number('Costo Revisión', value=0).classes('w-full').props('prefix="$"')

                ui.button('Crear Registro', icon='save', on_click=crear_nueva_entrada).classes('w-full mt-4 bg-slate-800 text-white')

            # --- PANEL DERECHO: TABS ---
            with ui.card().classes('flex-grow w-0 p-0 shadow-lg overflow-hidden'):
                
                with ui.tabs().classes('w-full text-grey') as tabs_control:
                    tab_taller = ui.tab('tab_taller', label='🔧 En Proceso', icon='build').classes('text-blue-700')
                    # Pestaña Cotizaciones (SOLO ADMIN)
                    if es_admin:
                        tab_cots = ui.tab('tab_cots', label='📋 Cotizaciones', icon='request_quote').classes('text-orange-700')

                with ui.tab_panels(tabs_control, value='tab_taller').classes('w-full p-4'):
                    
                    # --- TAB 1: TALLER ACTIVO ---
                    with ui.tab_panel(tab_taller):
                        cols_taller = [
                            {'name': 'id', 'label': '#', 'field': 'id', 'align': 'center', 'classes': 'text-gray-400 font-bold'},
                            {'name': 'estatus', 'label': 'Estado', 'field': 'estatus_detalle', 'align': 'center', 'classes': 'font-bold text-blue-600'},
                            {'name': 'vehiculo', 'label': 'Auto', 'field': 'modelo', 'classes': 'font-bold'},
                            {'name': 'desc', 'label': 'Trabajo', 'field': 'descripcion', 'classes': 'italic text-xs text-wrap max-w-[200px]'},
                        ]
                        if es_admin:
                            cols_taller.append({'name': 'monto', 'label': 'Total', 'field': 'costo_fmt', 'align': 'right', 'classes': 'text-green-700 font-bold'})
                        cols_taller.append({'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'})

                        tabla_servicios = ui.table(columns=cols_taller, rows=[], row_key='id', pagination=10).classes('w-full')
                        
                        # SLOT DE ESTATUS (Dropdown para mover el flujo)
                        tabla_servicios.add_slot('body-cell-estatus', r'''
                            <q-td :props="props">
                                <q-btn-dropdown auto-close flat dense size="sm" :label="props.value" color="primary">
                                    <q-list>
                                        <q-item clickable @click="$parent.$emit('cambiar_status', {id: props.row.id, st: 'Diagnóstico'})"><q-item-section>🔍 Diagnóstico</q-item-section></q-item>
                                        <q-item clickable @click="$parent.$emit('cambiar_status', {id: props.row.id, st: 'Reparación'})"><q-item-section>🔧 Reparación</q-item-section></q-item>
                                        <q-item clickable @click="$parent.$emit('cambiar_status', {id: props.row.id, st: 'Piezas'})"><q-item-section>📦 Esperando Piezas</q-item-section></q-item>
                                        <q-item clickable @click="$parent.$emit('cambiar_status', {id: props.row.id, st: 'Listo'})"><q-item-section>✅ Listo p/Entrega</q-item-section></q-item>
                                    </q-list>
                                </q-btn-dropdown>
                                <q-btn flat round dense icon="link" size="xs" color="grey" @click="$parent.$emit('link', props.row.uuid_publico)"><q-tooltip>Link Cliente</q-tooltip></q-btn>
                            </q-td>
                        ''')
                        
                        # SLOT DE ACCIONES (BLINDADO)
                        # Creamos el string HTML dinámicamente según permisos
                        btn_cobrar = ''
                        if es_admin:
                            btn_cobrar = (
                                '<q-btn v-if="props.row.estatus_detalle == \'Listo\'" '
                                'icon="payments" size="sm" round color="green" '
                                '@click="$parent.$emit(\'cobrar\', props.row)">'
                                '<q-tooltip>Cobrar</q-tooltip></q-btn>'
                            )
                        
                        slot_acc = f'''
                            <q-td :props="props">
                                <div class="flex items-center gap-1 justify-center">
                                    <q-btn icon="picture_as_pdf" size="sm" flat round color="red" @click="$parent.$emit('pdf', props.row.id)" />
                                    <q-btn icon="post_add" size="sm" flat round color="indigo" @click="$parent.$emit('add_serv', props.row.id)"><q-tooltip>Mano Obra</q-tooltip></q-btn>
                                    <q-btn icon="inventory_2" size="sm" flat round color="orange" @click="$parent.$emit('add_ref', props.row.id)"><q-tooltip>Refacción</q-tooltip></q-btn>
                                    {btn_cobrar}
                                </div>
                            </q-td>
                        '''
                        tabla_servicios.add_slot('body-cell-acciones', slot_acc)
                        
                        # CONEXIONES DE EVENTOS
                        tabla_servicios.on('link', lambda e: (ui.clipboard.write(f"https://app.tregal.com.mx/status/{e.args}"), ui.notify('Link copiado')))
                        tabla_servicios.on('pdf', lambda e: generar_pdf_click(e.args))
                        tabla_servicios.on('add_serv', lambda e: abrir_agregar_servicio(e.args))
                        tabla_servicios.on('add_ref', lambda e: abrir_refaccion(e.args))
                        if es_admin: tabla_servicios.on('cobrar', lambda e: abrir_cierre(e.args))
                        
                        # --- LA PIEZA QUE FALTABA: CONECTAR EL CAMBIO DE ESTATUS ---
                        tabla_servicios.on('cambiar_status', lambda e: cambiar_estatus_flujo(e.args['id'], e.args['st']))

                    # --- TAB 2: COTIZACIONES (SOLO ADMIN) ---
                    if es_admin:
                        with ui.tab_panel(tab_cots):
                            cols_cot = [
                                {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'sortable': True},
                                {'name': 'modelo', 'label': 'Auto', 'field': 'modelo', 'classes': 'font-bold'},
                                {'name': 'dueno', 'label': 'Cliente', 'field': 'dueno_nombre'},
                                {'name': 'total', 'label': 'Estimado', 'field': 'costo_fmt', 'classes': 'text-orange-600 font-bold'},
                                {'name': 'acciones', 'label': 'Gestión', 'field': 'acciones', 'align': 'center'}
                            ]
                            tabla_cotizaciones = ui.table(columns=cols_cot, rows=[], row_key='id', pagination=10).classes('w-full')
                            
                            tabla_cotizaciones.add_slot('body-cell-acciones', r'''
                                <q-td :props="props">
                                    <q-btn label="Editar" icon="edit" size="sm" flat color="grey" @click="$parent.$emit('add_serv', props.row.id)" />
                                    <q-btn label="PDF" icon="picture_as_pdf" size="sm" flat color="red" @click="$parent.$emit('pdf', props.row.id)" />
                                    <q-btn label="Aprobar" icon="check_circle" size="sm" color="green" @click="$parent.$emit('aprobar', props.row.id)" />
                                </q-td>
                            ''')
                            
                            tabla_cotizaciones.on('add_serv', lambda e: abrir_agregar_servicio(e.args))
                            tabla_cotizaciones.on('pdf', lambda e: generar_pdf_click(e.args))
                            tabla_cotizaciones.on('aprobar', lambda e: aprobar_cotizacion(e.args))

    # Esto permite que la UI se "pinte" primero y luego carga los datos
    ui.timer(0.3, actualizar_tablas, once=True)