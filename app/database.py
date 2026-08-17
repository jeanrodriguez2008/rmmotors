import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "autohub.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS webmaster (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marca TEXT NOT NULL,
        modelo TEXT NOT NULL,
        anio INTEGER NOT NULL,
        precio REAL NOT NULL,
        kilometraje INTEGER DEFAULT 0,
        transmision TEXT DEFAULT 'Automático',
        modalidad TEXT CHECK (modalidad IN ('Venta', 'Financiamiento', 'Consignacion')),
        categoria TEXT CHECK (categoria IN ('Camioneta', 'Sedan', 'Rustico', 'Blindado')),
        imagen_url TEXT NOT NULL,
        estado TEXT DEFAULT 'Disponible',
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS galeria_taller (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        servicio TEXT CHECK (servicio IN ('Latoneria y Pintura', 'Detallado Profesional', 'Mecanica')),
        foto_antes TEXT NOT NULL,
        foto_despues TEXT NOT NULL,
        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

init_db()