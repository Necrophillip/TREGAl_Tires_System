from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from datetime import datetime, timedelta
import os

# ==========================================
# 1. GENERADOR DE DOCUMENTOS (Cotización / Nota)
# ==========================================
def generar_pdf_cotizacion(datos, dias_vigencia, titulo="COTIZACIÓN"):
    """
    Genera un PDF elegante para TREGAL Tires.
    Soporta cambio de título para Nota de Mostrador.
    """
    filename = f"Documento_{datos['id']}.pdf"
    
    c = canvas.Canvas(filename, pagesize=LETTER)
    width, height = LETTER
    
    # --- COLORES DE MARCA ---
    COLOR_PRIMARIO = colors.HexColor("#1e293b") 
    COLOR_ACENTO = colors.HexColor("#ea580c")   
    COLOR_GRIS = colors.HexColor("#64748b")
    
    # 1. ENCABEZADO
    c.setFillColor(COLOR_PRIMARIO)
    c.rect(0, 0, 30, height, fill=1, stroke=0)
    
    c.setFillColor(COLOR_PRIMARIO)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(50, height - 50, "TREGAL TIRES")
    
    c.setFillColor(COLOR_ACENTO)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 65, "ESPECIALISTAS AUTOMOTRICES")

    c.setFillColor(COLOR_GRIS)
    c.setFont("Helvetica", 9)
    c.drawString(50, height - 85, "Dirección: Av. José de Gálvez 1355, Central de Abastos, 78390 San Luis Potosí, S.L.P., Mexico")
    c.drawString(50, height - 97, "Tel: 821 4588/89 | Email: Regina.Gallegos@servillantas.com")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(width - 30, height - 50, titulo)
    
    c.setFillColor(COLOR_ACENTO)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 30, height - 70, f"#{datos['id']:04d}") 

    # 2. DATOS DEL CLIENTE Y FECHAS
    y_bloque = height - 140
    
    # Cliente
    c.setFillColor(COLOR_PRIMARIO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_bloque, "CLIENTE:")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawString(50, y_bloque - 15, datos['cliente'])
    c.setFont("Helvetica", 9)
    tel_str = datos['telefono'] if datos['telefono'] else "Sin teléfono"
    c.drawString(50, y_bloque - 30, tel_str)

    # Vehículo
    c.setFillColor(COLOR_PRIMARIO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(250, y_bloque, "VEHÍCULO:")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawString(250, y_bloque - 15, f"{datos['modelo']} ({datos['anio']})")
    c.setFont("Helvetica", 9)
    c.drawString(250, y_bloque - 28, f"Placas: {datos['placas']}  |  Color: {datos['color']}")
    
    eco = datos.get('num_economico') or "N/A"
    vin_num = datos.get('vin') or "N/A"
    kms = datos.get('kilometraje') or "N/A"
    c.drawString(250, y_bloque - 40, f"No. Eco: {eco}  |  Kms: {kms}")
    c.drawString(250, y_bloque - 52, f"VIN: {vin_num}")

    # Fechas
    fecha_emision = datetime.now()
    fecha_vence = fecha_emision + timedelta(days=dias_vigencia)
    
    c.setFillColor(COLOR_PRIMARIO)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 30, y_bloque, "FECHA EMISIÓN:")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 30, y_bloque - 15, fecha_emision.strftime("%d/%m/%Y"))
    
    if dias_vigencia > 0:
        c.setFillColor(colors.red)
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width - 30, y_bloque - 35, "VIGENCIA:")
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawRightString(width - 30, y_bloque - 50, fecha_vence.strftime("%d/%m/%Y"))

    c.setStrokeColor(colors.lightgrey)
    c.line(50, y_bloque - 65, width - 30, y_bloque - 65)

    # 3. TABLA DE PRODUCTOS
    data_tabla = [['CANT', 'DESCRIPCIÓN / SERVICIO', 'TIPO', 'P. UNIT', 'TOTAL']]
    total_general = 0
    
    if 'items' in datos and datos['items']:
        for item in datos['items']:
            descripcion = item['descripcion']
            if len(descripcion) > 45: descripcion = descripcion[:45] + "..."
            
            row = [
                str(item['cantidad']),
                descripcion,
                item['tipo'],
                f"${item['unitario']:,.2f}",
                f"${item['total']:,.2f}"
            ]
            data_tabla.append(row)
            total_general += item['total']
    
    col_widths = [40, 280, 80, 80, 80]
    tabla = Table(data_tabla, colWidths=col_widths)
    
    estilo_tabla = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARIO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ])
    tabla.setStyle(estilo_tabla)
    
    w_tab, h_tab = tabla.wrap(width, height)
    tabla.drawOn(c, 50, height - 230 - h_tab)
    
    # 4. TOTALES
    y_totales = height - 250 - h_tab
    c.setFillColor(COLOR_PRIMARIO)
    c.rect(width - 200, y_totales - 40, 170, 40, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width - 190, y_totales - 25, "TOTAL:")
    c.drawRightString(width - 40, y_totales - 25, f"${total_general:,.2f}")
    
    # 5. PIE DE PÁGINA
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, 60, "Precios sujetos a cambio sin previo aviso.")
    c.drawCentredString(width / 2, 50, "No se entregan vehículos sin liquidar el total de la reparación.")
    c.setFillColor(COLOR_ACENTO)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, 30, "¡GRACIAS POR SU PREFERENCIA!")

    c.save()
    return filename  # <--- ¡AQUÍ ESTÁ LA CLAVE!

# ==========================================
# 2. REPORTE FINANCIERO GLOBAL
# ==========================================
def generar_reporte_mensual(resumen, detalles, f_ini, f_fin):
    filename = f"Reporte_Financiero_{f_ini}_{f_fin}.pdf"
    c = canvas.Canvas(filename, pagesize=LETTER)
    width, height = LETTER
    
    COLOR_HEAD = colors.HexColor("#1e293b")
    
    # Encabezado
    c.setFillColor(COLOR_HEAD)
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(30, height - 50, "REPORTE FINANCIERO")
    c.setFont("Helvetica", 12)
    c.drawString(30, height - 70, f"Periodo: {f_ini} al {f_fin}")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 30, height - 50, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Resumen
    y_cards = height - 130
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y_cards, "TOTAL INGRESOS:")
    c.setFillColor(colors.green)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(150, y_cards, f"${resumen['total']:,.2f}")
    
    y_det = y_cards - 25
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    for m in resumen['desglose']:
        txt = f"- {m['metodo_pago']}: ${m['subtotal']:,.2f} ({m['cantidad_tickets']} ops)"
        c.drawString(30, y_det, txt)
        y_det -= 15

    # Tabla Detalle
    data = [['FECHA', 'TICKET', 'CLIENTE', 'VEHÍCULO', 'MÉTODO', 'MONTO']]
    for d in detalles:
        fecha = str(d.get('fecha_cierre', ''))[:10]
        ticket = f"#{d.get('id', 0)}"
        cliente = d.get('cliente', 'Mostrador') or 'Mostrador'
        if len(cliente) > 18: cliente = cliente[:18] + "..."
        auto = d.get('modelo', 'N/A')
        if len(auto) > 15: auto = auto[:15] + "..."
        metodo = d.get('metodo_pago', 'N/A')
        monto = f"${d.get('costo_final', 0):,.2f}"
        data.append([fecha, ticket, cliente, auto, metodo, monto])
        
    col_widths = [70, 50, 130, 110, 90, 80]
    tabla = Table(data, colWidths=col_widths)
    
    estilo = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_HEAD),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
    ])
    tabla.setStyle(estilo)
    
    w_tab, h_tab = tabla.wrap(width, height)
    if height - 250 - h_tab < 50:
        c.showPage()
        tabla.drawOn(c, 30, height - h_tab - 50)
    else:
        tabla.drawOn(c, 30, height - 250 - h_tab)
        
    c.save()
    return filename