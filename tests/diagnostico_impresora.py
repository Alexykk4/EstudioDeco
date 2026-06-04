"""
Diagnóstico de impresoras disponibles en el sistema
"""
import subprocess
import sys

print("=" * 60)
print("DIAGNÓSTICO DE IMPRESORAS - Estudio Deco POS")
print("=" * 60)

# 1. Listar impresoras con PowerShell
print("\n[1] Impresoras locales disponibles:")
print("-" * 60)
try:
    result = subprocess.run(
        ["powershell", "-Command", "Get-Printer | Select-Object -ExpandProperty Name"],
        capture_output=True, text=True, timeout=5
    )
    impresoras = [p.strip() for p in result.stdout.split('\n') if p.strip()]
    if impresoras:
        for i, p in enumerate(impresoras, 1):
            print(f"  {i}. {p}")
    else:
        print("  ❌ No se encontraron impresoras")
except Exception as e:
    print(f"  ❌ Error: {e}")

# 2. Impresora por defecto
print("\n[2] Impresora por defecto del sistema:")
print("-" * 60)
try:
    result = subprocess.run(
        ["powershell", "-Command", "Get-Printer -Default | Select-Object -ExpandProperty Name"],
        capture_output=True, text=True, timeout=5
    )
    default = result.stdout.strip()
    if default:
        print(f"  ✓ {default}")
    else:
        print("  ⚠ No hay impresora por defecto configurada")
except Exception as e:
    print(f"  ❌ Error: {e}")

# 3. Variables de entorno
print("\n[3] Variable de entorno ESTUDIO_PRINTER:")
print("-" * 60)
printer_name = subprocess.os.environ.get("ESTUDIO_PRINTER", "no configurada")
print(f"  {printer_name}")

# 4. Instrucciones
print("\n[4] CÓMO CONFIGURAR:")
print("-" * 60)
print("  Windows PowerShell (Opción A - Temporal):")
print("    $env:ESTUDIO_PRINTER='TU-NOMBRE-IMPRESORA'")
print("    python server.py")
print()
print("  Windows PowerShell (Opción B - Permanente):")
print("    [Environment]::SetEnvironmentVariable('ESTUDIO_PRINTER','TU-NOMBRE-IMPRESORA','User')")
print()
print("  Luego reinicia la terminal.")
print()
print("=" * 60)
