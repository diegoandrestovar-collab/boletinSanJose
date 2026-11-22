@echo off
rem Genera dist\BoletinInstitucional\BoletinInstitucional.exe (no requiere Python en el equipo destino).
cd /d "%~dp0"
if not exist .venv call ejecutar.bat
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\pyinstaller --noconfirm --windowed --name BoletinInstitucional ^
    --add-data "boletin\recursos;boletin\recursos" main.py
echo.
echo Listo: copie la carpeta dist\BoletinInstitucional completa al equipo donde se usara.
pause
