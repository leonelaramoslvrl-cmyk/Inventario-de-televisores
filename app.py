import os
import time
from flask import Flask, g, jsonify, render_template, request

# Intentamos importar psycopg2 para PostgreSQL en producción
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

def get_db():
    """Abre o reutiliza la conexión a la base de datos (PostgreSQL en Render o SQLite local)."""
    if "db" not in g:
        if DATABASE_URL:
            url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
            g.db = psycopg2.connect(url, cursor_factory=psycopg2.extras.DictCursor)
        else:
            DB_PATH = os.path.join(BASE_DIR, "inventario.db")
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Crea la tabla adaptada al motor de base de datos en uso."""
    conn = get_db()
    cursor = conn.cursor()
    if DATABASE_URL:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tvs (
                id            SERIAL PRIMARY KEY,
                room          TEXT NOT NULL,
                ubicacion     TEXT,
                marca         TEXT,
                modelo        TEXT NOT NULL,
                serial        TEXT NOT NULL,
                perifericos   TEXT,
                instalacion   TEXT,
                createdat     BIGINT NOT NULL
            )
            """
        )
    else:
        DB_PATH = os.path.join(BASE_DIR, "inventario.db")
        cursor.execute(
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
                createdat     INTEGER NOT NULL
            )
            """
        )
    conn.commit()
    cursor.close()

# Ejecutar init_db al iniciar la aplicación en cualquier entorno (incluyendo Gunicorn)
with app.app_context():
    init_db()

FIELDS = [
    "room",
    "ubicacion",
    "marca",
    "modelo",
    "serial",
    "perifericos",
    "instalacion",
]

def row_to_dict(row) -> dict:
    d = dict(row)
    d["id"] = str(d["id"])
    return d

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/tvs", methods=["GET"])
def list_tvs():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tvs ORDER BY createdat DESC")
    rows = cursor.fetchall()
    cursor.close()
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

    columns = FIELDS + ["createdat"]
    columns_str = ", ".join(columns)
    
    ph = "%s" if DATABASE_URL else "?"
    placeholders = ", ".join([ph] * len(columns))

    db = get_db()
    cursor = db.cursor()

    if DATABASE_URL:
        cursor.execute(
            f"INSERT INTO tvs ({columns_str}) VALUES ({placeholders}) RETURNING id",
            [values[f] for f in FIELDS] + [created_at],
        )
        new_id = cursor.fetchone()["id"]
        db.commit()
        cursor.execute("SELECT * FROM tvs WHERE id = %s", (new_id,))
        new_row = cursor.fetchone()
    else:
        cursor.execute(
            f"INSERT INTO tvs ({columns_str}) VALUES ({placeholders})",
            [values[f] for f in FIELDS] + [created_at],
        )
        db.commit()
        cursor.execute("SELECT * FROM tvs WHERE id = ?", (cursor.lastrowid,))
        new_row = cursor.fetchone()

    cursor.close()
    return jsonify(row_to_dict(new_row)), 201

@app.route("/api/tvs/<int:tv_id>", methods=["PUT"])
def update_tv(tv_id):
    payload = request.get_json(silent=True) or {}

    db = get_db()
    cursor = db.cursor()
    
    sel_ph = "%s" if DATABASE_URL else "?"
    cursor.execute(f"SELECT * FROM tvs WHERE id = {sel_ph}", (tv_id,))
    existing = cursor.fetchone()
    if existing is None:
        cursor.close()
        return jsonify({"error": "No encontrado"}), 404

    room = (payload.get("room") or "").strip()
    modelo = (payload.get("modelo") or "").strip()
    serial = (payload.get("serial") or "").strip()
    if not room or not modelo or not serial:
        cursor.close()
        return jsonify({"error": "room, modelo y serial son obligatorios"}), 400

    values = {field: (payload.get(field) or "") for field in FIELDS}
    values["room"] = room
    values["modelo"] = modelo
    values["serial"] = serial

    eq_ph = "%s" if DATABASE_URL else "?"
    set_clause = ", ".join(f"{f} = {eq_ph}" for f in FIELDS)
    
    cursor.execute(
        f"UPDATE tvs SET {set_clause} WHERE id = {eq_ph}",
        [values[f] for f in FIELDS] + [tv_id],
    )
    db.commit()
    
    cursor.execute(f"SELECT * FROM tvs WHERE id = {sel_ph}", (tv_id,))
    updated = cursor.fetchone()
    cursor.close()
    return jsonify(row_to_dict(updated))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)