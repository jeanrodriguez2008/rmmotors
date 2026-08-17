import os
import json
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import jwt

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
DB_PATH = BASE_DIR / "autohub.db"

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "rmmotors_secret_key_2026")

app = Flask(__name__, static_folder=str(PUBLIC_DIR))
CORS(app)

# Detección automática de Base de Datos (PostgreSQL en Render / SQLite en Local)
def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn, "postgres"
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    try:
        conn, db_type = get_db()
        cursor = conn.cursor()
        
        if db_type == "postgres":
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS webmaster (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehiculos (
                id SERIAL PRIMARY KEY,
                marca VARCHAR(50) NOT NULL,
                modelo VARCHAR(50) NOT NULL,
                anio INT NOT NULL,
                precio NUMERIC NOT NULL,
                kilometraje INT DEFAULT 0,
                transmision VARCHAR(30) DEFAULT 'Automático',
                modalidad VARCHAR(30),
                categoria VARCHAR(30),
                imagen_url TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS galeria_taller (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(100) NOT NULL,
                descripcion TEXT,
                servicio VARCHAR(50),
                foto_antes TEXT NOT NULL,
                foto_despues TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS webmaster (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
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
                modalidad TEXT,
                categoria TEXT,
                imagen_url TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS galeria_taller (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                servicio TEXT,
                foto_antes TEXT NOT NULL,
                foto_despues TEXT NOT NULL,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

        conn.commit()
        cursor.close()
        conn.close()
        print("--> Base de datos inicializada correctamente.")
    except Exception as e:
        print(f"--> Error al inicializar BD: {e}")

init_db()

# --- RUTAS DE ARCHIVOS ESTÁTICOS ---

@app.route('/')
def index():
    return send_from_directory(PUBLIC_DIR, 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory(PUBLIC_DIR, path)

# --- ENDPOINTS API ---

@app.route('/api/vehiculos', methods=['GET'])
def listar_vehiculos():
    conn, db_type = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehiculos ORDER BY id DESC;")
    rows = cursor.fetchall()
    vehiculos = [dict(row) for row in rows]
    cursor.close()
    conn.close()
    return jsonify(vehiculos)

@app.route('/api/taller', methods=['GET'])
def listar_taller():
    conn, db_type = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM galeria_taller ORDER BY id DESC;")
    rows = cursor.fetchall()
    trabajos = [dict(row) for row in rows]
    cursor.close()
    conn.close()
    return jsonify(trabajos)

@app.route('/api/admin/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    username = data.get('username', '')
    password = data.get('password', '')

    conn, db_type = get_db()
    cursor = conn.cursor()
    
    param = "%s" if db_type == "postgres" else "?"
    cursor.execute(f"SELECT * FROM webmaster WHERE username = {param};", (username,))
    row = cursor.fetchone()
    user = dict(row) if row else None
    cursor.close()
    conn.close()

    if user and hash_password(password) == user['password_hash']:
        token = jwt.encode({"id": user['id'], "username": username}, SECRET_KEY, algorithm="HS256")
        return jsonify({"token": token, "username": username}), 200
    return jsonify({"detail": "Usuario o contraseña incorrectos."}), 400

@app.route('/api/admin/seed', methods=['POST'])
def seed():
    data = request.get_json(force=True)
    username = data.get('username', 'admin')
    password = data.get('password', '123456')

    conn, db_type = get_db()
    cursor = conn.cursor()
    param = "%s" if db_type == "postgres" else "?"
    
    cursor.execute(f"DELETE FROM webmaster WHERE username = {param};", (username,))
    cursor.execute(f"INSERT INTO webmaster (username, password_hash) VALUES ({param}, {param});", (username, hash_password(password)))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": f"Usuario {username} creado exitosamente."}), 200

@app.route('/api/admin/vehiculos', methods=['POST'])
def guardar_vehiculo():
    data = request.get_json(force=True)
    conn, db_type = get_db()
    cursor = conn.cursor()
    
    params = ("%s, " * 9)[:-2] if db_type == "postgres" else ("?, " * 9)[:-2]
    query = f"""
        INSERT INTO vehiculos (marca, modelo, anio, precio, kilometraje, transmision, modalidad, categoria, imagen_url)
        VALUES ({params});
    """
    cursor.execute(query, (
        data.get('marca'), data.get('modelo'), data.get('anio'),
        data.get('precio'), data.get('kilometraje'), data.get('transmision', 'Automático'),
        data.get('modalidad'), data.get('categoria'), data.get('imagen_url')
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "Vehículo registrado correctamente."}), 201

@app.route('/api/admin/taller', methods=['POST'])
def guardar_taller():
    data = request.get_json(force=True)
    conn, db_type = get_db()
    cursor = conn.cursor()
    
    params = ("%s, " * 5)[:-2] if db_type == "postgres" else ("?, " * 5)[:-2]
    query = f"""
        INSERT INTO galeria_taller (titulo, descripcion, servicio, foto_antes, foto_despues)
        VALUES ({params});
    """
    cursor.execute(query, (
        data.get('titulo'), data.get('descripcion'), data.get('servicio'),
        data.get('foto_antes'), data.get('foto_despues')
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "Trabajo de taller registrado correctamente."}), 201

@app.route('/api/admin/vehiculos/<int:v_id>', methods=['DELETE'])
def eliminar_vehiculo(v_id):
    conn, db_type = get_db()
    cursor = conn.cursor()
    param = "%s" if db_type == "postgres" else "?"
    cursor.execute(f"DELETE FROM vehiculos WHERE id = {param};", (v_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "Vehículo eliminado."}), 200

@app.route('/api/admin/taller/<int:t_id>', methods=['DELETE'])
def eliminar_taller(t_id):
    conn, db_type = get_db()
    cursor = conn.cursor()
    param = "%s" if db_type == "postgres" else "?"
    cursor.execute(f"DELETE FROM galeria_taller WHERE id = {param};", (t_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"mensaje": "Trabajo eliminado."}), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)