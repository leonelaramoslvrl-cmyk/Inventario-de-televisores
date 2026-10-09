"""
Inventario de televisores — backend
------------------------------------
Framework: Flask (gratuito, open source)
Base de datos: SQLite — viene incluida en Python, no requiere instalar nada
                aparte ni crear ninguna cuenta en la nube. Los datos se
                guardan en el archivo "inventario.db" que se crea solo, en
                esta misma carpeta, la primera vez que arrancas la app.

Cómo correrlo:
    1. pip install -r requirements.txt
    2. python app.py

Luego abre http://localhost:5000 en el navegador (o http://TU_IP_LOCAL:5000
desde otro celular en la misma red Wi-Fi).

Independencia: la app funciona sola, sin internet y sin configurar nada —
no hay contraseñas ni cadenas de conexión que copiar. Mientras conserves el
archivo "inventario.db" (por ejemplo, al mover la carpeta completa a otra
computadora), tus datos se mantienen intactos.
"""

#import os
#import sqlite3
#import time

#from flask import Flask, g, jsonify, render_template, request

#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#DB_PATH = os.path.join(BASE_DIR, "inventario.db")

#app = Flask(__name__)

import os
import time
from flask import Flask, g, jsonify, render_template, request

# Intentamos importar psycopg2 para PostgreSQL en producción
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

def get_db():
    if DATABASE_URL:
        # Conexión a PostgreSQL en Render
        if DATABASE_URL.startswith("postgres://"):
            url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        else:
            url = DATABASE_URL
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.DictCursor)
        return conn
    else:
        # Conexión local a SQLite
        DB_PATH = os.path.join(BASE_DIR, "inventario.db")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

# Columnas que el frontend envía y espera recibir de vuelta.
FIELDS = [
    "room",
    "ubicacion",
    "marca",
    "modelo",
    "serial",
    "perifericos",
    "instalacion",
]


def get_db():
    """Abre (o reutiliza) la conexión SQLite de esta petición."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea la tabla y el archivo inventario.db si no existen. Se llama una vez al iniciar la app."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tvs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            room          TEXT NOT NULL,
            ubicacion     TEXT,
            marca         TEXT,
            modelo        TEXT NOT NULL,
            serial        TEXT NOT NULL,
            perifericos   TEXT,
            instalacion   TEXT,
            createdAt     INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # El frontend espera un campo "id" como texto.
    d["id"] = str(d["id"])
    return d


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tvs", methods=["GET"])
def list_tvs():
    db = get_db()
    rows = db.execute('SELECT * FROM tvs ORDER BY "createdAt" DESC').fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/tvs", methods=["POST"])
def create_tv():
    payload = request.get_json(silent=True) or {}

    room = (payload.get("room") or "").strip()
    modelo = (payload.get("modelo") or "").strip()
    serial = (payload.get("serial") or "").strip()
    if not room or not modelo or not serial:
        return jsonify({"error": "room, modelo y serial son obligatorios"}), 400

    values = {field: (payload.get(field) or "") for field in FIELDS}
    values["room"] = room
    values["modelo"] = modelo
    values["serial"] = serial
    created_at = int(time.time() * 1000)

    columns = FIELDS + ["createdAt"]
    quoted_columns = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(["?"] * len(columns))

    db = get_db()
    cur = db.execute(
        f'INSERT INTO tvs ({quoted_columns}) VALUES ({placeholders})',
        [values[f] for f in FIELDS] + [created_at],
    )
    db.commit()
    new_row = db.execute('SELECT * FROM tvs WHERE id = ?', (cur.lastrowid,)).fetchone()
    return jsonify(row_to_dict(new_row)), 201


@app.route("/api/tvs/<int:tv_id>", methods=["PUT"])
def update_tv(tv_id):
    payload = request.get_json(silent=True) or {}

    db = get_db()
    existing = db.execute('SELECT * FROM tvs WHERE id = ?', (tv_id,)).fetchone()
    if existing is None:
        return jsonify({"error": "No encontrado"}), 404

    room = (payload.get("room") or "").strip()
    modelo = (payload.get("modelo") or "").strip()
    serial = (payload.get("serial") or "").strip()
    if not room or not modelo or not serial:
        return jsonify({"error": "room, modelo y serial son obligatorios"}), 400

    values = {field: (payload.get(field) or "") for field in FIELDS}
    values["room"] = room
    values["modelo"] = modelo
    values["serial"] = serial

    set_clause = ", ".join(f'"{f}" = ?' for f in FIELDS)
    db.execute(
        f'UPDATE tvs SET {set_clause} WHERE id = ?',
        [values[f] for f in FIELDS] + [tv_id],
    )
    db.commit()
    updated = db.execute('SELECT * FROM tvs WHERE id = ?', (tv_id,)).fetchone()
    return jsonify(row_to_dict(updated))


if __name__ == "__main__":
    init_db()
    # host="0.0.0.0" permite abrir la app desde otros celulares en la misma red Wi-Fi
    app.run(host="0.0.0.0", port=5000, debug=True)
