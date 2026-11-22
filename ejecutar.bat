@echo off
rem Abre el editor del Boletin Institucional (crea el entorno la primera vez).
cd /d "%~dp0"
if not exist .venv (
    echo Preparando el entorno por primera vez, espere un momento...
    py -3 -m venv .venv || python -m venv .venv
    .venv\Scripts\python -m pip install --upgrade pip
    .venv\Scripts\python -m pip install -r requirements.txt
)
start "" .venv\Scripts\pythonw main.py %*
