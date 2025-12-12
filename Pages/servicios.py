from nicegui import ui, app 
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

    # ==========================================
    # 2. GESTIÓN DE TABLAS (REFRESCO DE DATOS)
    # ==========================================
    def actualizar_tablas():
        # --- A. TABLA COTIZACIONES (Solo Admin) ---
        if es_admin:
            # Convertimos a dict para poder manipular los datos
            raw_cots = db.obtener_cotizaciones()
            rows_cot = [dict(r) for r in raw_cots] 

            for r in rows_cot:
                # Formateamos moneda
                r['costo_fmt'] = f"${r['costo_estimado']:,.2f}"
            
            # Asignamos a la tabla
            tabla_cotizaciones.rows = rows_cot
            tabla_cotizaciones.update()
        
        # --- B. TABLA TALLER ACTIVO (Todos) ---
        # Si es técnico, solo ve sus asignaciones. Admin ve todo.
        filtro = None if es_admin else user_worker_id
        
        raw_servicios = db.obtener_servicios_activos(filtro_trabajador_id=filtro)
        rows_ord = [dict(r) for r in raw_servicios]

        for r in rows_ord:
            # Formato de dinero (oculto para técnicos)
            if es_admin:
                r['costo_fmt'] = f"${r['costo_estimado']:,.2f}"
            else:
                r['costo_fmt'] = "***"
            
            # Sanitización de datos para la UI
            r['asignado_str'] = r.get('nombre_tecnico') or 'Sin Asignar'
            if 'estatus_detalle' not in r: r['estatus_detalle'] = 'Diagnóstico'
            
            # Convertir fechas a string seguro
            if 'fecha' in r and not isinstance(r['fecha'], str):
                r['fecha'] = str(r['fecha'])

        tabla_servicios.rows = rows_ord
        tabla_servicios.update()

    # ==========================================
    # 3. LÓGICA DEL WORKFLOW (ACCIONES)
    # ==========================================
    
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
        # Limpieza de formulario
        select_auto.value = None; descripcion.value = ''
        if es_admin: costo_inicial.value = 0
        actualizar_tablas()

    # RC4 

    def aprobar_cotizacion(id_servicio):
        tech_id = user_worker_id if not es_admin else None
        
        # CAMBIO: Ahora capturamos el resultado (ok, msg)
        ok, msg = db.convertir_cotizacion_a_orden(id_servicio, tecnico_id=tech_id)
        
        if ok:
            ui.notify(f'✅ {msg}', type='positive')
            actualizar_tablas()
            if es_admin: tabs_control.value = 'tab_taller' # Auto-cambiar tab
        else:
            ui.notify(f'❌ Error al aprobar: {msg}', type='negative')

    def cambiar_estatus_flujo(id_servicio, nuevo_estatus):
        db.actualizar_estatus_servicio(id_servicio, nuevo_estatus)
        ui.notify(f'Estatus actualizado: {nuevo_estatus}', type='positive')
        actualizar_tablas()

# --- RC5 FUNCIÓN DE ENVÍO ---
    def enviar_nota_por_correo(sid):
        # 1. Obtener datos del cliente
        info_cliente = db.obtener_email_cliente_por_servicio(sid)
        if not info_cliente or not info_cliente['email']:
            ui.notify('Este cliente no tiene correo registrado 😟', type='warning')
            return

        # 2. Generar el PDF fresco (Nota de Mostrador)
        datos = db.obtener_datos_completos_pdf(sid)
        if not datos: return
        
        # Generamos PDF temporal
        ruta_pdf = pdf_generator.generar_pdf_cotizacion(datos, 0, titulo="NOTA DE SERVICIO")
        
        # 3. Notificación de "Enviando..." (UI UX)
        n = ui.notification('Enviando correo...', spinner=True, timeout=None)
        
        # 4. Enviar (En un timer para no congelar la UI)
        def proceso_envio():
            cuerpo = f"""Hola {info_cliente['nombre']},
            
Adjunto encontrarás el detalle de tu servicio en TREGAL Tires.
Gracias por tu preferencia.
            
Atte. El Equipo TREGAL."""
            
            ok, msg = email_service.enviar_correo_con_pdf(
                info_cliente['email'], 
                f"Tu Servicio #{sid} - TREGAL Tires", 
                cuerpo, 
                ruta_pdf
            )
            
            n.dismiss() # Quitar spinner
            if ok:
                ui.notify(f'📨 {msg} a {info_cliente["email"]}', type='positive')
            else:
                ui.notify(f'❌ {msg}', type='negative')
            
            # Limpieza (borrar PDF temporal)
            if os.path.exists(ruta_pdf): os.remove(ruta_pdf)

        ui.timer(0.1, proceso_envio, once=True)
    # ==========================================
    # 4. DIÁLOGOS Y MODALES
    # ==========================================

    # --- A. VISOR DE PDF (NUEVO FEATURE) ---
    with ui.dialog() as dialog_visor_pdf, ui.card().classes('w-[90vw] h-[90vh] p-0'):
        with ui.row().classes('w-full bg-slate-800 text-white p-2 items-center justify-between'):
            ui.label('Vista Previa de Documento').classes('text-lg font-bold ml-2')
            ui.button(icon='close', on_click=dialog_visor_pdf.close).props('flat round dense text-color=white')
        
        # Contenedor para el Iframe
        visor_container = ui.html('', sanitize=False).classes('w-full h-full')

    def previsualizar_documento(sid, es_cotizacion=False):
        """Genera el PDF, lo convierte a Base64 y lo muestra en el visor"""
        datos = db.obtener_datos_completos_pdf(sid)
        if not datos:
            ui.notify("No se encontraron datos para este servicio", type='negative')
            return

        # LÓGICA DE TÍTULO DINÁMICO
        titulo_doc = "COTIZACIÓN" if es_cotizacion else "NOTA DE MOSTRADOR"
        
        try:
            # Generamos el archivo PDF (Pasamos el título dinámico)
            ruta_pdf = pdf_generator.generar_pdf_cotizacion(datos, 15, titulo=titulo_doc)
            
            # Leemos el archivo generado para convertirlo a Base64
            with open(ruta_pdf, "rb") as pdf_file:
                base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
            
            # Creamos el iframe (#toolbar=1 activa el menú de impresión del navegador)
            src = f"data:application/pdf;base64,{base64_pdf}#toolbar=1"
            content = f'<iframe src="{src}" width="100%" height="100%" style="border:none;"></iframe>'
            
            visor_container.content = content
            dialog_visor_pdf.open()
            
        except Exception as e:
            ui.notify(f"Error generando PDF: {str(e)}", type='negative')

    # --- B. AGREGAR SERVICIO ---
    with ui.dialog() as dialog_servicio_cat, ui.card().classes('w-96'):
        ui.label('Agregar Servicio').classes('text-xl font-bold text-indigo-700')
        opciones_cat = db.obtener_servicios_para_select()
        sel_servicio = ui.select(options=opciones_cat, label='Servicio del Catálogo', with_input=True).classes('w-full')
        
        sel_trab_com = ui.select(options=db.obtener_trabajadores_select(), label='Técnico Realiza').classes('w-full')
        if not es_admin: sel_trab_com.disable()

        num_costo = ui.number('Precio Venta').classes('w-full').props('prefix="$"').bind_visibility_from(sel_servicio, 'value')
        if not es_admin: num_costo.visible = False 

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
            
            costo_final = float(num_costo.value or 0) if es_admin else 0
            
            # Calculamos comisión básica
            worker_data = db.obtener_trabajador_detalle(sel_trab_com.value)
            pct = worker_data['pct_mano_obra'] if worker_data else 0
            
            db.agregar_tarea_comision(dialog_servicio_cat.sid, sel_trab_com.value, txt_servicio, costo_final, pct)
            ui.notify('Servicio agregado', type='positive'); dialog_servicio_cat.close(); actualizar_tablas()

        ui.button('Agregar a la Orden', on_click=guardar_servicio_orden).classes('w-full bg-indigo-600 text-white')

    def abrir_agregar_servicio(sid):
        # 1. Recargar opciones del catálogo (por si cambiaste precios)
        sel_servicio.options = db.obtener_servicios_para_select()
        sel_servicio.update()
        
        # 2. Resetear
        sel_servicio.value = None
        num_costo.value = 0
        sel_trab_com.value = user_worker_id 
        
        # 3. Abrir
        dialog_servicio_cat.sid = sid
        dialog_servicio_cat.open()

    # --- C. AGREGAR REFACCIÓN ---
    with ui.dialog() as dialog_refaccion, ui.card():
        ui.label('Refacción de Inventario').classes('text-xl font-bold text-orange-700')
        sel_prod = ui.select(options=db.obtener_inventario_select(), label='Pieza', with_input=True).classes('w-full')
        num_cant = ui.number('Cantidad', value=1).classes('w-full')
        def guardar_refaccion():
            ok, msg = db.agregar_refaccion_a_servicio(dialog_refaccion.sid, sel_prod.value, int(num_cant.value))
            if ok: ui.notify(msg, type='positive'); dialog_refaccion.close(); actualizar_tablas()
            else: ui.notify(msg, type='negative')
        ui.button('Descontar de Inventario', on_click=guardar_refaccion).classes('w-full bg-orange-600 text-white')
    def abrir_refaccion(sid):
        # 1. Forzamos la recarga de opciones desde la DB
        sel_prod.options = db.obtener_inventario_select()
        sel_prod.update()
        
        # 2. Reseteamos valores
        sel_prod.value = None
        num_cant.value = 1
        
        # 3. Abrimos
        dialog_refaccion.sid = sid
        dialog_refaccion.open()

    # --- D. CIERRE DE CAJA (COBRO) ---
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
        if not es_admin: return 
        sel_cajero.value = user_worker_id
        dialog_cierre.sid = row['id']
        dialog_cierre.monto = row['costo_estimado']
        lbl_total_cobrar.text = row['costo_fmt']
        dialog_cierre.open()

    # --- E. EDITOR DE ÍTEMS (NUEVO) ---
    with ui.dialog() as dialog_editor, ui.card().classes('w-[600px]'):
        with ui.row().classes('w-full items-center justify-between'):
            ui.label('✏️ Editar Contenido de la Orden').classes('text-xl font-bold text-slate-700')
            ui.button(icon='close', on_click=dialog_editor.close).props('flat round dense')
        
        # Contenedor donde pintaremos la lista dinámica
        lista_items_container = ui.column().classes('w-full gap-2')

    def cargar_editor_items(sid):
        dialog_editor.sid = sid # Guardamos ID en el dialogo
        lista_items_container.clear() # Limpiamos lista anterior
        
        items = db.obtener_items_editables(sid)
        
        with lista_items_container:
            if not items:
                ui.label('La orden está vacía').classes('italic text-gray-400 self-center')
            
            for item in items:
                with ui.row().classes('w-full items-center justify-between p-2 bg-gray-50 rounded border hover:bg-gray-100'):
                    # Icono según tipo
                    icono = 'engineering' if item['tipo'] == 'MO' else 'inventory_2'
                    color_icon = 'indigo' if item['tipo'] == 'MO' else 'orange'
                    
                    with ui.row().classes('items-center gap-3'):
                        ui.icon(icono, color=color_icon).classes('text-xl')
                        with ui.column().classes('gap-0'):
                            ui.label(item['desc']).classes('font-bold leading-tight')
                            ui.label(f"Cant: {item['cant']} | Total: ${item['total']:,.2f}").classes('text-xs text-gray-500')
                    
                    # Botón Eliminar
                    ui.button(icon='delete', color='red', on_click=lambda e, i=item: borrar_item_wrapper(i)).props('flat round dense').tooltip('Eliminar de la orden')

        dialog_editor.open()

    def borrar_item_wrapper(item):
        ok, msg = db.eliminar_item_orden(item['tipo'], item['id'], dialog_editor.sid)
        if ok:
            ui.notify(msg, type='positive')
            cargar_editor_items(dialog_editor.sid) # Refresca la lista del popup
            actualizar_tablas() # <--- ESTO ES VITAL: Refresca la tabla principal
        else:
            ui.notify(f"Error: {msg}", type='negative')

    # ==========================================
    # 5. ESTRUCTURA VISUAL PRINCIPAL
    # ==========================================
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # Header
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('handyman', size='lg', color='primary')
                titulo = 'Gestión de Taller' if es_admin else 'Mis Asignaciones'
                ui.label(titulo).classes('text-2xl font-bold text-gray-800')

        # Contenedor Principal (Split View)
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # --- PANEL IZQUIERDO: FORMULARIO DE ENTRADA ---
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-blue-500'):
                ui.label('📍 Nueva Entrada').classes('text-lg font-bold text-slate-700 mb-2')
                
                # Switch Tipo (Solo Admin)
                tipo_entrada = ui.toggle(['Orden', 'Cotizacion'], value='Orden').props('spread no-caps active-class="bg-blue-700 text-white"').classes('w-full border rounded mb-4')
                if not es_admin: tipo_entrada.visible = False 

                # Selector Auto
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

            # --- PANEL DERECHO: TABS Y TABLAS ---
            with ui.card().classes('flex-grow w-0 p-0 shadow-lg overflow-hidden'):
                
                with ui.tabs().classes('w-full text-grey') as tabs_control:
                    tab_taller = ui.tab('tab_taller', label='🔧 En Proceso', icon='build').classes('text-blue-700')
                    # Tab Cotizaciones (Solo Admin)
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
                        
                        # SLOT ESTATUS
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
                        
                        # SLOT ACCIONES (Botón Cobrar condicional)
                        btn_cobrar = ''
                        if es_admin:
                            btn_cobrar = (
                                '<q-btn v-if="props.row.estatus_detalle == \'Listo\'" '
                                'icon="payments" size="sm" round color="green" '
                                '@click="$parent.$emit(\'cobrar\', props.row)">'
                                '<q-tooltip>Cobrar</q-tooltip></q-btn>'
                            )
                        
                        # Definición del slot con botones
                        slot_acc = f'''
                            <q-td :props="props">
                                <div class="flex items-center gap-1 justify-center">
                                    <q-btn icon="edit_note" size="sm" flat round color="slate" @click="$parent.$emit('editar_items', props.row.id)"><q-tooltip>Modificar Ítems</q-tooltip></q-btn>
                                    
                                    <q-btn icon="print" size="sm" flat round color="red" @click="$parent.$emit('ver_pdf', props.row.id)"><q-tooltip>Ver Nota</q-tooltip></q-btn>
                                    <q-btn icon="post_add" size="sm" flat round color="indigo" @click="$parent.$emit('add_serv', props.row.id)"><q-tooltip>Mano Obra</q-tooltip></q-btn>
                                    <q-btn icon="inventory_2" size="sm" flat round color="orange" @click="$parent.$emit('add_ref', props.row.id)"><q-tooltip>Refacción</q-tooltip></q-btn>
                                    <q-btn icon="email" size="sm" flat round color="blue" @click="$parent.$emit('email', props.row.id)"><q-tooltip>Enviar por Correo</q-tooltip></q-btn>
                                    {btn_cobrar}
                                </div>
                            </q-td>
                        '''
                        tabla_servicios.add_slot('body-cell-acciones', slot_acc)
                        tabla_servicios.on('editar_items', lambda e: cargar_editor_items(e.args))
                        tabla_servicios.on('email', lambda e: enviar_nota_por_correo(e.args))
                        
                        # Eventos de la tabla
                        tabla_servicios.on('link', lambda e: (ui.clipboard.write(f"https://app.tregal.com.mx/status/{e.args}"), ui.notify('Link copiado')))
                        # AQUÍ LA CLAVE: es_cotizacion=False para Nota de Mostrador
                        tabla_servicios.on('ver_pdf', lambda e: previsualizar_documento(e.args, es_cotizacion=False))
                        tabla_servicios.on('add_serv', lambda e: abrir_agregar_servicio(e.args))
                        tabla_servicios.on('add_ref', lambda e: abrir_refaccion(e.args))
                        tabla_servicios.on('cambiar_status', lambda e: cambiar_estatus_flujo(e.args['id'], e.args['st']))
                        if es_admin: tabla_servicios.on('cobrar', lambda e: abrir_cierre(e.args))

                    # --- TAB 2: COTIZACIONES ---
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
                                    <q-btn label="PDF" icon="print" size="sm" flat color="red" @click="$parent.$emit('ver_pdf', props.row.id)" />
                                    <q-btn label="Aprobar" icon="check_circle" size="sm" color="green" @click="$parent.$emit('aprobar', props.row.id)" />
                                </q-td>
                            ''')
                            
                            tabla_cotizaciones.on('add_serv', lambda e: abrir_agregar_servicio(e.args))
                            # AQUÍ LA CLAVE: es_cotizacion=True
                            tabla_cotizaciones.on('ver_pdf', lambda e: previsualizar_documento(e.args, es_cotizacion=True))
                            tabla_cotizaciones.on('aprobar', lambda e: aprobar_cotizacion(e.args))

    # Carga inicial de datos
    ui.timer(0.1, actualizar_tablas, once=True)
    # 2. Refresco automático cada 5 segundos (Polling)
    # Esto mantiene el tablero sincronizado si hay varios usuarios conectados
    ui.timer(5.0, actualizar_tablas)