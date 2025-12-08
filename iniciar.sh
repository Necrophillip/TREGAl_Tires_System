#!/bin/bash

# Obtener la ruta real de la carpeta donde está este script
# (Esto evita errores si lo ejecutas desde otro lado)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "🔧 Verificando sistema..."

# 1. Verificar si existe la carpeta 'venv'. Si no, la crea.
if [ ! -d "venv" ]; then
    echo "🚀 Creando entorno virtual por primera vez..."
    python3 -m venv venv
    
    echo "📦 Instalando librerías..."
    ./venv/bin/pip install -r requirements.txt
else
    echo "✅ Entorno virtual detectado."
fi

# (Opcional) Verificar si hay dependencias nuevas rápidamente
# ./venv/bin/pip install -r requirements.txt --quiet

# 2. Ejecutar la aplicación usando el Python DEL entorno virtual
# Nota: No hace falta hacer "activate". Si llamamos al python dentro de /bin,
# ya sabe que debe usar esas librerías.
echo "🏁 Iniciando Taller Dashboard..."
./venv/bin/python main.py