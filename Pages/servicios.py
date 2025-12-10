from nicegui import ui, app 
from Db import database as db
import pdf_generator
from datetime import datetime

def show():
    # --- CONTEXTO DE USUARIO ---
    rol_usuario = app.storage.user.get('rol', 'tecnico')
    user_worker_id = app.storage.user.get('trabajador_id') 
    es_admin = (rol_usuario == 'admin')

    # --- CORRECCIÓN CRÍTICA: Inicializar variable para evitar NameError ---
    tabla_historial = None 

    # --- FUNCIONES AUXILIARES ---
    def limpiar_valor_moneda(valor):
        if isinstance(valor, str): valor = valor.replace('$', '').replace(',', '').strip()
        try: return float(valor or 0.0)
        except ValueError: return 0.0 

    def actualizar_tabla():
        # Filtro: Si es admin ve todo (None), si es técnico ve solo lo suyo
        filtro = None if es_admin else user_worker_id
        
        rows = db.obtener_servicios_activos(filtro_trabajador_id=filtro)
        
        formatted_rows = []
        for r in rows:
            item = dict(r)
            # Ocultar dinero visualmente si no es admin
            item['costo_fmt'] = f"${item['costo_estimado']:,.2f}" if es_admin else "***"
            
            tech_name = item.get('nombre_tecnico') or 'Sin Asignar'
            item['asignado_str'] = tech_name 
            formatted_rows.append(item)
            
        tabla_servicios.rows = formatted_rows
        tabla_servicios.update()
        
        # CORRECCIÓN: Verificar que tabla_historial existe antes de actualizar
        if es_admin and tabla_historial:
            tabla_historial.rows = formatear_historial(db.obtener_servicios_terminados())
            tabla_historial.update()

    def formatear_historial(rows_terminados):
        formatted = []
        for r in rows_terminados:
            item = dict(r)
            item['costo_fmt'] = f"${item['costo_estimado']:,.2f}"
            item['fecha_cierre_fmt'] = item['fecha_cierre'][:10] if item['fecha_cierre'] else 'N/A'
            formatted.append(item)
        return formatted

    # --- FUNCIONES DE ACCIÓN ---
    def cambiar_estatus_flujo(servicio_id, nuevo_estatus):
        db.actualizar_estatus_servicio(servicio_id, nuevo_estatus)
        ui.notify(f'Estatus: {nuevo_estatus}', type='positive')
        actualizar_tabla()

    def copiar_link_cliente(uuid_publico):
        if not uuid_publico: ui.notify('Error: Sin Link', type='warning'); return
        link = f"https://app.tregal.com.mx/status/{uuid_publico}" 
        ui.clipboard.write(link)
        ui.notify('🔗 Link copiado', type='positive')

    def eliminar_servicio(servicio_id):
        if not es_admin: return
        exito, msg = db.eliminar_servicio_por_id(servicio_id)
        if exito: ui.notify('Eliminado', type='positive'); actualizar_tabla()
        else: ui.notify(msg, type='negative')

    def confirmar_eliminacion(servicio_id):
        dialog_confirmar_eliminar.sid = servicio_id
        dialog_confirmar_eliminar.open()


    # --- INTERFAZ ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. Encabezado
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('handyman', size='lg', color='primary')
                titulo = 'Control Maestro' if es_admin else 'Mis Asignaciones'
                ui.label(titulo).classes('text-2xl font-bold text-gray-800')

        # 2. CONTENEDOR PRINCIPAL
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # PANEL IZQUIERDO: NUEVA ORDEN
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-blue-500'):
                ui.label('📍 Recepción de Vehículo').classes('text-lg font-bold text-slate-700 mb-2')
                
                with ui.row().classes('w-full items-center gap-2'):
                    opciones_autos = db.obtener_vehiculos_select_format()
                    select_auto = ui.select(options=opciones_autos, label='Seleccionar Vehículo', with_input=True).classes('flex-grow')
                    ui.button(icon='refresh', on_click=lambda: (select_auto.set_options(db.obtener_vehiculos_select_format()), ui.notify('Actualizado'))).props('flat round dense')

                descripcion = ui.textarea('Falla Reportada').classes('w-full').props('rows=3')
                
                # --- ASIGNACIÓN DE TÉCNICO (Solo Admin) ---
                select_asignacion = None
                if es_admin:
                    opciones_tech = db.obtener_trabajadores_select()
                    select_asignacion = ui.select(options=opciones_tech, label='Asignar Técnico Responsable').classes('w-full')
                
                # Costo (Solo Admin ve el input)
                costo_inicial = ui.number('Costo Revisión', value=0).classes('w-full').props('prefix="$" step=0.01')
                costo_inicial.visible = es_admin 

                def crear_orden():
                    if not select_auto.value or not descripcion.value:
                        ui.notify('Faltan datos', type='warning'); return
                    
                    c_ini = costo_inicial.value if es_admin else 0.0
                    costo_limpio = limpiar_valor_moneda(str(c_ini))
                    
                    id_asignado = None
                    if es_admin and select_asignacion:
                        id_asignado = select_asignacion.value 
                    elif not es_admin:
                        id_asignado = user_worker_id 

                    db.crear_servicio(select_auto.value, descripcion.value, costo_limpio, id_asignado)
                    
                    ui.notify('Orden creada exitosamente', type='positive')
                    select_auto.value = None; descripcion.value = ''
                    if es_admin: 
                        costo_inicial.value = 0
                        select_asignacion.value = None
                    actualizar_tabla()

                ui.button('Ingresar al Taller', icon='garage', on_click=crear_orden).classes('w-full mt-4 bg-slate-800 text-white')

            # PANEL DERECHO: TABLERO
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    subtitulo = 'Todas las Órdenes' if es_admin else 'Mis Trabajos Pendientes'
                    ui.label(subtitulo).classes('text-lg font-bold text-slate-700')
                    ui.button(icon='refresh', on_click=lambda: actualizar_tabla()).props('flat round dense')

                # Columnas
                columns = [
                    {'name': 'id', 'label': '#', 'field': 'id', 'sortable': True, 'align': 'center', 'classes': 'font-bold text-gray-400'},
                    {'name': 'estatus', 'label': 'Progreso', 'field': 'estatus_detalle', 'align': 'center', 'classes': 'font-bold text-blue-600'},
                    {'name': 'vehiculo', 'label': 'Auto', 'field': 'modelo', 'classes': 'font-bold'},
                    {'name': 'desc', 'label': 'Trabajo', 'field': 'descripcion', 'classes': 'italic text-xs'},
                ]
                
                if es_admin:
                    columns.insert(3, {'name': 'asignado', 'label': 'Técnico', 'field': 'asignado_str', 'align': 'center', 'classes': 'text-purple-700 text-xs font-bold'})
                    columns.append({'name': 'monto', 'label': 'Total', 'field': 'costo_fmt', 'align': 'right', 'classes': 'text-green-700 font-bold'})
                
                columns.append({'name': 'acciones', 'label': 'Control', 'field': 'acciones', 'align': 'center'})

                tabla_servicios = ui.table(columns=columns, rows=[], row_key='id', pagination=5).classes('w-full')
                
                # Slots
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
                        <q-btn flat round dense icon="link" size="xs" color="grey" @click="$parent.$emit('copiar_link', props.row.uuid_publico)"><q-tooltip>Link Cliente</q-tooltip></q-btn>
                    </q-td>
                ''')

                slot_acciones = r'''
                        <q-td :props="props">
                            <div class="flex items-center gap-1 justify-center">
                                <q-btn icon="delete" size="xs" color="red-2" round flat dense @click="$parent.$emit('confirmar_eliminar', props.row.id)" />
                                <q-btn icon="picture_as_pdf" size="xs" color="red" round dense @click="$parent.$emit('gen_pdf', props.row.id)" />
                                <q-btn icon="visibility" size="xs" color="grey" round dense @click="$parent.$emit('ver_detalle', props.row.id)" />
                                <q-btn icon="build" size="xs" color="orange" round dense @click="$parent.$emit('add_refa', props.row.id)" />
                                <q-btn icon="person" size="xs" color="purple" round dense @click="$parent.$emit('add_mo', props.row.id)" />
                                <q-btn v-if="props.row.estatus_detalle === 'Listo'" label="$" color="green" size="sm" round dense @click="$parent.$emit('cobrar', props.row)" />
                            </div>
                        </q-td>
                    ''' if es_admin else r'''
                        <q-td :props="props">
                            <div class="flex items-center gap-1 justify-center">
                                <q-btn icon="visibility" size="xs" color="grey" round dense @click="$parent.$emit('ver_detalle', props.row.id)"><q-tooltip>Instrucciones</q-tooltip></q-btn>
                                <q-btn icon="build" size="xs" color="orange" round dense @click="$parent.$emit('add_refa', props.row.id)"><q-tooltip>Pedir Pieza</q-tooltip></q-btn>
                                <q-btn icon="person" size="xs" color="purple" round dense @click="$parent.$emit('add_mo', props.row.id)"><q-tooltip>Reportar Trabajo</q-tooltip></q-btn>
                            </div>
                        </q-td>
                    '''
                tabla_servicios.add_slot('body-cell-acciones', slot_acciones)
                
                # Inicializar carga
                actualizar_tabla()


        # --- HISTORIAL ADMIN ---
        if es_admin:
            with ui.card().classes('w-full p-4 shadow-lg mt-6'):
                ui.label('📂 Historial Global').classes('text-lg font-bold text-slate-700 mb-2 border-b pb-1')
                columns_historial = [
                    {'name': 'id', 'label': 'Folio', 'field': 'id', 'align': 'center'},
                    {'name': 'fecha_cierre', 'label': 'Cierre', 'field': 'fecha_cierre_fmt', 'align': 'left'},
                    {'name': 'vehiculo', 'label': 'Auto', 'field': 'modelo'},
                    {'name': 'monto', 'label': 'Total', 'field': 'costo_fmt', 'align': 'right', 'classes': 'font-bold text-green-700'},
                ]
                rows_historial = formatear_historial(db.obtener_servicios_terminados())
                # AQUÍ asignamos la variable que inicializamos como None arriba
                tabla_historial = ui.table(columns=columns_historial, rows=rows_historial, row_key='id', pagination=5).classes('w-full')


    # [ DIÁLOGOS ]
    with ui.dialog() as dialog_confirmar_eliminar, ui.card():
        ui.label('⚠️ ¿Eliminar?').classes('font-bold text-red')
        with ui.row():
            ui.button('Sí', on_click=lambda: (eliminar_servicio(dialog_confirmar_eliminar.sid), dialog_confirmar_eliminar.close())).classes('bg-red')
            ui.button('No', on_click=dialog_confirmar_eliminar.close).props('flat')

    # DIALOGO MO
    with ui.dialog() as dialog_comision, ui.card():
        ui.label('Registrar Mano de Obra').classes('text-xl font-bold text-purple-700')
        sel_trab_com = ui.select(options={}, label='Técnico').classes('w-full')
        txt_tarea = ui.input('Tarea').classes('w-full')
        with ui.row().classes('w-full'):
            num_costo = ui.number('Costo').classes('w-1/2').props('prefix="$" step=0.01'); num_costo.visible = es_admin
            num_porc = ui.number('% Comisión').classes('w-1/2').props('suffix="%"'); num_porc.visible = es_admin
        def guardar_comision():
            c = limpiar_valor_moneda(num_costo.value) if es_admin else 0
            p = limpiar_valor_moneda(num_porc.value) if es_admin else 0
            db.agregar_tarea_comision(dialog_comision.sid, sel_trab_com.value, txt_tarea.value, c, p)
            ui.notify('Guardado', type='positive'); dialog_comision.close(); actualizar_tabla()
        ui.button('Guardar', on_click=guardar_comision).classes('w-full bg-purple-600 text-white')

    def abrir_comision(sid):
        sel_trab_com.options = db.obtener_trabajadores_select()
        sel_trab_com.update(); dialog_comision.sid = sid
        if not es_admin and user_worker_id:
            sel_trab_com.value = user_worker_id
            sel_trab_com.disable() 
        dialog_comision.open()

    # REFACCIONES
    with ui.dialog() as dialog_refaccion, ui.card():
        ui.label('Refacción').classes('text-xl font-bold text-orange-700')
        sel_prod = ui.select(options={}, label='Pieza', with_input=True).classes('w-full')
        num_cant = ui.number('Cantidad', value=1).classes('w-full')
        def guardar_refaccion():
            db.agregar_refaccion_a_servicio(dialog_refaccion.sid, sel_prod.value, int(num_cant.value))
            ui.notify('Agregado', type='positive'); dialog_refaccion.close(); actualizar_tabla()
        ui.button('Agregar', on_click=guardar_refaccion).classes('w-full bg-orange-600 text-white')
    def abrir_refaccion(sid): 
        sel_prod.options = db.obtener_inventario_select(); sel_prod.update(); dialog_refaccion.sid = sid; dialog_refaccion.open()

    # DETALLE
    with ui.dialog() as dialog_detalle, ui.card().classes('w-96'):
        ui.label('Detalle').classes('font-bold')
        lista_detalle = ui.column().classes('w-full')
        def ver_detalle_func(sid): 
            items = db.obtener_detalle_completo_servicio(sid)
            lista_detalle.clear()
            with lista_detalle:
                if not items: ui.label('Vacío').classes('text-gray-400')
                for i in items:
                    with ui.row().classes('w-full justify-between border-b'):
                        ui.label(f"{i['cantidad']}x {i['descripcion']}").classes('text-sm')
                        if es_admin: ui.label(f"${i['total']:,.2f}").classes('font-bold text-sm')
            dialog_detalle.open()

    # PDF
    with ui.dialog() as dialog_pdf, ui.card():
        num_vigencia = ui.number('Vigencia', value=15)
        def descargar_pdf():
            d = db.obtener_datos_completos_pdf(dialog_pdf.sid)
            if d: ui.download(pdf_generator.generar_pdf_cotizacion(d, int(num_vigencia.value)))
            dialog_pdf.close()
        ui.button('PDF', on_click=descargar_pdf)
    def abrir_pdf(sid): dialog_pdf.sid = sid; dialog_pdf.open()
    
    # COBRO
    with ui.dialog() as dialog_cierre, ui.card():
        sel_cajero = ui.select(options={}, label='Cajero').classes('w-full')
        txt_tic = ui.input('Ticket').classes('w-full')
        def confirmar_cierre():
            db.cerrar_servicio(dialog_cierre.sid, txt_tic.value, sel_cajero.value, dialog_cierre.monto)
            ui.notify('Cobrado', type='positive'); dialog_cierre.close(); actualizar_tabla()
        ui.button('Pagar', on_click=confirmar_cierre).classes('bg-green text-white w-full')
    def abrir_cierre(row):
        if not es_admin: return
        sel_cajero.options = db.obtener_trabajadores_select(); sel_cajero.update()
        dialog_cierre.sid = row['id']; dialog_cierre.monto = row['costo_estimado']; dialog_cierre.open()


    # CONEXIONES
    tabla_servicios.on('confirmar_eliminar', lambda e: confirmar_eliminacion(e.args))
    tabla_servicios.on('gen_pdf', lambda e: abrir_pdf(e.args))
    tabla_servicios.on('ver_detalle', lambda e: ver_detalle_func(e.args))
    tabla_servicios.on('add_mo', lambda e: abrir_comision(e.args))
    tabla_servicios.on('add_refa', lambda e: abrir_refaccion(e.args))
    tabla_servicios.on('cobrar', lambda e: abrir_cierre(e.args))
    tabla_servicios.on('cambiar_status', lambda e: cambiar_estatus_flujo(e.args['id'], e.args['st']))
    tabla_servicios.on('copiar_link', lambda e: copiar_link_cliente(e.args))