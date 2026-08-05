@echo off
chcp 65001 >nul
title Estudio Deco — Actualizar rama deco
cd /d "%~dp0"

echo.
echo  ========================================
echo    Actualizar Estudio Deco (rama deco)
echo  ========================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo  [ERROR] Git no esta instalado o no esta en el PATH.
  echo  Instala Git y vuelve a intentar.
  echo.
  pause
  exit /b 1
)

echo  [1/3] Descargando cambios de GitHub...
git fetch origin deco
if errorlevel 1 (
  echo.
  echo  [ERROR] No se pudo conectar con GitHub / origin.
  echo.
  pause
  exit /b 1
)

echo  [2/3] Cambiando a la rama deco...
git checkout deco
if errorlevel 1 (
  echo.
  echo  [!] No existia deco local. Creando desde origin/deco...
  git checkout -b deco origin/deco
  if errorlevel 1 (
    echo  [ERROR] No se pudo cambiar a deco.
    echo.
    pause
    exit /b 1
  )
)

echo  [3/3] Aplicando actualizaciones (git pull)...
git pull origin deco
if errorlevel 1 (
  echo.
  echo  [ERROR] git pull fallo. Puede haber cambios locales en conflicto.
  echo  Revisa el mensaje de arriba.
  echo.
  pause
  exit /b 1
)

echo.
echo  ========================================
echo    Listo. Rama deco actualizada.
echo  ========================================
echo.
git log -1 --format="  Ultimo commit: %%h — %%s%%n  Fecha: %%ci"
echo.
pause
