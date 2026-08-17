import os
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import jwt

# Rutas de base de datos
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "autohub.db"
PUBLIC_DIR = BASE_DIR / "public"

SECRET_KEY = "rmmotors_secret_key_2026"
ALGORITHM = "HS256"

# Inicializador de Base de Datos SQLite
def init_db():
    conn = sqlite3.connect(DB_PATH)
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

# Crear base de datos al cargar el modulo
init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

app = FastAPI(title="RMmotors API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Esquemas Pydantic
class WebmasterSeed(BaseModel):
    username: str
    password: str

class LoginData(BaseModel):
    username: str
    password: str

class VehiculoCreate(BaseModel):
    marca: str
    modelo: str
    anio: int
    precio: float
    kilometraje: int
    transmision: str = "Automático"
    modalidad: str
    categoria: str
    imagen_url: str

class TallerCreate(BaseModel):
    titulo: str
    descripcion: Optional[str] = None
    servicio: str
    foto_antes: str
    foto_despues: str

# Helpers de Seguridad (Hashlib SHA-256 Nativo)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def crear_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def obtener_usuario_actual(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Acceso denegado. Token requerido.")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado.")

# --- RUTAS DE ADMINISTRACIÓN ---

@app.post("/api/admin/seed")
def seed_webmaster(data: WebmasterSeed):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM webmaster WHERE username = ?;", (data.username,))
    hashed_pwd = hash_password(data.password)
    cursor.execute(
        "INSERT INTO webmaster (username, password_hash) VALUES (?, ?);",
        (data.username, hashed_pwd)
    )
    conn.commit()
    conn.close()
    return {"mensaje": f"Usuario {data.username} registrado exitosamente."}

@app.post("/api/admin/login")
def login(data: LoginData):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM webmaster WHERE username = ?;", (data.username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=400, detail="El usuario no existe.")
    
    if not verificar_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Contraseña incorrecta.")
    
    token = crear_token({"id": user["id"], "username": user["username"]})
    return {"token": token, "username": user["username"]}

# --- RUTAS PÚBLICAS ---

@app.get("/api/vehiculos")
def listar_vehiculos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehiculos ORDER BY id DESC;")
    vehiculos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return vehiculos

@app.get("/api/taller")
def listar_taller():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM galeria_taller ORDER BY id DESC;")
    trabajos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return trabajos

# --- RUTAS PRIVADAS (WEBMASTER) ---

@app.post("/api/admin/vehiculos", status_code=201)
def guardar_vehiculo(v: VehiculoCreate, user: dict = Depends(obtener_usuario_actual)):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        INSERT INTO vehiculos (marca, modelo, anio, precio, kilometraje, transmision, modalidad, categoria, imagen_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    cursor.execute(query, (v.marca, v.modelo, v.anio, v.precio, v.kilometraje, v.transmision, v.modalidad, v.categoria, v.imagen_url))
    conn.commit()
    cursor.execute("SELECT * FROM vehiculos WHERE id = ?;", (cursor.lastrowid,))
    nuevo_vehiculo = dict(cursor.fetchone())
    conn.close()
    return nuevo_vehiculo

@app.post("/api/admin/taller", status_code=201)
def guardar_taller(t: TallerCreate, user: dict = Depends(obtener_usuario_actual)):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        INSERT INTO galeria_taller (titulo, descripcion, servicio, foto_antes, foto_despues)
        VALUES (?, ?, ?, ?, ?);
    """
    cursor.execute(query, (t.titulo, t.descripcion, t.servicio, t.foto_antes, t.foto_despues))
    conn.commit()
    cursor.execute("SELECT * FROM galeria_taller WHERE id = ?;", (cursor.lastrowid,))
    nuevo_trabajo = dict(cursor.fetchone())
    conn.close()
    return nuevo_trabajo

@app.delete("/api/admin/vehiculos/{vehiculo_id}")
def eliminar_vehiculo(vehiculo_id: int, user: dict = Depends(obtener_usuario_actual)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vehiculos WHERE id = ?;", (vehiculo_id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Vehículo eliminado correctamente."}

# Servir archivos estáticos del frontend
if PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")