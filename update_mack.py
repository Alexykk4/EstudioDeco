import sqlite3
import os

db_path = "c:\\EstudioDeco\\pos_estudio_deco.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check if Mack exists and current configuration
    cur.execute("SELECT id, nombre, precio_abierto FROM tiendas WHERE nombre='Mack'")
    tienda = cur.fetchone()
    
    if tienda:
        print(f"Tienda encontrada: {tienda[1]} con precio_abierto={tienda[2]}")
        cur.execute("UPDATE tiendas SET precio_abierto = 0 WHERE id = ?", (tienda[0],))
        conn.commit()
        print("MACK actualizado a precio_abierto = 0 exitosamente.")
    else:
        print("La tienda MACK no fue encontrada.")
    conn.close()
else:
    print("Base de datos no encontrada.")
