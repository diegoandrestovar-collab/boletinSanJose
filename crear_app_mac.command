#!/bin/bash
# Genera "Boletín Institucional.app" para macOS (queda en la carpeta dist).
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    osascript -e 'display alert "Falta Python 3" message "Instale Python desde https://www.python.org/downloads/ y vuelva a abrir este archivo."'
    exit 1
fi

if [ ! -d .venv ]; then
    echo "Creando el entorno de Python..."
    python3 -m venv .venv || exit 1
fi
echo "Instalando dependencias (la primera vez tarda unos minutos)..."
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements-compilar.txt || { read -r -p "Error al instalar. Presione Enter para cerrar"; exit 1; }

echo "Compilando la aplicación..."
rm -rf build "dist/Boletín Institucional.app"
.venv/bin/pyinstaller --noconfirm --clean empaquetado/boletin.spec || { read -r -p "Error al compilar. Presione Enter para cerrar"; exit 1; }

# Copia lista para compartir: un .zip que conserva la estructura del .app
cd dist && rm -f "Boletin_Institucional_macOS.zip"
ditto -c -k --keepParent "Boletín Institucional.app" "Boletin_Institucional_macOS.zip"
cd ..

echo ""
echo "Listo. La aplicación está en: dist/Boletín Institucional.app"
echo "Arrástrela a la carpeta Aplicaciones. Para compartirla use dist/Boletin_Institucional_macOS.zip"
open dist
read -r -p "Presione Enter para cerrar"
