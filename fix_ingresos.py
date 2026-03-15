"""Borrar ingresos y gastos extra de hoy"""
from modules.database import get_connection

conn = get_connection()

# Borrar ingresos duplicados (dejar solo ID 3 y 4)
conn.execute("DELETE FROM ingresos WHERE id IN (5, 6, 7)")
print("Eliminados ingresos ID 5, 6, 7")

# Borrar gasto "Fondo" $17,391
conn.execute("DELETE FROM gastos WHERE id = 37")
print("Eliminado gasto ID 37 (Fondo $17,391)")

conn.commit()

# Verificar
rows = conn.execute(
    "SELECT id, concepto, monto, metodo_pago FROM ingresos WHERE DATE(created_at) = DATE('now','localtime')"
).fetchall()
print("\n=== INGRESOS RESTANTES HOY ===")
for r in rows:
    print(f"  ID:{r['id']} | {r['concepto']} | ${r['monto']} | {r['metodo_pago']}")

gastos = conn.execute(
    "SELECT id, concepto, monto, origen FROM gastos WHERE DATE(created_at) = DATE('now','localtime')"
).fetchall()
print("\n=== GASTOS RESTANTES HOY ===")
for g in gastos:
    print(f"  ID:{g['id']} | {g['concepto']} | ${g['monto']} | {g['origen']}")

conn.close()
print("\n✅ Listo")
