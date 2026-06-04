from modules.database import get_connection
conn = get_connection()
conn.execute("UPDATE config SET valor='1ycDNWVK9ePwDzVUfGLjvbz3N-9Qf7Y9WEuP-2rq7CII' WHERE clave='sheets_id'")
conn.commit()
print("ID de Sheets actualizado a: 1ycDNWVK9ePwDzVUfGLjvbz3N-9Qf7Y9WEuP-2rq7CII")
row = conn.execute("SELECT valor FROM config WHERE clave='sheets_id'").fetchone()
print("Verificación en BD:", row["valor"] if row else None)
conn.close()
