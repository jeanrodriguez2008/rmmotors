import sqlite3
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "autohub.db"

def crear_admin_directo():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Crear tabla si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS webmaster (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)
    
    # Limpiar y crear usuario admin
    username = "admin"
    password_hash = hashlib.sha256("123456".encode('utf-8')).hexdigest()
    
    cursor.execute("DELETE FROM webmaster WHERE username = ?;", (username,))
    cursor.execute("INSERT INTO webmaster (username, password_hash) VALUES (?, ?);", (username, password_hash))
    
    conn.commit()
    conn.close()
    print("--------------------------------------------------")
    print(" SUCCESS: Usuario 'admin' con clave '123456' creado directamente en autohub.db")
    print("--------------------------------------------------")

if __name__ == "__main__":
    crear_admin_directo()