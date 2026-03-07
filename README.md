# Estudio Deco POS — Web Edition

## Instalación rápida (Windows)

```powershell
# 1. Abre PowerShell y ve a la carpeta
cd C:\EstudioDecoPOS

# 2. Instala dependencias
pip install -r requirements.txt

# 3. Inicializa la base de datos con productos de prueba
python -c "from modules.database import init_db; init_db(); print('BD lista')"

# 4. Ejecuta el servidor
python server.py
```

## Abre en el navegador: http://localhost:8000

## NIP por defecto: 1234 (Admin)

## Compartir por Tailscale
Otros dispositivos en tu red Tailscale pueden acceder con:
http://TU-IP-TAILSCALE:8000
