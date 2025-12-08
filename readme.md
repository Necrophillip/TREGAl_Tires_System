# 🚗 TREGAL Tires System (v1.0)

Sistema de gestión integral (ERP) diseñado a medida para el taller automotriz **TREGAL Tires**. Desarrollado en Python con una arquitectura ligera y despliegue local.

## 📋 Características Principales

* **Dashboard en Tiempo Real:** Visualización de ingresos, autos en patio y alertas de stock con actualización automática.
* **Gestión de Órdenes de Servicio:**
    * Control de estatus (Pendiente, En Proceso, Terminado/Pagado).
    * Asignación de Mano de Obra y Comisiones.
    * Consumo de Refacciones directo del almacén.
* **Generador de Cotizaciones PDF:** Creación de documentos profesionales con vigencia configurable y diseño de marca.
* **Inventario Inteligente:**
    * Control de existencias.
    * Alertas configurables de stock bajo.
    * Cálculo automático de precios.
* **Recursos Humanos:**
    * Gestión de mecánicos.
    * Cálculo automático de nómina basada en comisiones.
* **Base de Datos Local:** Persistencia robusta usando SQLite.

## 🛠 Tecnologías Utilizadas

* **Lenguaje:** Python 3.10+
* **Frontend/UI:** NiceGUI (basado en Quasar/Vue)
* **Base de Datos:** SQLite3
* **Reportes:** ReportLab (Generación de PDF píxel-perfect)
* **Empaquetado:** PyInstaller / PyWebView

## 🚀 Instalación y Uso

### Requisitos Previos
Tener Python 3 instalado en el sistema.

### Instalación
1. Clonar el repositorio:
   ```bash
   git clone [https://github.com/Necrophillip/TREGAl_Tires_System.git](https://github.com/Necrophillip/TREGAl_Tires_System.git)