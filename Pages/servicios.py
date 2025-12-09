from nicegui import ui, app 
from Db import database as db
import pdf_generator
from datetime import datetime

def show():
    # --- Definición de funciones ---

    # 1. FUNCIÓN DE LIMPIEZA (NUEVA)
    def limpiar_valor_moneda(valor):
        """Limpia el símbolo de moneda ($) y comas (,) para evitar errores de conversión."""
        if isinstance(valor, str):
            valor = valor.replace('$', '').replace(',', '').strip()
        try:
            return float(valor or 0.0)
        except ValueError:
            return 0.0
    
    def actualizar_tabla():
        # Actualiza el tablero de activos
        rows = db.obtener_servicios_activos()
        formatted_rows = []
        for r in rows:
            item = dict(r)
            item['costo_fmt'] = f"${item['costo_estimado']:,.2f}"
            if item['estado'] == 'Terminado': 
                item['estado'] = '✅ PAGADO' 
            formatted_rows.append(item)
        tabla_servicios.rows = formatted_rows
        tabla_servicios.update()
        
        # Actualiza la tabla de historial
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

    def eliminar_servicio(servicio_id):
        # --- GUARDIA DE SEGURIDAD (Eliminar) ---
        if not app.storage.user.get('authenticated', False):
            ui.notify('Sesión expirada. Acceso denegado.', type='negative')
            ui.navigate.to('/login?expired=true')
            return

        exito, msg = db.eliminar_servicio_por_id(servicio_id)
        if exito:
            ui.notify(f'Producto ID {servicio_id} eliminado.', type='positive')
            actualizar_tabla()
        else:
            ui.notify(msg, type='negative')

    def confirmar_eliminacion(servicio_id):
        dialog_confirmar_eliminar.sid = servicio_id
        dialog_confirmar_eliminar.open()


    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. Encabezado
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('handyman', size='lg', color='primary')
                ui.label('Control de Servicios y Taller').classes('text-2xl font-bold text-gray-800')

        # 2. CONTENEDOR DIVIDIDO (Formulario y Tabla Activa)
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # [CÓDIGO PANEL IZQUIERDO DE RECEPCIÓN (Mantenido)]
            with ui.card().classes('w-1/3 min-w-[350px] p-4 shadow-lg sticky top-4 border-t-4 border-blue-500'):
                ui.label('📍 Nueva Orden de Servicio').classes('text-lg font-bold text-slate-700 mb-2')
                
                with ui.row().classes('w-full items-center gap-2'):
                    opciones_autos = db.obtener_vehiculos_select_format()
                    select_auto = ui.select(options=opciones_autos, label='Seleccionar Vehículo', with_input=True).classes('flex-grow')
                    def refrescar_lista_autos():
                        select_auto.options = db.obtener_vehiculos_select_format()
                        select_auto.update()
                        ui.notify('Lista de vehículos actualizada', type='positive')
                    ui.button(icon='refresh', on_click=refrescar_lista_autos).props('flat round dense color=blue').tooltip('Actualizar lista')

                descripcion = ui.textarea('Descripción del Problema / Solicitud').classes('w-full').props('rows=3')
                
                # CORRECCIÓN IMPORTANTE: Quitamos format='$ %.2f' para evitar el crash, usamos prefix.
                costo_inicial = ui.number('Costo Revisión (Inicial)', value=0).classes('w-full').props('prefix="$" step=0.01')

                def crear_orden():
                    if not app.storage.user.get('authenticated', False):
                        ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                        ui.navigate.to('/login?expired=true'); return
                        
                    if not select_auto.value or not descripcion.value:
                        ui.notify('Faltan datos (Vehículo o Descripción)', type='warning'); return
                    
                    # 2. USO DE LIMPIEZA
                    costo_limpio = limpiar_valor_moneda(costo_inicial.value)

                    db.crear_servicio(select_auto.value, descripcion.value, costo_limpio)
                    ui.notify('Orden de servicio creada exitosamente', type='positive')
                    select_auto.value = None; descripcion.value = ''; costo_inicial.value = 0
                    actualizar_tabla()

                ui.button('Generar Orden de Entrada', icon='add_task', on_click=crear_orden).classes('w-full mt-4 bg-slate-800 text-white')

            # PANEL DERECHO: TABLERO DE CONTROL (Tabla Activa)
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('📋 Tablero de Control (En Proceso)').classes('text-lg font-bold text-slate-700')
                    ui.button(icon='refresh', on_click=lambda: actualizar_tabla()).props('flat round dense')

                columns = [
                    {'name': 'id', 'label': 'Folio', 'field': 'id', 'sortable': True, 'align': 'center', 'classes': 'font-bold text-gray-500'},
                    {'name': 'vehiculo', 'label': 'Auto', 'field': 'modelo', 'classes': 'font-bold'},
                    {'name': 'desc', 'label': 'Falla', 'field': 'descripcion', 'classes': 'italic text-xs'},
                    {'name': 'estado', 'label': 'Estado', 'field': 'estado', 'align': 'center'}, 
                    {'name': 'monto', 'label': 'Total', 'field': 'costo_fmt', 'align': 'right', 'classes': 'text-blue-800 font-bold'},
                    {'name': 'acciones', 'label': 'Gestionar', 'field': 'acciones', 'align': 'center'},
                ]

                rows = db.obtener_servicios_activos()
                tabla_servicios = ui.table(columns=columns, rows=rows, row_key='id', pagination=5).classes('w-full')
                
                # Conexión de slots (Se mantiene TU código original)
                tabla_servicios.add_slot('body-cell-id', r'''
                    <q-td :props="props">
                        <div class="flex items-center gap-1">
                            <span class="font-bold text-gray-500 mr-2">#{{ props.value }}</span>
                            <q-btn v-if="props.row.estado !== '✅ PAGADO'" icon="delete_forever" size="xs" color="red-5" round dense @click="$parent.$emit('confirmar_eliminar', props.row.id)" ><q-tooltip>Eliminar Orden</q-tooltip></q-btn>
                            <q-btn icon="picture_as_pdf" size="xs" color="red" round dense @click="$parent.$emit('gen_pdf', props.row.id)" ><q-tooltip>Cotización PDF</q-tooltip></q-btn>
                            <q-btn icon="visibility" size="xs" color="grey" round dense @click="$parent.$emit('ver_detalle', props.row.id)" ><q-tooltip>Ver Detalle</q-tooltip></q-btn>
                            <div v-if="props.row.estado !== '✅ PAGADO'" class="flex gap-1">
                                <q-btn icon="person_add" size="xs" color="purple" round dense @click="$parent.$emit('add_mo', props.row.id)"><q-tooltip>+ Mano de Obra</q-tooltip></q-btn>
                                <q-btn icon="build_circle" size="xs" color="orange" round dense @click="$parent.$emit('add_refa', props.row.id)"><q-tooltip>+ Refacción</q-tooltip></q-btn>
                            </div>
                        </div>
                    </q-td>
                ''')
                tabla_servicios.add_slot('body-cell-estado', r'''
                    <q-td :props="props">
                        <div v-if="props.value !== '✅ PAGADO'">
                            <q-btn label="COBRAR" icon="attach_money" color="green" size="sm" @click="$parent.$emit('cobrar', props.row)" />
                        </div>
                        <div v-else class="text-green-700 font-bold bg-green-100 px-2 rounded text-xs text-center">{{ props.value }}</div>
                    </q-td>
                ''')
        
        # --- NUEVA SECCIÓN: HISTORIAL DE SERVICIOS PAGADOS ---
        with ui.card().classes('w-full p-4 shadow-lg mt-6'):
            ui.label('📂 Historial de Servicios Pagados').classes('text-lg font-bold text-slate-700 mb-2 border-b pb-1')
            
            columns_historial = [
                {'name': 'id', 'label': 'Folio', 'field': 'id', 'align': 'center'},
                {'name': 'fecha_cierre', 'label': 'Fecha Cierre', 'field': 'fecha_cierre_fmt', 'align': 'left', 'classes': 'text-gray-600'},
                {'name': 'vehiculo', 'label': 'Vehículo', 'field': 'modelo', 'classes': 'font-semibold'},
                {'name': 'cliente', 'label': 'Cliente', 'field': 'dueno_nombre'},
                {'name': 'monto', 'label': 'Total Cobrado', 'field': 'costo_fmt', 'align': 'right', 'classes': 'font-bold text-green-700'},
            ]

            rows_historial = formatear_historial(db.obtener_servicios_terminados())
            tabla_historial = ui.table(columns=columns_historial, rows=rows_historial, row_key='id', pagination=5).classes('w-full')


    # [CÓDIGO DE DIÁLOGOS Y CONEXIONES (Mantenido)]
    
    # 0. DIALOGO DE CONFIRMACIÓN DE ELIMINACIÓN
    with ui.dialog() as dialog_confirmar_eliminar, ui.card().classes('w-96'):
        ui.label('⚠️ Confirmar Eliminación').classes('text-xl font-bold text-red-700')
        ui.label('¿Estás seguro de eliminar esta orden de servicio? Esta acción no se puede deshacer.').classes('my-4')
        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancelar', on_click=dialog_confirmar_eliminar.close).props('flat')
            ui.button('Eliminar Permanentemente', on_click=lambda: (eliminar_servicio(dialog_confirmar_eliminar.sid), dialog_confirmar_eliminar.close())).classes('bg-red-700 text-white')

    # A. DIALOGO MANO DE OBRA (Mantenido)
    with ui.dialog() as dialog_comision, ui.card():
        ui.label('Agregar Mano de Obra').classes('text-xl font-bold text-purple-700')
        sel_trab_com = ui.select(options={}, label='Trabajador').classes('w-full')
        txt_tarea = ui.input('Tarea (Ej. Afinación)').classes('w-full')
        with ui.row().classes('w-full'):
            num_costo = ui.number('Costo MO').classes('w-1/2 pr-1').props('prefix="$"')
            num_porc = ui.number('% Comisión').classes('w-1/2 pl-1').props('suffix="%"')
        
        def guardar_comision():
            if not app.storage.user.get('authenticated', False):
                ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                ui.navigate.to('/login?expired=expired=true')
                return
            if not sel_trab_com.value: return

            # 3. USO DE LIMPIEZA
            costo_limpio = limpiar_valor_moneda(num_costo.value)
            porc_limpio = limpiar_valor_moneda(num_porc.value)

            db.agregar_tarea_comision(dialog_comision.sid, sel_trab_com.value, txt_tarea.value, costo_limpio, porc_limpio)
            ui.notify('Mano de obra agregada', type='positive')
            dialog_comision.close()
            actualizar_tabla()
        ui.button('Guardar', on_click=guardar_comision).classes('w-full bg-purple-600 text-white')

    def abrir_comision(sid):
        sel_trab_com.options = db.obtener_trabajadores_select()
        sel_trab_com.update()
        dialog_comision.sid = sid
        dialog_comision.open()

    # B. DIALOGO REFACCIONES (Mantenido)
    with ui.dialog() as dialog_refaccion, ui.card():
        ui.label('Agregar Refacción').classes('text-xl font-bold text-orange-700')
        sel_prod = ui.select(options={}, label='Buscar Pieza', with_input=True).classes('w-full')
        num_cant = ui.number('Cantidad a usar', value=1, format='%.0f').classes('w-full')
        
        def guardar_refaccion():
            if not app.storage.user.get('authenticated', False):
                ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                ui.navigate.to('/login?expired=true')
                return

            if not sel_prod.value: return
            exito, msg = db.agregar_refaccion_a_servicio(dialog_refaccion.sid, sel_prod.value, int(num_cant.value))
            if exito:
                ui.notify(msg, type='positive'); dialog_refaccion.close(); actualizar_tabla()
            else:
                ui.notify(msg, type='negative')
        ui.button('Descontar y Cobrar', on_click=guardar_refaccion).classes('w-full bg-orange-600 text-white')

    def abrir_refaccion(sid):
        sel_prod.options = db.obtener_inventario_select()
        sel_prod.update()
        dialog_refaccion.sid = sid
        num_cant.value = 1
        dialog_refaccion.open()

    # C. DIALOGO DETALLE (Mantenido)
    with ui.dialog() as dialog_detalle, ui.card().classes('w-96'):
        ui.label('Detalle de la Orden').classes('text-lg font-bold')
        lista_detalle = ui.column().classes('w-full')
        def ver_detalle_func(sid): 
            items = db.obtener_detalle_completo_servicio(sid)
            lista_detalle.clear()
            with lista_detalle:
                if not items: ui.label('Orden vacía').classes('italic text-gray-400')
                else:
                    for i in items:
                        color = 'text-purple-600' if i['tipo'] == 'Mano de Obra' else 'text-orange-600'
                        with ui.row().classes('w-full justify-between items-center border-b border-gray-100 py-1'):
                            ui.label(f"{i['cantidad']}x {i['descripcion']}").classes(f'text-sm {color}')
                            ui.label(f"${i['total']:,.2f}").classes('font-bold text-sm')
            dialog_detalle.open()

    # D. DIALOGO COBRO (Mantenido)
    with ui.dialog() as dialog_cierre, ui.card().classes('w-96'):
        ui.label('Cerrar y Cobrar').classes('text-xl font-bold text-green-700')
        sel_cobrador = ui.select(options={}, label='Cajero').classes('w-full')
        txt_ticket = ui.input('Ticket / Factura').classes('w-full')
        def confirmar_cierre():
            if not app.storage.user.get('authenticated', False):
                ui.notify('Sesión expirada. Acceso denegado.', type='negative')
                ui.navigate.to('/login?expired=true')
                return

            if not sel_cobrador.value or not txt_ticket.value:
                ui.notify('Faltan datos', type='warning'); return
            db.cerrar_servicio(dialog_cierre.sid, txt_ticket.value, sel_cobrador.value, dialog_cierre.monto_final)
            ui.notify('¡Cobrado!', type='positive')
            dialog_cierre.close()
            actualizar_tabla()
        ui.button('CONFIRMAR PAGO', on_click=confirmar_cierre).classes('w-full bg-green-600 text-white')

    def abrir_cierre(sid, monto_actual):
        sel_cobrador.options = db.obtener_trabajadores_select()
        sel_cobrador.update()
        dialog_cierre.sid = sid
        dialog_cierre.monto_final = monto_actual
        dialog_cierre.open()

    # E. DIALOGO PDF (Mantenido)
    with ui.dialog() as dialog_pdf, ui.card():
        ui.label('Generar Cotización PDF').classes('text-xl font-bold text-red-700')
        num_vigencia = ui.number('Días de Vigencia', value=15, format='%.0f').classes('w-full')
        def descargar_pdf():
            datos = db.obtener_datos_completos_pdf(dialog_pdf.sid)
            if datos:
                try:
                    archivo = pdf_generator.generar_pdf_cotizacion(datos, int(num_vigencia.value))
                    ui.download(archivo); ui.notify('PDF Generado', type='positive'); dialog_pdf.close()
                except Exception as e: ui.notify(f'Error: {e}', type='negative')
        ui.button('DESCARGAR PDF', on_click=descargar_pdf).classes('w-full bg-red-700 text-white')

    def abrir_pdf(sid):
        dialog_pdf.sid = sid
        dialog_pdf.open()

    # CONEXIÓN EVENTOS VUE -> PYTHON
    tabla_servicios.on('confirmar_eliminar', lambda e: confirmar_eliminacion(e.args))
    tabla_servicios.on('gen_pdf', lambda e: abrir_pdf(e.args))
    tabla_servicios.on('ver_detalle', lambda e: ver_detalle_func(e.args))
    tabla_servicios.on('add_mo', lambda e: abrir_comision(e.args))
    tabla_servicios.on('add_refa', lambda e: abrir_refaccion(e.args))
    tabla_servicios.on('cobrar', lambda e: abrir_cierre(e.args['id'], e.args['costo_estimado']))