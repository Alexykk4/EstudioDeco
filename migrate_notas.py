import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pos_estudio_deco.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("""
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    texto TEXT NOT NULL,
    pos_x REAL NOT NULL DEFAULT 100,
    pos_y REAL NOT NULL DEFAULT 100,
    color TEXT DEFAULT '#fef3c7',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
)
""")
conn.commit()
conn.close()
print("Migration applied successfully.")
