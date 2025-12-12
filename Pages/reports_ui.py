import sys
import os
import base64 # NUEVO
from Db import database as db
from nicegui import ui
from datetime import datetime, timedelta
import pdf_generator # NUEVO

def show_reports():
    # Fechas por defecto: El mes actual
    hoy = datetime.now().date()
    inicio_mes = hoy.replace(day=1)
    
    # Variables reactivas para mantener el estado de los datos
    state = {
        'resumen': {'total': 0, 'desglose': []},
        'detalles': []
    }
    date_range = {'from': inicio_mes.strftime('%Y-%m-%d'), 'to': hoy.strftime('%Y-%m-%d')}
    
    # --- VISOR DE PDF (REUTILIZABLE) ---
    with ui.dialog() as dialog_visor, ui.card().classes('w-[90vw] h-[90vh] p-0'):
        with ui.row().classes('w-full bg-slate-800 text-white p-2 items-center justify-between'):
            ui.label('Vista Previa').classes('text-lg font-bold ml-2')
            ui.button(icon='close', on_click=dialog_visor.close).props('flat round dense text-color=white')
        visor_container = ui.html('', sanitize=False).classes('w-full h-full')

    def mostrar_pdf_en_visor(ruta_archivo):
        try:
            with open(ruta_archivo, "rb") as pdf_file:
                b64 = base64.b64encode(pdf_file.read()).decode('utf-8')
            src = f"data:application/pdf;base64,{b64}#toolbar=1"
            visor_container.content = f'<iframe src="{src}" width="100%" height="100%" style="border:none;"></iframe>'
            dialog_visor.open()
        except Exception as e:
            ui.notify(f"Error al abrir PDF: {str(e)}", type='negative')

    # --- GENERADORES ---
    def generar_imprimir_reporte_global():
        """Genera el reporte financiero del rango actual"""
        if not state['detalles']:
            ui.notify('No hay datos para generar el reporte', type='warning')
            return
            
        ruta = pdf_generator.generar_reporte_mensual(
            state['resumen'], 
            state['detalles'], 
            date_range['from'], 
            date_range['to']
        )
        mostrar_pdf_en_visor(ruta)

    def reimprimir_nota_venta(ticket_id):
        """Reconstruye la nota de venta individual"""
        datos = db.obtener_datos_completos_pdf(ticket_id)
        if datos:
            # Generamos el PDF
            ruta = pdf_generator.generar_pdf_cotizacion(datos, dias_vigencia=0, titulo="NOTA DE VENTA")
            
            # --- VALIDACIÓN DE SEGURIDAD ---
            if ruta and isinstance(ruta, str):
                mostrar_pdf_en_visor(ruta)
            else:
                ui.notify('Error: El generador de PDF no devolvió un archivo válido.', type='negative')
        else:
            ui.notify('Error al recuperar datos del ticket. ¿El cliente aún existe?', type='negative')

    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full p-4 gap-6 bg-gray-50'):
        
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('📊 Reporte Financiero & Corte de Caja').classes('text-3xl font-bold text-slate-800')
            
            # BOTON NUEVO: Imprimir Reporte Global
            ui.button('Imprimir Reporte', icon='print', on_click=generar_imprimir_reporte_global).classes('bg-slate-800 text-white')

        # --- FILTROS DE FECHA ---
        with ui.card().classes('w-full p-4 flex flex-row items-center gap-4'):
            ui.icon('calendar_month', size='md', color='primary')
            ui.label('Rango de Consulta:').classes('font-bold')
            
            date_label = ui.label(f"{date_range['from']} -> {date_range['to']}").classes('text-lg bg-gray-100 px-3 py-1 rounded')
            
            with ui.dialog() as date_dialog, ui.card():
                date_picker = ui.date(value=date_range).props('range')
                def on_date_change(e):
                    if isinstance(e.value, dict):
                        date_range['from'] = e.value['from']; date_range['to'] = e.value['to']
                    else:
                        date_range['from'] = e.value; date_range['to'] = e.value
                    date_label.text = f"{date_range['from']} -> {date_range['to']}"
                    cargar_datos()
                date_picker.on_value_change(on_date_change)
                ui.button('Cerrar', on_click=date_dialog.close).classes('w-full')

            ui.button('Cambiar Fechas', on_click=date_dialog.open).props('flat icon=edit')
            ui.button('Hoy', on_click=lambda: (date_picker.set_value(hoy.strftime('%Y-%m-%d')), date_dialog.close())).props('flat')

        # --- TARJETAS DE TOTALES ---
        row_cards = ui.row().classes('w-full gap-4')
        
        # --- TABLA DETALLE ---
        ui.label('Desglose de Tickets').classes('text-xl font-bold mt-4 text-slate-700')
        
        # --- RC4

        # Columnas (Agregamos 'cliente')
        cols = [
            {'name': 'id', 'label': '#', 'field': 'id', 'sortable': True, 'align': 'center'},
            {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha_cierre', 'align': 'left'},
            
            # ✅ NUEVA COLUMNA CLIENTE
            {'name': 'cliente', 'label': 'Cliente', 'field': 'cliente', 'align': 'left', 'classes': 'font-bold text-slate-600'},
            
            {'name': 'auto', 'label': 'Vehículo', 'field': 'modelo', 'align': 'left'},
            {'name': 'metodo', 'label': 'Método', 'field': 'metodo_pago', 'align': 'center'},
            {'name': 'total', 'label': 'Monto', 'field': 'fmt_costo', 'classes': 'font-bold text-green-700', 'align': 'right'},
            {'name': 'acciones', 'label': 'Nota', 'field': 'acciones', 'align': 'center'},
        ]
        
        tabla_detalle = ui.table(columns=cols, rows=[], pagination=10).classes('w-full')
        
        # SLOT PARA BOTÓN DE VER NOTA
        tabla_detalle.add_slot('body-cell-acciones', r'''
            <q-td :props="props">
                <q-btn icon="visibility" size="sm" flat round color="primary" 
                       @click="$parent.$emit('ver_nota', props.row.id)">
                    <q-tooltip>Ver Nota de Venta</q-tooltip>
                </q-btn>
            </q-td>
        ''')
        
        # Conectamos el evento del slot a la función Python
        tabla_detalle.on('ver_nota', lambda e: reimprimir_nota_venta(e.args))

        # --- LOGICA DE CARGA ---
        def cargar_datos():
            f_ini = date_range['from']
            f_fin = date_range['to']
            
            # 1. Obtener Resumen
            datos = db.obtener_resumen_financiero(f_ini, f_fin)
            state['resumen'] = datos # Guardamos en estado para el PDF
            
            row_cards.clear()
            with row_cards:
                with ui.card().classes('bg-slate-800 text-white p-4 items-center min-w-[200px] shadow-lg'):
                    ui.label('VENTA TOTAL').classes('text-xs tracking-widest opacity-80')
                    ui.label(f"${datos['total']:,.2f}").classes('text-3xl font-black text-green-400')
                
                colors = {'Efectivo': 'bg-green-600', 'Tarjeta': 'bg-blue-600', 'Transferencia': 'bg-purple-600'}
                for metodo in datos['desglose']:
                    bg = colors.get(metodo['metodo_pago'].split(' ')[0], 'bg-gray-500')
                    with ui.card().classes(f'{bg} text-white p-4 items-center min-w-[150px] shadow-md'):
                        icon = 'payments' if 'Efectivo' in metodo['metodo_pago'] else 'credit_card'
                        ui.icon(icon, size='sm')
                        ui.label(metodo['metodo_pago']).classes('text-xs font-bold uppercase mt-1')
                        ui.label(f"${metodo['subtotal']:,.2f}").classes('text-xl font-bold')
                        ui.label(f"{metodo['cantidad_tickets']} ops").classes('text-xs opacity-75')

            # 2. Cargar Tabla Detalle
            detalles = db.obtener_detalle_ventas(f_ini, f_fin)
            state['detalles'] = detalles # Guardamos para PDF
            
            for d in detalles:
                d['fmt_costo'] = f"${d['costo_final']:,.2f}"
                if d['fecha_cierre']: d['fecha_cierre'] = str(d['fecha_cierre'])[0:16]
            
            tabla_detalle.rows = detalles
            tabla_detalle.update()

        # Cargar inicial
        ui.timer(0.1, cargar_datos, once=True)