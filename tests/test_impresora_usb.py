"""
Test seguro de conectividad con impresora USB
SIN comandos peligrosos (sin cut, sin cashdraw, etc)
"""
import sys
from pathlib import Path

# Agregar módulos al path
sys.path.insert(0, str(Path(__file__).parent))

from modules.printer import _conectar, _detectar_impresora_usb

print("=" * 60)
print("TEST SEGURO - Impresora USB")
print("=" * 60)

# Paso 1: Detectar
print("\n[1] Detectando impresora USB...")
device = _detectar_impresora_usb()

if not device:
    print("❌ No se encontró impresora USB")
    sys.exit(1)

# Paso 2: Conectar
print("\n[2] Conectando...")
printer = _conectar()

if not printer:
    print("❌ No se pudo conectar")
    sys.exit(1)

# Paso 3: Probar escritura segura
print("\n[3] Enviando texto de prueba (SIN cut ni cashdraw)...")
try:
    printer.set(align="center", bold=True)
    printer.text("TEST DE IMPRESORA\n")
    printer.text("Fecha: 2025-01-01\n")
    printer.text("Si ves esto, funciona!\n\n")
    printer.set(align="left", bold=False)
    printer.text("* Sin comandos peligrosos\n")
    printer.text("* Impresión segura\n\n")
    printer.close()
    
    print("✅ Prueba exitosa!")
    print("\nPróximos pasos:")
    print("1. Verifica que el papel salió de la impresora")
    print("2. La impresora está lista para usar")
    print("3. Lanza el servidor: python server.py")
    
except Exception as e:
    print(f"❌ Error durante prueba: {e}")
    try:
        printer.close()
    except:
        pass
    sys.exit(1)
