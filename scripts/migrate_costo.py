from modules.database import get_connection

def migrate():
    conn = get_connection()
    cur = conn.cursor()
    
    # Check productos
    cur.execute("PRAGMA table_info(productos)")
    cols_prod = [c[1] for c in cur.fetchall()]
    if "costo" not in cols_prod:
        print("Adding costo to productos...")
        cur.execute("ALTER TABLE productos ADD COLUMN costo REAL NOT NULL DEFAULT 0.0")

    # Check venta_detalle 
    cur.execute("PRAGMA table_info(venta_detalle)")
    cols_vd = [c[1] for c in cur.fetchall()]
    if "costo_unitario" not in cols_vd:
        print("Adding costo_unitario to venta_detalle...")
        cur.execute("ALTER TABLE venta_detalle ADD COLUMN costo_unitario REAL NOT NULL DEFAULT 0.0")
        
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
