from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from datetime import datetime, timedelta
import os

def generar_pdf_cotizacion(datos, dias_vigencia):
    """
    Genera un PDF elegante para TREGAL Tires.
    """
    # --- CORRECCIÓN AQUÍ: Usamos 'id' en lugar de 'servicio_id' ---
    filename = f"Cotizacion_{datos['id']}.pdf" 
    
    c = canvas.Canvas(filename, pagesize=LETTER)
    width, height = LETTER
    
    # --- COLORES DE MARCA (TREGAL TIRES) ---
    COLOR_PRIMARIO = colors.HexColor("#1e293b") # Azul oscuro
    COLOR_ACENTO = colors.HexColor("#ea580c")   # Naranja
    COLOR_GRIS = colors.HexColor("#64748b")
    
    # ==========================================
    # 1. ENCABEZADO
    # ==========================================
    
    # Franja lateral
    c.setFillColor(COLOR_PRIMARIO)
    c.rect(0, 0, 30, height, fill=1, stroke=0)
    
    # Logo / Nombre
    c.setFillColor(COLOR_PRIMARIO)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(50, height - 50, "TREGAL TIRES")
    
    c.setFillColor(COLOR_ACENTO)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 65, "ESPECIALISTAS AUTOMOTRICES")

    # Contacto
    c.setFillColor(COLOR_GRIS)
    c.setFont("Helvetica", 9)
    c.drawString(50, height - 85, "Dirección: Av. Industrias #123, San Luis Potosí")
    c.drawString(50, height - 97, "Tel: (444) 123-4567 | Email: contacto@tregaltires.com")

    # Título y Folio
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(width - 30, height - 50, "COTIZACIÓN")
    
    c.setFillColor(COLOR_ACENTO)
    c.setFont("Helvetica-Bold", 14)
    # --- CORRECCIÓN AQUÍ TAMBIÉN: 'id' ---
    c.drawRightString(width - 30, height - 70, f"#{datos['id']:04d}") 

    # ==========================================
    # 2. DATOS DEL CLIENTE Y FECHAS
    # ==========================================
    y_bloque = height - 140
    
    # Cliente
    c.setFillColor(COLOR_PRIMARIO)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_bloque, "CLIENTE:")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawString(50, y_bloque - 15, datos['cliente'])
    c.setFont("Helvetica", 9)
    # Manejo seguro si no hay teléfono
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
    c.drawString(250, y_bloque - 30, f"Placas: {datos['placas']}")
    c.drawString(250, y_bloque - 42, f"Color: {datos['color']}")

    # Fechas
    fecha_emision = datetime.now()
    fecha_vence = fecha_emision + timedelta(days=dias_vigencia)
    
    c.setFillColor(COLOR_PRIMARIO)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 30, y_bloque, "FECHA EMISIÓN:")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 30, y_bloque - 15, fecha_emision.strftime("%d/%m/%Y"))
    
    c.setFillColor(colors.red)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 30, y_bloque - 35, "VIGENCIA:")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 30, y_bloque - 50, fecha_vence.strftime("%d/%m/%Y"))

    # Línea divisoria
    c.setStrokeColor(colors.lightgrey)
    c.line(50, y_bloque - 60, width - 30, y_bloque - 60)

    # ==========================================
    # 3. TABLA DE PRODUCTOS
    # ==========================================
    
    data_tabla = [['CANT', 'DESCRIPCIÓN / SERVICIO', 'TIPO', 'P. UNIT', 'TOTAL']]
    total_general = 0
    
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
    
    # Estilo Tabla
    # Ajustamos altura dinámica si hay muchos items
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
    
    # ==========================================
    # 4. TOTALES
    # ==========================================
    y_totales = height - 250 - h_tab
    
    c.setFillColor(COLOR_PRIMARIO)
    c.rect(width - 200, y_totales - 40, 170, 40, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width - 190, y_totales - 25, "TOTAL:")
    c.drawRightString(width - 40, y_totales - 25, f"${total_general:,.2f}")
    
    # ==========================================
    # 5. PIE DE PÁGINA
    # ==========================================
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, 60, "Precios sujetos a cambio sin previo aviso.")
    c.drawCentredString(width / 2, 50, "No se entregan vehículos sin liquidar el total de la reparación.")
    
    c.setFillColor(COLOR_ACENTO)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, 30, "¡GRACIAS POR SU PREFERENCIA!")

    c.save()
    return filename