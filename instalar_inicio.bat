@echo off
title Instalar inicio automatico — Estudio Deco POS

REM ─── Ruta a la carpeta de inicio de Windows ───────────────────────────────
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM ─── Crea el lanzador en inicio ──────────────────────────────────────────
set "DESTINO=%STARTUP%\EstudioDecoPOS_Server.bat"

echo.
echo  Instalando inicio automatico del servidor POS...
echo  Destino: %DESTINO%
echo.

(
echo @echo off
echo cd /d "%~dp0"
echo call start_server.bat
) > "%DESTINO%"

if exist "%DESTINO%" (
    echo  [OK] El servidor arrancara automaticamente al iniciar Windows.
    echo       Puedes probarlo ahora reiniciando la laptop o ejecutando:
    echo       "%DESTINO%"
) else (
    echo  [ERROR] No se pudo crear el archivo.
    echo          Intenta ejecutar este script como Administrador.
)

echo.
pause
