"""Detalle de ventas por dia con items"""
from modules.database import get_connection
conn = get_connection()

dias = conn.execute("""
    SELECT DATE(created_at) as fecha, 
           COUNT(*) as n, 
           COALESCE(SUM(total),0) as t,
           COALESCE(SUM(monto_efectivo),0) as ef,
           COALESCE(SUM(monto_tarjeta),0) as tar
    FROM ventas 
    WHERE (cancelada IS NULL OR cancelada=0)
    GROUP BY DATE(created_at) ORDER BY fecha
""").fetchall()

print("=== VENTAS POR DIA ===")
for d in dias:
    print(f"\n--- {d['fecha']} --- ({d['n']} ventas) Total: ${d['t']:,.2f} (Ef: ${d['ef']:,.2f} / Tar: ${d['tar']:,.2f})")
    ventas = conn.execute("""
        SELECT v.folio, v.total, v.metodo_pago, v.monto_efectivo, v.monto_tarjeta, v.created_at,
               GROUP_CONCAT(vd.nombre_producto || ' x' || vd.cantidad, ', ') as items
        FROM ventas v
        LEFT JOIN venta_detalle vd ON vd.venta_id = v.id
        WHERE DATE(v.created_at) = ? AND (v.cancelada IS NULL OR v.cancelada=0)
        GROUP BY v.id
        ORDER BY v.created_at
    """, (d['fecha'],)).fetchall()
    for v in ventas:
        hora = v['created_at'][11:16] if v['created_at'] else ''
        print(f"  {hora} | {v['folio'][-8:]} | ${v['total']:,.2f} | {v['metodo_pago']} | {v['items'] or '-'}")

conn.close()
