@echo off
title Estudio Deco POS — Servidor
cd /d "%~dp0"

echo.
echo  ========================================
echo    Estudio Deco POS v2  -  Servidor
echo    http://localhost:8001
echo  ========================================
echo.

REM Activa el entorno virtual
call "%~dp0venv\Scripts\activate.bat"

REM Inicia el servidor (se mantiene visible para ver errores)
python server.py

REM Si el servidor se cierra inesperadamente, el script simplemente se detendrá.
echo.
echo  [!] El servidor se detuvo o encontro un error.
pause
