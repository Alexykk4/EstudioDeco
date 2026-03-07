from modules.database import get_connection
conn = get_connection()
conn.execute("UPDATE config SET valor='1UaZtqerPntG-rLh5uJz48B44k2h_4tF8Z2w7xXJ0L7Q' WHERE clave='sheets_id'")
conn.commit()
print("Updated.")
row = conn.execute("SELECT valor FROM config WHERE clave='sheets_id'").fetchone()
print("ID is now:", row["valor"] if row else None)
conn.close()
