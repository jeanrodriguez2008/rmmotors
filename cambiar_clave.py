import sqlite3
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "autohub.db"

def cambiar_password():
    print("=== CAMBIO DE CONTRASEÑA WEBMASTER - RMMOTORS ===")
    username = input("Ingresa el usuario (por defecto 'admin'): ").strip() or "admin"
    nueva_clave = input("Ingresa la NUEVA contraseña: ").strip()

    if not nueva_clave:
        print("Error: La contraseña no puede estar vacía.")
        return

    # Generar Hash SHA-256 de la nueva clave
    password_hash = hashlib.sha256(nueva_clave.encode('utf-8')).hexdigest()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verificar si el usuario existe
    cursor.execute("SELECT id FROM webmaster WHERE username = ?;", (username,))
    user = cursor.fetchone()

    if user:
        cursor.execute("UPDATE webmaster SET password_hash = ? WHERE username = ?;", (password_hash, username))
        print("--------------------------------------------------")
        print(f" ÉXITO: Contraseña para el usuario '{username}' actualizada correctamente.")
        print("--------------------------------------------------")
    else:
        cursor.execute("INSERT INTO webmaster (username, password_hash) VALUES (?, ?);", (username, password_hash))
        print("--------------------------------------------------")
        print(f" ÉXITO: El usuario '{username}' no existía y fue creado con la nueva contraseña.")
        print("--------------------------------------------------")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    cambiar_password()