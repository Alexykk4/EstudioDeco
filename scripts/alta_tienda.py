import sqlite3
from pathlib import Path

# Ruta a la base de datos
DB_PATH = Path(r"c:\EstudioDeco\pos_estudio_deco.db")

def registrar_tienda():
    query = """
        INSERT INTO tiendas (nombre, categoria, precio_abierto, es_barra) 
        VALUES ('Ehretia', 'Deco', 0, 0);
    """
    try:
        # Se asegura de soltar el lock al terminar
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            print("✅ Tienda 'Ehretia' registrada correctamente en la BD.")
            
    except sqlite3.Error as e:
        print(f"❌ Ocurrió un error al intentar modificar la base de datos: {e}")

if __name__ == "__main__":
    registrar_tienda()
