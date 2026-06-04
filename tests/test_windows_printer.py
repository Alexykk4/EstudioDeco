"""
Test simple de impresión a través de Windows
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.printer import imprimir_ticket

# Datos de prueba
venta_prueba = {
    'folio': 'TEST-001',
    'fecha': '2026-03-06 14:30:00',
    'total': 150.00,
    'metodo_pago': 'Efectivo',
    'items': [
        {'nombre': 'Café', 'cantidad': 2, 'precio_unitario': 25.00},
        {'nombre': 'Pastel', 'cantidad': 1, 'precio_unitario': 100.00}
    ]
}

print("=" * 60)
print("TEST DE IMPRESIÓN")
print("=" * 60)
print(f"\nIntentando imprimir en: POS-80")
print(f"Folio: {venta_prueba['folio']}")
print(f"Total: ${venta_prueba['total']}\n")

# show the actual ticket text for debugging
print("\n--- TEXTO DEL TICKET ---")
from modules.printer import preview_ticket_text
print(preview_ticket_text(venta_prueba, "Test Cajero"))
print("--- FIN TEXTO ---\n")

resultado = imprimir_ticket(venta_prueba, "Test Cajero")

if resultado:
    print("\n✅ Ticket enviado exitosamente!")
    print("Verifica que el papel salió de la impresora.")
else:
    print("\n❌ Hubo un problema enviando el ticket.")

print("\n" + "=" * 60)
