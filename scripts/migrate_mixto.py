import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "pos_estudio_deco.db"

def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("Inicio de la migración para método de pago Mixto...")

    # Verificar si las columnas ya existen
    cur.execute("PRAGMA table_info(ventas)")
    columns = [row["name"] for row in cur.fetchall()]

    if "monto_efectivo" not in columns:
        print("Agregando columna monto_efectivo...")
        cur.execute("ALTER TABLE ventas ADD COLUMN monto_efectivo REAL NOT NULL DEFAULT 0.0;")
    else:
        print("La columna monto_efectivo ya existe.")

    if "monto_tarjeta" not in columns:
        print("Agregando columna monto_tarjeta...")
        cur.execute("ALTER TABLE ventas ADD COLUMN monto_tarjeta REAL NOT NULL DEFAULT 0.0;")
    else:
        print("La columna monto_tarjeta ya existe.")

    # Actualizar los datos existentes (ventas viejas) para que el corte histórico siga cuadrando.
    # Si la venta fue en Efectivo, todo va a monto_efectivo.
    # Si fue Tarjeta o Transferencia, todo va a monto_tarjeta.
    print("Migrando datos históricos de ventas...")
    cur.execute("UPDATE ventas SET monto_efectivo = total, monto_tarjeta = 0.0 WHERE metodo_pago = 'Efectivo' AND monto_efectivo = 0.0 AND monto_tarjeta = 0.0;")
    cur.execute("UPDATE ventas SET monto_efectivo = 0.0, monto_tarjeta = total WHERE metodo_pago IN ('Tarjeta', 'Transferencia') AND monto_efectivo = 0.0 AND monto_tarjeta = 0.0;")

    conn.commit()
    conn.close()
    print("Migración completada exitosamente.")

if __name__ == "__main__":
    migrate()
