# 🖨️ Guía: Configurar la Impresora Térmica

## Problema
El servidor estaba silenciosamente fallando al conectarse a la impresora, por eso no imprimía nada.

## Solución fácil en 2 pasos:

### Paso 1: Identifica el nombre de tu impresora
Abre PowerShell y ejecuta:
```powershell
python C:\EstudioDeco\diagnostico_impresora.py
```

Verás algo como:
```
DIAGNÓSTICO DE IMPRESORAS - Estudio Deco POS
[1] Impresoras locales disponibles:
  1. POS-80 
  2. Brother HL-L2350DW
  3. PDF Printer
```

### Paso 2: Configura la impresora

**Opción A — Temporal (solo esta sesión):**
```powershell
cd C:\EstudioDeco
$env:ESTUDIO_PRINTER = 'TU-NOMBRE-IMPRESORA'  # Reemplaza con tu impresora
python server.py
```

**Opción B — Permanente (recomendado):**
```powershell
# Ejecuta esto una sola vez
[Environment]::SetEnvironmentVariable('ESTUDIO_PRINTER', 'TU-NOMBRE-IMPRESORA', 'User')

# Cierra y reabre PowerShell, luego:
cd C:\EstudioDeco
python server.py
```

## ¿Tienes una impresora térmica ESC/POS?

Si es marca **Epson TM-T20/T80/T88** o similar, el nombre debería ser algo como:
- `POS-80`
- `Thermal Printer`
- `EPSON TM-T20II`

Si es **otra marca**, verifica en:
- Panel de Control → Dispositivos e Impresoras
- O en PowerShell: `Get-Printer | Select-Object Name`

## Ahora verás en el terminal:

✓ Si **SÍ** hay impresora:
```
[PRINTER] Intentando conectar a: POS-80
[PRINTER] ✓ Conectado a POS-80
[PRINTER] ✓ Ticket 001 impreso
```

✗ Si **NO** hay impresora:
```
[PRINTER] ✗ Error conectando a 'POS-80': ...
[PRINTER] Impresoras disponibles:
  - Brother HL-L2350DW
  - PDF Printer
[PRINTER] ⚠ No hay impresora. Solo se mostrará preview.
```

En este caso, harás clic en **"Imprimir"** en el navegador para enviar a PDF o cambias la configuración.

---

**¿Necesitas ayuda?** Comparte el output del diagnóstico.
