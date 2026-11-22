@echo off
rem Genera dist\BoletinInstitucional\BoletinInstitucional.exe para Windows.
cd /d "%~dp0"
if not exist .venv (
    echo Creando el entorno de Python...
    py -3 -m venv .venv || python -m venv .venv
)
echo Instalando dependencias (la primera vez tarda unos minutos)...
.venv\Scripts\python -m pip install --upgrade pip >nul
.venv\Scripts\python -m pip install -r requirements-compilar.txt || goto error
echo Compilando la aplicacion...
if exist build rmdir /s /q build
if exist dist\BoletinInstitucional rmdir /s /q dist\BoletinInstitucional
.venv\Scripts\pyinstaller --noconfirm --clean empaquetado\boletin.spec || goto error
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\BoletinInstitucional' -DestinationPath 'dist\Boletin_Institucional_Windows.zip'"
echo.
echo Listo: dist\BoletinInstitucional\BoletinInstitucional.exe
echo Para compartirla use dist\Boletin_Institucional_Windows.zip
explorer dist
pause
exit /b 0
:error
echo Ocurrio un error. Revise los mensajes anteriores.
pause
exit /b 1
