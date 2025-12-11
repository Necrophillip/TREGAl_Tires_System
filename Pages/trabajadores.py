from nicegui import ui, app 
from Db import database as db
from datetime import datetime

def show():
    # --- Estructura Principal ---
    with ui.column().classes('w-full h-full p-4 gap-4 bg-gray-50'):
        
        # 1. ENCABEZADO
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('engineering', size='lg', color='primary')
                ui.label('Equipo y Esquemas de Pago').classes('text-2xl font-bold text-gray-800')

        # 2. CONTENEDOR SPLIT VIEW
        with ui.row().classes('w-full flex-nowrap items-start gap-6'):
            
            # =================================================
            # PANEL IZQUIERDO: GESTIÓN FINANCIERA
            # =================================================
            with ui.card().classes('w-1/3 min-w-[400px] p-4 shadow-lg sticky top-4 border-t-4 border-purple-600'):
                ui.label('Gestión de Integrante').classes('text-lg font-bold text-slate-700 mb-2')
                
                # Selector para EDITAR o CREAR
                opciones_trabajadores = db.obtener_trabajadores_select()
                opciones_trabajadores[0] = '➕ Nuevo Integrante' # Opción especial
                
                select_worker = ui.select(options=opciones_trabajadores, label='Seleccionar Trabajador', value=0).classes('w-full bg-purple-50 rounded px-2 mb-4')
                
                # --- FORMULARIO DATOS GENERALES ---
                ui.label('Datos Generales').classes('text-xs font-bold text-gray-400 uppercase')
                nombre = ui.input('Nombre Completo').classes('w-full')
                fecha_ingreso = ui.input('Fecha Ingreso').classes('w-full').props('type=date')
                sueldo_base = ui.number('Sueldo Base (Semanal)').classes('w-full').props('prefix="$"')

                ui.separator().classes('my-4')

                # --- FORMULARIO ESQUEMA DE PAGO (RC3) ---
                ui.label('Esquema de Ganancias').classes('text-xs font-bold text-purple-600 uppercase')
                
                esquema = ui.select(['Mixto', 'Solo Comisión', 'Solo Sueldo'], label='Tipo de Esquema', value='Mixto').classes('w-full')
                
                with ui.row().classes('w-full gap-2'):
                    pct_mo = ui.number('% Mano Obra').classes('w-1/2').props('suffix="%"')
                    pct_ref = ui.number('% Refacciones').classes('w-1/2').props('suffix="%"')
                
                fijo_servicio = ui.number('Bono Fijo por Servicio').classes('w-full').props('prefix="$"')
                
                ui.label('Nota: Las comisiones se calculan ANTES de IVA.').classes('text-[10px] text-gray-400 italic')

                # --- LOGICA DE CARGA ---
                def cargar_datos_worker(e):
                    # --- CORRECCIÓN AQUÍ: Manejar tanto Objeto (NiceGUI) como Dict (Manual) ---
                    try:
                        wid = e.value # Intento acceder como objeto
                    except AttributeError:
                        wid = e.get('value') # Si falla, accedo como diccionario
                    
                    if wid == 0 or not wid:
                        # Limpiar para nuevo
                        nombre.value = ''
                        fecha_ingreso.value = datetime.now().strftime('%Y-%m-%d')
                        sueldo_base.value = 0
                        pct_mo.value = 0; pct_ref.value = 0; fijo_servicio.value = 0
                        btn_guardar.text = 'Contratar Nuevo'
                        btn_guardar.props('color=green')
                    else:
                        # Cargar existente
                        w_data = db.obtener_trabajador_detalle(wid)
                        if w_data:
                            nombre.value = w_data['nombre']
                            fecha_ingreso.value = w_data['fecha_ingreso']
                            sueldo_base.value = w_data['sueldo_base']
                            # Datos RC3
                            esquema.value = w_data.get('esquema_pago', 'Mixto')
                            pct_mo.value = w_data.get('pct_mano_obra', 0)
                            pct_ref.value = w_data.get('pct_refacciones', 0)
                            fijo_servicio.value = w_data.get('pago_fijo_servicio', 0)
                            
                            btn_guardar.text = 'Actualizar Datos'
                            btn_guardar.props('color=purple')

                select_worker.on_value_change(cargar_datos_worker)

                def guardar_worker():
                    if not app.storage.user.get('authenticated', False): return
                    if not nombre.value: ui.notify('Nombre requerido', type='warning'); return

                    # Lógica para Nuevo vs Actualizar
                    wid = select_worker.value
                    
                    if wid == 0: # NUEVO
                        db.agregar_trabajador(nombre.value, fecha_ingreso.value, float(sueldo_base.value or 0))
                        ui.notify(f'Bienvenido {nombre.value}. Ahora selecciónalo para configurar comisiones.', type='positive')
                    else: # ACTUALIZAR
                        db.actualizar_esquema_trabajador(
                            wid, 
                            esquema.value, 
                            float(pct_mo.value or 0), 
                            float(pct_ref.value or 0), 
                            float(fijo_servicio.value or 0)
                        )
                        ui.notify('Esquema financiero actualizado', type='positive')
                    
                    actualizar_listas()

                btn_guardar = ui.button('Guardar', on_click=guardar_worker).classes('w-full mt-4 text-white')

            # =================================================
            # PANEL DERECHO: VISOR DE RENDIMIENTO
            # =================================================
            with ui.card().classes('flex-grow w-0 p-4 shadow-lg'):
                ui.label('Simulación de Ganancias').classes('text-lg font-bold text-slate-700 mb-4')
                
                with ui.row().classes('w-full gap-4'):
                    with ui.column().classes('flex-1 bg-gray-100 p-4 rounded'):
                        ui.label('Ejemplo: Servicio de $2,000 + IVA').classes('font-bold')
                        ui.label('Refacciones: $1,000 | MO: $1,000').classes('text-sm')
                        ui.separator().classes('my-2')
                        
                        lbl_simulacion = ui.label('$0.00').classes('text-2xl font-bold text-green-600')
                        
                        def simular_calculo():
                            # Calculamos sin IVA
                            p_mo = float(pct_mo.value or 0) / 100
                            p_ref = float(pct_ref.value or 0) / 100
                            fijo = float(fijo_servicio.value or 0)
                            
                            ganancia = (1000 * p_ref) + (1000 * p_mo) + fijo
                            lbl_simulacion.text = f"${ganancia:,.2f}"
                        
                        ui.button('Calcular Simulación', on_click=simular_calculo).props('flat dense')

    def actualizar_listas():
        opciones = db.obtener_trabajadores_select()
        opciones[0] = '➕ Nuevo Integrante'
        select_worker.options = opciones
        select_worker.update()

    # Inicializar (Esta línea era la que daba error, ahora funciona gracias al try/except arriba)
    cargar_datos_worker({'value': 0})