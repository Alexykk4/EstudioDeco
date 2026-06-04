"""
Detecta todas las impresoras USB y sus identificadores
"""
import sys

try:
    import usb.core
    import usb.util
    import usb.backend.libusb1
    
    print("=" * 70)
    print("DISPOSITIVOS USB CONECTADOS")
    print("=" * 70)
    
    # Obtener backend
    backend = usb.backend.libusb1.get_backend()
    
    # Listar todos los dispositivos USB
    devices = usb.core.find(find_all=True)
    
    found_any = False
    for device in devices:
        found_any = True
        vendor_id = device.idVendor
        product_id = device.idProduct
        
        # Intentar obtener descripción
        try:
            manufacturer = usb.util.get_string(device, device.iManufacturer)
        except:
            manufacturer = "Desconocido"
        
        try:
            product = usb.util.get_string(device, device.iProduct)
        except:
            product = "Desconocido"
        
        print(f"\nDispositivo encontrado:")
        print(f"  Vendor ID:  0x{vendor_id:04x} ({vendor_id})")
        print(f"  Product ID: 0x{product_id:04x} ({product_id})")
        print(f"  Fabricante: {manufacturer}")
        print(f"  Producto:   {product}")
        print(f"  Bus/Device: {device.bus}/{device.address}")
        
        # Si parece ser impresora térmica
        if "pos" in product.lower() or "thermal" in product.lower() or "printer" in product.lower():
            print(f"  ⭐ POSIBLE IMPRESORA POS-80")
    
    if not found_any:
        print("\nNo se encontraron dispositivos USB")
    
    print("\n" + "=" * 70)
    print("Para usar la impresora, necesitamos el Vendor ID y Product ID arriba ⬆️")
    
except ImportError:
    print("❌ Error: pyusb no está instalado")
    print("\nOpciones alternativas:")
    print("\n1. Especifica manualmente el puerto:")
    print("   Si ves 'USB 001', prueba:")
    print("   - Puerto directo: /dev/usb/lp0 (Linux)")
    print("   - LPT1 o COM1 (Windows, si está mapeado)")
    print("\n2. O proporciona el Vendor ID y Product ID")
