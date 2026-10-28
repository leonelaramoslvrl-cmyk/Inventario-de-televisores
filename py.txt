import io
import os
import time
from datetime import datetime
from flask import Flask, g, jsonify, render_template, request, send_file

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

import sqlite3

# Librería para generar hojas de Excel profesionales
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

def get_db():
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
                conexion      TEXT,
                intergo       TEXT,
                comentarios   TEXT,
                createdat     BIGINT NOT NULL
            )
            """
        )
    else:
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
                conexion      TEXT,
                intergo       TEXT,
                comentarios   TEXT,
                createdat     INTEGER NOT NULL
            )
            """
        )
    
    if DATABASE_URL:
        cursor.execute("ALTER TABLE tvs ADD COLUMN IF NOT EXISTS conexion TEXT")
        cursor.execute("ALTER TABLE tvs ADD COLUMN IF NOT EXISTS intergo TEXT")
        cursor.execute("ALTER TABLE tvs ADD COLUMN IF NOT EXISTS comentarios TEXT")
    else:
        cursor.execute("PRAGMA table_info(tvs)")
        columns = [row[1] for row in cursor.fetchall()]
        if "conexion" not in columns:
            cursor.execute("ALTER TABLE tvs ADD COLUMN conexion TEXT")
        if "intergo" not in columns:
            cursor.execute("ALTER TABLE tvs ADD COLUMN intergo TEXT")
        if "comentarios" not in columns:
            cursor.execute("ALTER TABLE tvs ADD COLUMN comentarios TEXT")
            
    conn.commit()
    cursor.close()

with app.app_context():
    init_db()

FIELDS = [
    "room",
    "ubicacion",
    "marca",
    "modelo",
    "serial",
    "perifericos",
    "conexion",
    "intergo",
    "comentarios",
    "instalacion",
]

def format_datetime(ts):
    if not ts:
        return "—"
    try:
        dt = datetime.fromtimestamp(ts / 1000.0)
        return dt.strftime("%d/%m/%Y · %H:%M")
    except Exception:
        return "—"

def row_to_dict(row) -> dict:
    d = dict(row)
    d["id"] = str(d["id"])
    if "createdat" in d:
        d["createdAt"] = d["createdat"]
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

@app.route("/api/tvs/export", methods=["GET"])
def export_excel():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tvs")
    rows = cursor.fetchall()
    cursor.close()

    items = [row_to_dict(r) for r in rows]

    def get_tower(room_raw):
        room = str(room_raw).strip().upper()
        if not room.isdigit():
            return "Hotel"
        n = int(room)
        if 6051 <= n <= 6069 or 6151 <= n <= 6170:
            return "Suite"
        if 100 <= n < 1200:
            floor_num = n // 100
            remainder = n % 100
            if 1 <= floor_num <= 11:
                return "Hotel" if remainder <= 50 else "Suite"
        return "Hotel"

    hotel_items = []
    suite_items = []
    other_items = []

    for item in items:
        tower = get_tower(item.get("room", ""))
        if tower == "Hotel":
            hotel_items.append(item)
        elif tower == "Suite":
            suite_items.append(item)
        else:
            other_items.append(item)

    def room_sort_key(x):
        try:
            return (0, int(x.get("room", "0")))
        except ValueError:
            return (1, x.get("room", ""))

    hotel_items.sort(key=room_sort_key)
    suite_items.sort(key=room_sort_key)
    other_items.sort(key=room_sort_key)

    wb = openpyxl.Workbook()
    default_sheet = wb.active

    headers = [
        "Num. Hab.", "Ubicación", "Marca", "Modelo", "Serial",
        "Tipo de conexión", "¿Reconoce periféricos?", "InterGO+",
        "Comentarios adicionales", "Tipo de instalación", "Fecha y hora"
    ]

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366690", end_color="366690", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    thin_border = Border(
        left=Side(style='thin', color='D7DEE7'),
        right=Side(style='thin', color='D7DEE7'),
        top=Side(style='thin', color='D7DEE7'),
        bottom=Side(style='thin', color='D7DEE7')
    )

    align_center = Alignment(horizontal="center", vertical="center")
    align_center_wrap = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def populate_sheet(ws, data_list):
        ws.views.sheetView[0].showGridLines = True
        ws.append(headers)
        ws.row_dimensions[1].height = 26
        
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = align_center
            cell.border = thin_border

        for row_idx, item in enumerate(data_list, start=2):
            room_raw = item.get("room", "")
            room_val = int(room_raw) if str(room_raw).isdigit() else room_raw

            row_data = [
                room_val,
                item.get("ubicacion", ""),
                item.get("marca", ""),
                item.get("modelo", ""),
                item.get("serial", ""),
                item.get("conexion", ""),
                item.get("perifericos", ""),
                item.get("intergo", ""),
                item.get("comentarios", ""),
                item.get("instalacion", ""),
                format_datetime(item.get("createdAt"))
            ]
            ws.append(row_data)
            ws.row_dimensions[row_idx].height = 22

            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.fill = white_fill
                cell.border = thin_border
                cell.font = Font(name="Calibri", size=10)
                
                if col_idx == 9:
                    cell.alignment = align_center_wrap
                else:
                    cell.alignment = align_center

        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            col_idx = col[0].column
            if col_idx == 9:
                ws.column_dimensions[col_letter].width = 35
            else:
                max_len = 0
                for cell in col:
                    val_str = str(cell.value or '')
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    is_first = True
    if hotel_items:
        ws_hotel = wb.active if is_first else wb.create_sheet(title="Torre Hotel")
        ws_hotel.title = "Torre Hotel"
        populate_sheet(ws_hotel, hotel_items)
        is_first = False

    if suite_items:
        ws_suite = wb.active if is_first else wb.create_sheet(title="Torre Suite")
        ws_suite.title = "Torre Suite"
        populate_sheet(ws_suite, suite_items)
        is_first = False

    if other_items:
        ws_other = wb.active if is_first else wb.create_sheet(title="Otros")
        ws_other.title = "Otros"
        populate_sheet(ws_other, other_items)
        is_first = False

    if not hotel_items and not suite_items and not other_items:
        default_sheet.title = "Inventario TV"
        populate_sheet(default_sheet, [])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Inventario_TVs.xlsx"
    )

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