# Archivo: main.py
from nicegui import ui
from multiprocessing import freeze_support
from Db import database as db
import interfaz  # <--- Importamos el archivo que acabamos de crear

if __name__ in {"__main__", "__mp_main__"}:
    freeze_support()
    
    # 1. Inicializar DB
    db.init_db()
    
    # 2. Cargar la interfaz
    interfaz.crear_paginas()
    
    # 3. Arrancar (IMPORTANTE: storage_secret ayuda a evitar lecturas de archivo)
    ui.run(
        title='TREGAL Tires System',
        native=True,
        window_size=(1280, 800),
        reload=False,
        show=False,
        language='es',
        storage_secret='tregal_secret_key_2025' # <--- Agrega esto por seguridad
    )