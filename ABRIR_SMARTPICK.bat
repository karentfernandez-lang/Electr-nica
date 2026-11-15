@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo No se pudo iniciar Python. Instala Python 3 y volve a intentar.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -c "import streamlit, serial; assert hasattr(streamlit, 'fragment')"
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo No se pudieron instalar las dependencias. Revisa la conexion a internet.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
pause
