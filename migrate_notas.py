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
    width REAL NOT NULL DEFAULT 260,
    height REAL NOT NULL DEFAULT 180,
    minimizada INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
)
""")
cols = {row[1] for row in conn.execute("PRAGMA table_info(notas)").fetchall()}
if "width" not in cols:
    conn.execute("ALTER TABLE notas ADD COLUMN width REAL NOT NULL DEFAULT 260")
if "height" not in cols:
    conn.execute("ALTER TABLE notas ADD COLUMN height REAL NOT NULL DEFAULT 180")
if "minimizada" not in cols:
    conn.execute("ALTER TABLE notas ADD COLUMN minimizada INTEGER NOT NULL DEFAULT 0")
conn.commit()
conn.close()
print("Migration applied successfully.")
