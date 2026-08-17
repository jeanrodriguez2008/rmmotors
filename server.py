import json
import sqlite3
import hashlib
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "autohub.db"
PUBLIC_DIR = BASE_DIR / "public"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    conn.close()

init_db()

class RMmotorsHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def _set_cors_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Type', 'application/json')

    def do_OPTIONS(self):
        self._set_cors_headers(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/vehiculos':
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vehiculos ORDER BY id DESC;")
            vehiculos = [dict(row) for row in cursor.fetchall()]
            conn.close()

            self._set_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps(vehiculos).encode('utf-8'))

        elif self.path == '/api/taller':
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM galeria_taller ORDER BY id DESC;")
            trabajos = [dict(row) for row in cursor.fetchall()]
            conn.close()

            self._set_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps(trabajos).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body) if body else {}

            if self.path == '/api/admin/login':
                username = data.get('username', '')
                password = data.get('password', '')

                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM webmaster WHERE username = ?;", (username,))
                user = cursor.fetchone()
                conn.close()

                if user and hash_password(password) == user['password_hash']:
                    self._set_cors_headers(200)
                    self.end_headers()
                    self.wfile.write(json.dumps({"token": "rmmotors_local_token_2026", "username": username}).encode('utf-8'))
                else:
                    self._set_cors_headers(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"detail": "Usuario o contraseña incorrectos."}).encode('utf-8'))

            elif self.path == '/api/admin/vehiculos':
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                query = """
                    INSERT INTO vehiculos (marca, modelo, anio, precio, kilometraje, transmision, modalidad, categoria, imagen_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """
                cursor.execute(query, (
                    data.get('marca'), data.get('modelo'), data.get('anio'),
                    data.get('precio'), data.get('kilometraje'), data.get('transmision', 'Automático'),
                    data.get('modalidad'), data.get('categoria'), data.get('imagen_url')
                ))
                conn.commit()
                conn.close()

                self._set_cors_headers(201)
                self.end_headers()
                self.wfile.write(json.dumps({"mensaje": "Vehículo registrado correctamente."}).encode('utf-8'))

            elif self.path == '/api/admin/taller':
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                query = """
                    INSERT INTO galeria_taller (titulo, descripcion, servicio, foto_antes, foto_despues)
                    VALUES (?, ?, ?, ?, ?);
                """
                cursor.execute(query, (
                    data.get('titulo'), data.get('descripcion'), data.get('servicio'),
                    data.get('foto_antes'), data.get('foto_despues')
                ))
                conn.commit()
                conn.close()

                self._set_cors_headers(201)
                self.end_headers()
                self.wfile.write(json.dumps({"mensaje": "Trabajo de taller publicado correctamente."}).encode('utf-8'))

        except Exception as e:
            print(f"--> Error en petición POST: {e}")
            self._set_cors_headers(500)
            self.end_headers()
            self.wfile.write(json.dumps({"detail": str(e)}).encode('utf-8'))

    def do_DELETE(self):
        if self.path.startswith('/api/admin/vehiculos/'):
            vehiculo_id = self.path.split('/')[-1]
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vehiculos WHERE id = ?;", (vehiculo_id,))
            conn.commit()
            conn.close()

            self._set_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"mensaje": "Vehículo eliminado."}).encode('utf-8'))

        elif self.path.startswith('/api/admin/taller/'):
            taller_id = self.path.split('/')[-1]
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM galeria_taller WHERE id = ?;", (taller_id,))
            conn.commit()
            conn.close()

            self._set_cors_headers(200)
            self.end_headers()
            self.wfile.write(json.dumps({"mensaje": "Trabajo de taller eliminado."}).encode('utf-8'))

if __name__ == '__main__':
    print("--> Servidor RMmotors activo en http://127.0.0.1:5000")
    server = HTTPServer(('127.0.0.1', 5000), RMmotorsHandler)
    server.serve_forever()