"""
Diagnóstico detallado de impresión
"""
import sys
import os

# Asegúrate de que estamos en la carpeta correcta
sys.path.insert(0, str(os.path.dirname(__file__)))

print("=" * 60)
print("DIAGNÓSTICO DETALLADO DE IMPRESIÓN")
print("=" * 60)

# 1. Verificar variable de entorno
print("\n[1] Variable ESTUDIO_PRINTER:")
printer_name = os.environ.get("ESTUDIO_PRINTER", "NO CONFIGURADA")
print(f"    {printer_name}")

# 2. Intentar importar escpos
print("\n[2] ¿Está instalado escpos?")
try:
    from escpos.printer import Win32Raw
    print("    ✓ escpos importado correctamente")
except ImportError as e:
    print(f"    ✗ ERROR: {e}")
    sys.exit(1)

# 3. Intentar conectar a impresora
print("\n[3] Intentando conectar a impresora...")
try:
    if printer_name == "NO CONFIGURADA":
        print(f"    ADVERTENCIA: ESTUDIO_PRINTER no está configurada")
        printer_name = "POS-80"
        print(f"    Intentando con: {printer_name}")
    
    p = Win32Raw(printer_name, profile="TM-P80")
    print(f"    ✓ Conectado a: {printer_name}")
    
    # 4. Intentar escribir algo simple
    print("\n[4] Enviando texto de prueba...")
    p.text("PRUEBA CONEXION\n")
    p.text("Si ves esto, la impresora funciona!\n\n")
    p.cut()
    p.close()
    print("    ✓ Texto enviado exitosamente")
    
except Exception as e:
    print(f"    ✗ Error: {e}")
    print(f"    Tipo de error: {type(e).__name__}")
    import traceback
    print("\nTraceback completo:")
    traceback.print_exc()

print("\n" + "=" * 60)
