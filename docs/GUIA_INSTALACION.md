# 🏪 Estudio Deco POS — Guía de Instalación desde Cero

> Esta guía asume una laptop Windows nueva que no tiene nada instalado.

---

## PASO 1 — Instalar Python

1. Ve a [python.org/downloads](https://www.python.org/downloads/)
2. Descarga la última versión de **Python 3.11** o superior
3. Al instalar, **marca la casilla** ✅ `Add Python to PATH` (MUY IMPORTANTE)
4. Clic en **Install Now**
5. Verifica que quedó bien. Abre **PowerShell** y ejecuta:
   ```powershell
   python --version
   ```
   Debe mostrar algo como `Python 3.11.x`

---

## PASO 2 — Copiar el proyecto

Copia toda la carpeta `EstudioDeco` a la raíz del disco C:, de modo que quede en:
```
C:\EstudioDeco\
```

La estructura del proyecto es:
```
C:\EstudioDeco\
├── assets/
│   ├── logo.png                 ← Logo que aparece en tickets
│   └── credentials.json         ← Credenciales Google (paso 7)
├── modules/
│   ├── database.py              ← Lógica de base de datos SQLite
│   ├── printer.py               ← Impresión ESC/POS de tickets
│   ├── pdf_report.py            ← Generación de PDFs de corte
│   └── sync_sheets.py           ← Sincronización a Google Sheets
├── static/
│   └── index.html               ← Interfaz web del punto de venta
├── reports/                     ← Aquí se guardan los PDFs de corte
├── schema.sql                   ← Esquema de la base de datos
├── server.py                    ← Servidor web (lo que ejecutas)
├── requirements.txt             ← Dependencias de Python
└── pos_estudio_deco.db          ← Se crea automáticamente
```

---

## PASO 3 — Crear el entorno virtual e instalar dependencias

Abre **PowerShell** y ejecuta esto línea por línea:

```powershell
# 3.1 — Ir a la carpeta del proyecto
cd C:\EstudioDeco

# 3.2 — Crear un entorno virtual
python -m venv venv

# 3.3 — Activar el entorno virtual
.\venv\Scripts\Activate

# 3.4 — Instalar todas las dependencias
pip install -r requirements.txt
```

> ⚠️ **Cada vez que abras una terminal nueva**, debes activar el entorno antes de arrancar el servidor:
> ```powershell
> cd C:\EstudioDeco
> .\venv\Scripts\Activate
> ```

---

## PASO 4 — Arrancar el servidor por primera vez

Con el entorno virtual activado:

```powershell
python server.py
```

Verás en la terminal:
```
  * Estudio Deco POS *
  http://localhost:8001

INFO:     Uvicorn running on http://0.0.0.0:8001
```

Ahora abre el navegador (Chrome o Edge) y ve a:
```
http://localhost:8001
```

¡Listo! Ya tienes el punto de venta funcionando. 🎉

La base de datos (`pos_estudio_deco.db`) se crea automáticamente con productos de prueba incluidos.

---

## PASO 5 — Usuarios y NIP

El sistema viene con un usuario por defecto:

| Usuario | Perfil        | NIP  |
|---------|---------------|------|
| Admin   | Administrador | 1234 |

### Para agregar más cajeros:

Con el entorno activado, ejecuta:
```powershell
python -c "from modules.database import crear_usuario; crear_usuario('María','Cajero','5678'); print('Usuario creado')"
```

Cambia `María` por el nombre y `5678` por el NIP de 4 dígitos que quieras.

### Perfiles disponibles:
- **Administrador** — Puede hacer corte de caja y ver el catálogo
- **Cajero** — Solo puede vender y registrar gastos

---

## PASO 6 — Configurar la impresora térmica

### 6.1 Instalar el driver de la impresora
Conecta la impresora por USB. Windows normalmente la detecta automáticamente. Si no, instala el driver que viene con la impresora (CD o sitio web del fabricante).

### 6.2 Identificar el nombre de la impresora
En PowerShell:
```powershell
python C:\EstudioDeco\diagnostico_impresora.py
```

Verás algo como:
```
IMPRESORAS DISPONIBLES:
  1. POS-80
  2. Microsoft Print to PDF
  3. Brother HL-L2350DW
```

Anota el nombre exacto de tu impresora térmica (ej: `POS-80`).

### 6.3 Configurar el nombre (permanente)

En PowerShell:
```powershell
[Environment]::SetEnvironmentVariable('ESTUDIO_PRINTER', 'POS-80', 'User')
```

Reemplaza `POS-80` con el nombre real de TU impresora. **Cierra y reabre PowerShell** para que tome efecto.

### 6.4 Verificar

Arranca el servidor y haz una venta de prueba. En la terminal debe aparecer:
```
[PRINTER] OK — folio VTA-20260307-0001
```

Si dice `SIN IMPRESORA`, revisa que el nombre sea exacto (mayúsculas/minúsculas importan).

> 💡 **Sin impresora conectada** el sistema funciona igual, solo no imprime. No se traba ni da error.

---

## PASO 7 — Google Sheets (OPCIONAL — sincronización en la nube)

Si quieres que las ventas se suban automáticamente a Google Sheets:

### 7.1 Crear un Service Account en Google Cloud
1. Ve a [console.cloud.google.com](https://console.cloud.google.com/)
2. Crea un proyecto nuevo (o usa uno existente)
3. Habilita la **Google Sheets API** y **Google Drive API**
4. Ve a **Credenciales** → **Crear credenciales** → **Cuenta de servicio**
5. Descarga el archivo JSON de credenciales

### 7.2 Colocar las credenciales
Copia el archivo JSON descargado a:
```
C:\EstudioDeco\assets\credentials.json
```

### 7.3 Crear la hoja de cálculo
1. Ve a [sheets.google.com](https://sheets.google.com) y crea una hoja nueva
2. Copia el **ID** de la URL: `https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit`
3. Comparte la hoja con el correo del Service Account (está en el JSON como `client_email`)

### 7.4 Guardar el ID en el sistema
Con el entorno activado:
```powershell
python -c "from modules.database import get_connection; c=get_connection(); c.execute(\"UPDATE config SET valor='TU_SPREADSHEET_ID' WHERE clave='sheets_id'\"); c.commit(); c.close(); print('OK')"
```

> Si no configuras Google Sheets, el sistema funciona al 100% en modo offline. Solo no sincroniza.

---

## PASO 8 — Personalización

### Logo del ticket
Reemplaza el archivo `C:\EstudioDeco\assets\logo.png` con tu logo.
- Formato: PNG
- Fondo blanco o transparente
- Tamaño recomendado: 384px de ancho (el máximo que imprime la térmica)

### Slogan y mensajes del ticket
Edita `C:\EstudioDeco\modules\printer.py`:

```python
# Línea 16 — Slogan debajo del logo:
SLOGAN = "Crea y decora en Estudio Deco"

# Línea 18 — Mensajes rotativos al pie del ticket:
_MENSAJES_PIE = [
    "Hecho con amor en Estudio Deco",
    "Tu creatividad nos inspira",
    ...
]
```

### Instagram QR
El ticket imprime un QR que lleva a `@estudiodecomx`. Para cambiar la URL, busca en `printer.py`:
```python
qr = _qr_escpos("https://instagram.com/estudiodecomx", max_w=180)
```

---

## PASO 9 — Uso diario

### Abrir el punto de venta
```powershell
cd C:\EstudioDeco
.\venv\Scripts\Activate
python server.py
```
Luego abre `http://localhost:8001` en el navegador.

### Flujo de trabajo
1. **Ingresar NIP** — 🔑 Con el botón de arriba a la derecha
2. **Seleccionar mesa** — Clic en una mesa disponible
3. **Agregar productos** — Clic en los productos de las pestañas
4. **Cobrar** — Seleccionar forma de pago y presionar Cobrar
5. **Corte de caja** — 📊 Solo Administrador, al final del turno

### Formas de pago
- 💵 **Efectivo**
- 💳 **Tarjeta** (se registra automáticamente 4% de comisión)
- 📱 **Transferencia**
- ⚖️ **Mixto** (parte efectivo, parte tarjeta)

---

## PASO 10 — Respaldos

### Respaldar la base de datos
Copia este archivo a un USB o nube cada cierto tiempo:
```
C:\EstudioDeco\pos_estudio_deco.db
```

### Restaurar un respaldo
Solo reemplaza el archivo `.db` y reinicia el servidor.

---

## Solución de Problemas

### "python no se reconoce como comando"
→ Python no está en el PATH. Desinstala Python y vuelve a instalarlo marcando ✅ `Add Python to PATH`.

### "El puerto 8001 ya está en uso"
→ Ya hay un servidor corriendo. Cierra la otra terminal o ejecuta:
```powershell
Get-Process python | Stop-Process -Force
```

### "La impresora no imprime"
→ Verifica el nombre con `diagnostico_impresora.py` y que la variable `ESTUDIO_PRINTER` esté configurada.

### "No se conecta desde otro dispositivo"
→ El firewall de Windows puede estar bloqueando. Abre el puerto 8001:
```powershell
# Ejecutar como Administrador:
New-NetFirewallRule -DisplayName "Estudio Deco POS" -Direction Inbound -Port 8001 -Protocol TCP -Action Allow
```
Luego accede desde otro dispositivo usando la IP de la computadora: `http://192.168.x.x:8001`

### "Error al instalar pywin32"
→ Asegúrate de estar usando el entorno virtual y ejecuta:
```powershell
pip install pywin32
python -c "import win32print; print('OK')"
```

---

## Comandos Rápidos

```powershell
# Iniciar el servidor
cd C:\EstudioDeco; .\venv\Scripts\Activate; python server.py

# Ver impresoras disponibles
python C:\EstudioDeco\diagnostico_impresora.py

# Crear usuario nuevo
python -c "from modules.database import crear_usuario; crear_usuario('Nombre','Cajero','1234')"

# Ver ventas del día
python -c "from modules.database import get_connection; c=get_connection(); [print(dict(r)) for r in c.execute('SELECT folio,total,created_at FROM ventas WHERE DATE(created_at)=DATE(\"now\",\"localtime\")')]; c.close()"
```
