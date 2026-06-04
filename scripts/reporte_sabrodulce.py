"""
reporte_sabrodulce.py — Historial completo de ventas de Sabro Dulce
"""
from modules.database import get_connection

conn = get_connection()

ventas = conn.execute("""
    SELECT
        v.id            as venta_id,
        DATE(v.created_at) as fecha,
        TIME(v.created_at) as hora,
        v.metodo_pago,
        COALESCE(u.nombre, 'Desconocido') as usuario,
        vd.nombre_producto as producto,
        vd.cantidad,
        vd.precio_unitario,
        vd.costo_unitario,
        vd.subtotal,
        CASE WHEN v.cancelada=1 THEN 'CANCELADA' ELSE 'OK' END as estado
    FROM venta_detalle vd
    JOIN ventas v ON v.id = vd.venta_id
    LEFT JOIN tiendas t ON t.id = vd.tienda_id
    LEFT JOIN usuarios u ON u.id = v.usuario_id
    WHERE LOWER(COALESCE(t.nombre,'')) LIKE '%sabro%'
    ORDER BY v.created_at
""").fetchall()

conn.close()

if not ventas:
    print("No hay ventas registradas de Sabro Dulce.")
else:
    # Header
    print(f"\n{'='*90}")
    print(f"  HISTORIAL DE VENTAS — SABRO DULCE  ({len(ventas)} registros)")
    print(f"{'='*100}")
    print(f"{'Fecha':<12} {'Hora':<8} {'Usuario':<12} {'Producto':<22} {'Cant':>4} {'Precio':>8} {'Costo':>8} {'Subtotal':>10} {'Método':<12} {'Estado'}")
    print(f"{'-'*100}")


    total_ventas = 0
    total_costo  = 0

    for r in ventas:
        print(
            f"{r['fecha']:<12} {r['hora']:<8} {r['usuario']:<12} {r['producto']:<22} "
            f"{r['cantidad']:>4} {r['precio_unitario']:>8.2f} {r['costo_unitario']:>8.2f} "
            f"{r['subtotal']:>10.2f} {r['metodo_pago']:<12} {r['estado']}"
        )
        if r['estado'] == 'OK':
            total_ventas += r['subtotal']
            total_costo  += r['cantidad'] * (r['costo_unitario'] or 0)

    print(f"{'='*100}")
    print(f"  TOTAL VENDIDO:  ${total_ventas:,.2f}")
    print(f"  TOTAL COSTO:    ${total_costo:,.2f}")
    print(f"  UTILIDAD EST.:  ${total_ventas - total_costo:,.2f}")
    print(f"{'='*90}\n")
