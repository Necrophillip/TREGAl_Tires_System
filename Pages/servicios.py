from nicegui import ui
from Db import database as db
import pdf_generator  # <--- Importamos el generador de PDF

def show():
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # --- CABECERA ---
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Recepción y Servicios').classes('text-2xl font-bold text-gray-800')
            with ui.row():
                ui.icon('handyman', size='lg', color='primary')
                ui.icon('assignment', size='lg', color='secondary')

        with ui.row().classes('w-full gap-6'):
            
            # --- PANEL IZQUIERDO: NUEVA ORDEN ---
            with ui.card().classes('w-1/3 p-4 shadow-lg border-t-4 border-blue-500'):
                ui.label('Nueva Orden').classes('text-lg font-bold mb-4 text-gray-700')
                
                # Buscador de vehículos con botón de refresh
                with ui.row().classes('w-full items-center gap-2'):
                    opciones_autos = db.obtener_vehiculos_select_format()
                    select_auto = ui.select(
                        options=opciones_autos, 
                        label='Buscar Vehículo', 
                        with_input=True
                    ).classes('flex-grow')
                    
                    def refrescar_lista_autos():
                        select_auto.options = db.obtener_vehiculos_select_format()
                        select_auto.update()
                        ui.notify('Lista de vehículos actualizada', type='positive')
                    
                    ui.button(icon='refresh', on_click=refrescar_lista_autos).props('flat round dense color=blue').tooltip('Actualizar lista')

                descripcion = ui.textarea(label='Descripción Inicial / Fallas').classes('w-full').props('rows=4')
                ui.label('Nota: El costo se calculará al agregar items.').classes('text-xs text-gray-400 italic')

                def guardar_orden():
                    if not select_auto.value or not descripcion.value:
                        ui.notify('Faltan datos', type='warning')
                        return
                    
                    # Creamos la orden con costo inicial 0
                    db.crear_servicio(select_auto.value, descripcion.value, 0.0)
                    ui.notify('Orden creada exitosamente', type='positive')
                    
                    # Limpiar
                    select_auto.value = None
                    descripcion.value = ''
                    actualizar_tabla()

                ui.button('ABRIR ORDEN', on_click=guardar_orden, icon='add_task').classes('w-full mt-4 bg-blue-600 text-white')

            # --- PANEL DERECHO: TABLA DE SERVICIOS ---
            with ui.card().classes('w-2/3 p-4 shadow-lg'):
                ui.label('Tablero de Control').classes('text-lg font-bold mb-2 text-gray-700')
                
                columns = [
                    {'name': 'id', 'label': '#', 'field': 'id', 'sortable': True, 'align': 'left'},
                    {'name': 'vehiculo', 'label': 'Auto', 'field': 'modelo', 'classes': 'font-bold'},
                    {'name': 'desc', 'label': 'Falla', 'field': 'descripcion', 'classes': 'italic text-xs'},
                    {'name': 'estado', 'label': 'Estado', 'field': 'estado', 'classes': 'font-bold'},
                    {'name': 'monto', 'label': 'Total', 'field': 'costo_fmt', 'align': 'right', 'classes': 'text-blue-800 font-bold'},
                ]
                
                tabla_servicios = ui.table(columns=columns, rows=[], row_key='id').classes('w-full')
                
                def actualizar_tabla():
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

                actualizar_tabla()

                # ==========================================
                #       SECCIÓN DE DIÁLOGOS (POP-UPS)
                # ==========================================

                # A. DIALOGO MANO DE OBRA (TRABAJADORES)
                with ui.dialog() as dialog_comision, ui.card():
                    ui.label('Agregar Mano de Obra').classes('text-xl font-bold text-purple-700')
                    sel_trab_com = ui.select(options={}, label='Trabajador').classes('w-full')
                    txt_tarea = ui.input('Tarea (Ej. Afinación)').classes('w-full')
                    with ui.row().classes('w-full'):
                        num_costo = ui.number('Costo MO').classes('w-1/2 pr-1').props('prefix="$"')
                        num_porc = ui.number('% Comisión').classes('w-1/2 pl-1').props('suffix="%"')
                    
                    def guardar_comision():
                        if not sel_trab_com.value: return
                        db.agregar_tarea_comision(dialog_comision.sid, sel_trab_com.value, txt_tarea.value, float(num_costo.value or 0), float(num_porc.value or 0))
                        ui.notify('Mano de obra agregada', type='positive')
                        dialog_comision.close()
                        actualizar_tabla()
                    ui.button('Guardar', on_click=guardar_comision).classes('w-full bg-purple-600 text-white')

                def abrir_comision(sid):
                    sel_trab_com.options = db.obtener_trabajadores_select()
                    sel_trab_com.update()
                    dialog_comision.sid = sid
                    dialog_comision.open()

                # B. DIALOGO REFACCIONES (INVENTARIO)
                with ui.dialog() as dialog_refaccion, ui.card():
                    ui.label('Agregar Refacción').classes('text-xl font-bold text-orange-700')
                    sel_prod = ui.select(options={}, label='Buscar Pieza', with_input=True).classes('w-full')
                    num_cant = ui.number('Cantidad a usar', value=1, format='%.0f').classes('w-full')
                    
                    def guardar_refaccion():
                        if not sel_prod.value: return
                        exito, msg = db.agregar_refaccion_a_servicio(dialog_refaccion.sid, sel_prod.value, int(num_cant.value))
                        if exito:
                            ui.notify(msg, type='positive')
                            dialog_refaccion.close()
                            actualizar_tabla()
                        else:
                            ui.notify(msg, type='negative')

                    ui.button('Descontar y Cobrar', on_click=guardar_refaccion).classes('w-full bg-orange-600 text-white')

                def abrir_refaccion(sid):
                    sel_prod.options = db.obtener_inventario_select()
                    sel_prod.update()
                    dialog_refaccion.sid = sid
                    num_cant.value = 1
                    dialog_refaccion.open()
                
                # C. DIALOGO DETALLE (VER TODO)
                with ui.dialog() as dialog_detalle, ui.card().classes('w-96'):
                    ui.label('Detalle de la Orden').classes('text-lg font-bold')
                    lista_detalle = ui.column().classes('w-full')
                    
                    def ver_detalle(sid):
                        items = db.obtener_detalle_completo_servicio(sid)
                        lista_detalle.clear()
                        with lista_detalle:
                            if not items:
                                ui.label('Orden vacía').classes('italic text-gray-400')
                            else:
                                for i in items:
                                    icono = 'person' if i['tipo'] == 'Mano de Obra' else 'build'
                                    color = 'text-purple-600' if i['tipo'] == 'Mano de Obra' else 'text-orange-600'
                                    with ui.row().classes('w-full justify-between items-center border-b border-gray-100 py-1'):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon(icono).classes(f'{color}')
                                            ui.label(f"{i['cantidad']}x {i['descripcion']}").classes('text-sm')
                                        ui.label(f"${i['total']:,.2f}").classes('font-bold text-sm')
                        dialog_detalle.open()

                # D. DIALOGO DE COBRO (CIERRE)
                with ui.dialog() as dialog_cierre, ui.card().classes('w-96'):
                    ui.label('Cerrar y Cobrar').classes('text-xl font-bold text-green-700')
                    lbl_cierre_monto = ui.label('').classes('text-2xl font-bold text-center w-full my-4')
                    sel_cobrador = ui.select(options={}, label='Cajero').classes('w-full')
                    txt_ticket = ui.input('Ticket / Factura').classes('w-full')

                    def confirmar_cierre():
                        if not sel_cobrador.value or not txt_ticket.value:
                            ui.notify('Faltan datos de cobro', type='warning')
                            return
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
                    lbl_cierre_monto.text = f"Total: ${monto_actual:,.2f}"
                    dialog_cierre.open()

                # E. DIALOGO PDF (GENERADOR) - ¡NUEVO!
                with ui.dialog() as dialog_pdf, ui.card():
                    ui.label('Generar Cotización PDF').classes('text-xl font-bold text-red-700')
                    ui.label('Configuración:').classes('text-sm text-gray-500')
                    num_vigencia = ui.number('Días de Vigencia', value=15, format='%.0f').classes('w-full')
                    
                    def descargar_pdf():
                        # 1. Obtener datos
                        datos = db.obtener_datos_completos_pdf(dialog_pdf.sid)
                        if not datos:
                            ui.notify('Error al leer datos', type='negative')
                            return
                        # 2. Generar y Descargar
                        try:
                            archivo = pdf_generator.generar_pdf_cotizacion(datos, int(num_vigencia.value))
                            ui.download(archivo)
                            ui.notify('PDF Generado', type='positive')
                            dialog_pdf.close()
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', type='negative')

                    ui.button('DESCARGAR PDF', on_click=descargar_pdf, icon='picture_as_pdf').classes('w-full bg-red-700 text-white')

                def abrir_pdf(sid):
                    dialog_pdf.sid = sid
                    dialog_pdf.open()

                # ==========================================
                #       SLOTS E INYECCIÓN DE BOTONES
                # ==========================================

                # Slot Columna ID: Botones de Acción (PDF, Detalle, +MO, +Refa)
                tabla_servicios.add_slot('body-cell-id', '''
                    <q-td :props="props">
                        <div class="flex items-center gap-1">
                            <span class="font-bold text-gray-500 mr-2">#{{ props.value }}</span>
                            
                            <q-btn icon="picture_as_pdf" size="xs" color="red" round dense 
                                   @click="$parent.$emit('gen_pdf', props.row.id)" >
                                <q-tooltip>Cotización PDF</q-tooltip>
                            </q-btn>

                            <q-btn icon="visibility" size="xs" color="grey" round dense 
                                   @click="$parent.$emit('ver_detalle', props.row.id)" >
                                <q-tooltip>Ver Detalle</q-tooltip>
                            </q-btn>

                            <div v-if="props.row.estado !== '✅ PAGADO'" class="flex gap-1">
                                <q-btn icon="person_add" size="xs" color="purple" round dense 
                                    @click="$parent.$emit('add_mo', props.row.id)">
                                    <q-tooltip>+ Mano de Obra</q-tooltip>
                                </q-btn>
                                
                                <q-btn icon="build_circle" size="xs" color="orange" round dense 
                                    @click="$parent.$emit('add_refa', props.row.id)">
                                    <q-tooltip>+ Refacción</q-tooltip>
                                </q-btn>
                            </div>
                        </div>
                    </q-td>
                ''')

                # Slot Columna Estado: Botón de Cobro
                tabla_servicios.add_slot('body-cell-estado', '''
                    <q-td :props="props">
                        <div v-if="props.value !== '✅ PAGADO'">
                            <q-btn label="COBRAR" icon="attach_money" color="green" size="sm" 
                                   @click="$parent.$emit('cobrar', props.row)" />
                        </div>
                        <div v-else class="text-green-700 font-bold bg-green-100 px-2 rounded">
                            {{ props.value }}
                        </div>
                    </q-td>
                ''')
                
                # Conexión de Eventos (Vue -> Python)
                tabla_servicios.on('gen_pdf', lambda e: abrir_pdf(e.args))
                tabla_servicios.on('ver_detalle', lambda e: ver_detalle(e.args))
                tabla_servicios.on('add_mo', lambda e: abrir_comision(e.args))
                tabla_servicios.on('add_refa', lambda e: abrir_refaccion(e.args))
                tabla_servicios.on('cobrar', lambda e: abrir_cierre(e.args['id'], e.args['costo_estimado']))