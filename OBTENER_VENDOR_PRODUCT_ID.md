# 📋 Cómo obtener el Vendor ID y Product ID de tu impresora

## Método 1: Administrador de dispositivos (Windows) - MÁS FÁCIL

1. Abre **Administrador de dispositivos** (tecla Windows + X → Administrador de dispositivos)
2. Busca **"Impresoras"** o **"Puertos COM/LPT"**
3. Haz clic derecho en tu impresora **POS-80** → **Propiedades**
4. Ve a la pestaña **Detalles**
5. En el dropdown **"Propiedad"**, selectiona **"Identificador de hardware"**
6. Verás algo como:

```
USB\VID_04B8&PID_0202\...
```

Donde:
- `VID_` = Vendor ID (en hexadecimal) → aquí `04B8`
- `PID_` = Product ID (en hexadecimal) → aquí `0202`

## Método 2: PowerShell

```powershell
Get-PnpDevice -Class Printers | Where-Object {$_.Name -match "POS"} | Get-PnpDeviceProperty -KeyName "DEVPKEY_Device_HardwareIds"
```

Busca en la salida el patrón: `USB\VID_XXXX&PID_XXXX\...`

## Método 3: Online

Si conoces la marca, busca en Google:
- "POS-80 thermal printer vendor id product id"
- O la marca + "USB vendor id"

## Una vez que tengas los IDs:

```powershell
$env:ESTUDIO_PRINTER_TYPE = 'usb'
$env:ESTUDIO_PRINTER_VENDOR = '0x04B8'    # Reemplaza con tu VID
$env:ESTUDIO_PRINTER_PRODUCT = '0x0202'   # Reemplaza con tu PID
python server.py
```

---
**¿Pudiste encontrar el VID y PID?**
