import sys
import os
from Db import database as db
from nicegui import ui
from datetime import datetime, timedelta

def show_reports():
    # Fechas por defecto: El mes actual
    hoy = datetime.now().date()
    inicio_mes = hoy.replace(day=1)
    
    # Variables reactivas
    date_range = {'from': inicio_mes.strftime('%Y-%m-%d'), 'to': hoy.strftime('%Y-%m-%d')}
    
    # Contenedor principal
    with ui.column().classes('w-full p-4 gap-6 bg-gray-50'):
        
        ui.label('📊 Reporte Financiero & Corte de Caja').classes('text-3xl font-bold text-slate-800')

        # --- FILTROS DE FECHA ---
        with ui.card().classes('w-full p-4 flex flex-row items-center gap-4'):
            ui.icon('calendar_month', size='md', color='primary')
            ui.label('Rango de Consulta:').classes('font-bold')
            
            # Input de fecha visual
            date_label = ui.label(f"{date_range['from']} -> {date_range['to']}").classes('text-lg bg-gray-100 px-3 py-1 rounded')
            
            with ui.dialog() as date_dialog, ui.card():
                # Selector de rango
                date_picker = ui.date(value=date_range).props('range')
                
                def on_date_change(e):
                    # Actualizar etiquetas y recargar datos
                    if isinstance(e.value, dict): # Es un rango
                        date_range['from'] = e.value['from']
                        date_range['to'] = e.value['to']
                    else: # Es un solo dia
                        date_range['from'] = e.value
                        date_range['to'] = e.value
                    
                    date_label.text = f"{date_range['from']} -> {date_range['to']}"
                    cargar_datos() # Recargar tablas
                    
                date_picker.on_value_change(on_date_change)
                ui.button('Cerrar', on_click=date_dialog.close).classes('w-full')

            ui.button('Cambiar Fechas', on_click=date_dialog.open).props('flat icon=edit')
            ui.button('Hoy', on_click=lambda: (date_picker.set_value(hoy.strftime('%Y-%m-%d')), date_dialog.close())).props('flat')

        # --- TARJETAS DE TOTALES ---
        row_cards = ui.row().classes('w-full gap-4')
        
        # --- TABLA DETALLE ---
        ui.label('Desglose de Tickets').classes('text-xl font-bold mt-4 text-slate-700')
        tabla_detalle = ui.table(
            columns=[
                {'name': 'id', 'label': 'Ticket #', 'field': 'id', 'sortable': True},
                {'name': 'fecha', 'label': 'Hora Cierre', 'field': 'fecha_cierre'},
                {'name': 'auto', 'label': 'Vehículo', 'field': 'modelo'},
                {'name': 'metodo', 'label': 'Método', 'field': 'metodo_pago'},
                {'name': 'total', 'label': 'Monto', 'field': 'fmt_costo', 'classes': 'font-bold text-green-700'},
            ],
            rows=[],
            pagination=10
        ).classes('w-full')

        # --- LOGICA DE CARGA ---
        def cargar_datos():
            f_ini = date_range['from']
            f_fin = date_range['to']
            
            # 1. Obtener Resumen
            datos = db.obtener_resumen_financiero(f_ini, f_fin)
            
            # Limpiar área de tarjetas
            row_cards.clear()
            with row_cards:
                # Tarjeta Total General
                with ui.card().classes('bg-slate-800 text-white p-4 items-center min-w-[200px]'):
                    ui.label('VENTA TOTAL').classes('text-sm opacity-80')
                    ui.label(f"${datos['total']:,.2f}").classes('text-3xl font-black')
                
                # Tarjetas por Método
                colors = {'Efectivo': 'bg-green-600', 'Tarjeta': 'bg-blue-600', 'Transferencia': 'bg-purple-600'}
                
                for metodo in datos['desglose']:
                    bg = colors.get(metodo['metodo_pago'].split(' ')[0], 'bg-gray-500')
                    with ui.card().classes(f'{bg} text-white p-4 items-center min-w-[150px]'):
                        ui.icon('payments' if 'Efectivo' in metodo['metodo_pago'] else 'credit_card', size='sm')
                        ui.label(metodo['metodo_pago']).classes('text-xs font-bold uppercase')
                        ui.label(f"${metodo['subtotal']:,.2f}").classes('text-xl font-bold')
                        ui.label(f"{metodo['cantidad_tickets']} tickets").classes('text-xs opacity-75')

            # 2. Cargar Tabla Detalle
            detalles = db.obtener_detalle_ventas(f_ini, f_fin)
            for d in detalles:
                d['fmt_costo'] = f"${d['costo_final']:,.2f}"
                # Recortar fecha larga
                if d['fecha_cierre']: d['fecha_cierre'] = str(d['fecha_cierre'])[0:16] 
            
            tabla_detalle.rows = detalles
            tabla_detalle.update()

        # Cargar inicial (con pequeño delay para UI fluida)
        ui.timer(0.1, cargar_datos, once=True)

# Nota: Para probarlo, llámalo en tu main.py en una ruta nueva:
# @ui.page('/admin/reportes')
# def pagina_reportes():
#     show_reports()