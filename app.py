import io
import json
import os
import re
import time
from datetime import datetime
from flask import Flask, g, jsonify, render_template, request, send_file

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

import sqlite3

# Librería para generar hojas de Excel
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Librerías de Google Sheets API
from google.oauth2 import service_account
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")

# Configuración de Google Sheets
SPREADSHEET_ID = "1fb3grPyS3WA6hmhWRSsvX4SUKmTkY-YfSMiASK6-Jf0"
SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "credentials.json")
RENDER_SECRET_FILE = "/etc/secrets/credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TARGET_SHEETS = [
    "C1 Intergo01@eurobuilding.com.v",
    "C2 Intergo02@eurobuilding.com.v",
    "C3 Intergo03@eurobuilding.com.v",
    "C4 Intergo04@eurobuilding.com.v",
    "C5 Intergo05@eurobuilding.com.v",
    "C6 Intergo06@eurobuilding.com.v",
    "C7 Intergo07@eurobuilding.com.v",
]

app = Flask(__name__)


def get_sheets_service():
    """Autentica con la cuenta de servicio desde variable de entorno, /etc/secrets (Render) o ruta local."""
    creds_json_env = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json_env:
        info = json.loads(creds_json_env)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif os.path.exists(RENDER_SECRET_FILE):
        creds = service_account.Credentials.from_service_account_file(RENDER_SECRET_FILE, scopes=SCOPES)
    elif os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    else:
        return None
    return build("sheets", "v4", credentials=creds)


def build_notas_text(tv_data: dict) -> str:
    """Devuelve únicamente el contenido de comentarios adicionales para la columna Notas."""
    return (tv_data.get("comentarios") or "").strip()


def find_target_row(rows: list, tv_data: dict):
    """Encuentra el índice de fila (1-based) correspondiente al TV dentro de una pestaña."""
    room_target = str(tv_data.get("room", "")).strip()
    if not room_target:
        return None

    match_num = re.search(r"\d+", room_target)
    room_num_str = match_num.group() if match_num else room_target

    is_tv2 = bool(re.search(r"(sala|tv\s*2|-2|\(2\))", f"{room_target} {tv_data.get('ubicacion', '')}", re.IGNORECASE))
    target_tv_index = "2" if is_tv2 else "1"
    serial = str(tv_data.get("serial", "")).strip()

    candidate_row_idx = None
    fallback_row_idx = None

    for idx, row in enumerate(rows, start=2):
        hab_cell = str(row[2]).strip() if len(row) > 2 else ""
        tv_cell = str(row[3]).strip() if len(row) > 3 else "1"
        serial_cell = str(row[6]).strip() if len(row) > 6 else ""

        if hab_cell == room_num_str:
            if fallback_row_idx is None:
                fallback_row_idx = idx
            if serial and serial_cell == serial:
                candidate_row_idx = idx
                break
            if tv_cell == target_tv_index:
                candidate_row_idx = idx
                break

    return candidate_row_idx or fallback_row_idx


def sync_tv_to_google_sheet(tv_data: dict) -> bool:
    """Busca la habitación en las pestañas C1..C7 y rellena Modelo, Serial, Intergo y Notas."""
    service = get_sheets_service()
    if not service:
        print("Advertencia: No se encontraron credenciales de Google (credentials.json).")
        return False

    if not str(tv_data.get("room", "")).strip():
        return False

    modelo = tv_data.get("modelo", "")
    serial = tv_data.get("serial", "")
    intergo = tv_data.get("intergo", "")
    notas = build_notas_text(tv_data)

    sheet_api = service.spreadsheets()

    for sheet_name in TARGET_SHEETS:
        range_read = f"'{sheet_name}'!A2:I150"
        result = sheet_api.values().get(spreadsheetId=SPREADSHEET_ID, range=range_read).execute()
        rows = result.get("values", [])

        row_to_update = find_target_row(rows, tv_data)
        if row_to_update:
            update_range = f"'{sheet_name}'!F{row_to_update}:I{row_to_update}"
            body = {"values": [[modelo, serial, intergo, notas]]}
            sheet_api.values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=update_range,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            return True

    return False


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
            CREATE TABLE IF NOT EXISTS tv_inventario (
                id           SERIAL PRIMARY KEY,
                room         TEXT NOT NULL,
                ubicacion    TEXT,
                marca        TEXT,
                modelo       TEXT NOT NULL,
                serial       TEXT NOT NULL,
                perifericos  TEXT,
                instalacion  TEXT,
                conexion     TEXT,
                intergo      TEXT,
                comentarios  TEXT,
                createdat    BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT
            )
            """
        )
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tv_inventario (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                room         TEXT NOT NULL,
                ubicacion    TEXT,
                marca        TEXT,
                modelo       TEXT NOT NULL,
                serial       TEXT NOT NULL,
                perifericos  TEXT,
                instalacion  TEXT,
                conexion     TEXT,
                intergo      TEXT,
                comentarios  TEXT,
                createdat    INTEGER DEFAULT (CAST(strftime('%s', 'now') AS INTEGER) * 1000)
            )
            """
        )

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
    d["createdAt"] = d.get("createdat") or d.get("CREATEDAT") or d.get("createdAt") or 0
    return d


def room_sort_key(x):
    room_raw = x.get("room", "")
    match = re.search(r"\d+", str(room_raw))
    if match:
        return (0, int(match.group()), str(room_raw).strip())
    return (1, 0, str(room_raw).strip())


@app.route("/")
def index():
    return render_template("index.html")


# --- LISTADO ORDENADO ASCENDENTEMENTE POR HABITACIÓN ---
@app.route("/api/tvs", methods=["GET"])
def list_tvs():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tv_inventario")
    rows = cursor.fetchall()
    cursor.close()

    items = [row_to_dict(r) for r in rows]
    items.sort(key=room_sort_key)

    return jsonify(items)


def get_base_room(room_raw):
    match = re.search(r"\d+", str(room_raw))
    if match:
        return int(match.group())
    return 0


# --- RUTA PARA SINCRONIZAR TODOS LOS REGISTROS EXISTENTES CON GOOGLE SHEETS EN BLOQUE ---
@app.route("/api/tvs/sync-sheets", methods=["POST"])
def sync_all_to_sheets():
    try:
        service = get_sheets_service()
        if not service:
            return jsonify({
                "error": "No se encontraron credenciales de Google en Render (/etc/secrets/credentials.json ni GOOGLE_CREDENTIALS_JSON)."
            }), 500

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tv_inventario")
        rows = cursor.fetchall()
        cursor.close()

        items = [row_to_dict(r) for r in rows]
        sheet_api = service.spreadsheets()

        # Leer todas las pestañas C1..C7 una sola vez
        sheets_data = {}
        for sheet_name in TARGET_SHEETS:
            range_read = f"'{sheet_name}'!A2:I150"
            result = sheet_api.values().get(spreadsheetId=SPREADSHEET_ID, range=range_read).execute()
            sheets_data[sheet_name] = result.get("values", [])

        batch_updates = []
        synced = 0
        not_found = []

        for item in items:
            matched = False
            for sheet_name in TARGET_SHEETS:
                row_to_update = find_target_row(sheets_data[sheet_name], item)
                if row_to_update:
                    batch_updates.append({
                        "range": f"'{sheet_name}'!F{row_to_update}:I{row_to_update}",
                        "values": [[
                            item.get("modelo", ""),
                            item.get("serial", ""),
                            item.get("intergo", ""),
                            build_notas_text(item),
                        ]],
                    })
                    synced += 1
                    matched = True
                    break
            if not matched:
                not_found.append(item.get("room"))

        if batch_updates:
            sheet_api.values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={
                    "valueInputOption": "USER_ENTERED",
                    "data": batch_updates,
                },
            ).execute()

        return jsonify({
            "message": f"Sincronizados {synced} de {len(items)} televisores.",
            "synced": synced,
            "no_encontrados_en_sheet": not_found,
        })
    except Exception as e:
        print(f"Error en sync_all_to_sheets: {e}")
        return jsonify({"error": str(e)}), 500


# --- RUTA DE EXPORTACIÓN A EXCEL ESTÁNDAR ---
@app.route("/api/tvs/export", methods=["GET"])
def export_excel():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tv_inventario")
        rows = cursor.fetchall()
        cursor.close()

        items = [row_to_dict(r) for r in rows]

        def get_tower(room_raw):
            n = get_base_room(room_raw)
            if n == 0:
                return "Hotel"
            if 6051 <= n <= 6069 or 6151 <= n <= 6170:
                return "Suite"
            if 100 <= n < 1200:
                floor_num = n // 100
                remainder = n % 100
                if 1 <= floor_num <= 11:
                    return "Hotel" if remainder <= 50 else "Suite"
            return "Hotel"

        hotel_items, suite_items, other_items = [], [], []
        for item in items:
            tower = get_tower(item.get("room", ""))
            if tower == "Hotel":
                hotel_items.append(item)
            elif tower == "Suite":
                suite_items.append(item)
            else:
                other_items.append(item)

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
            left=Side(style="thin", color="D7DEE7"),
            right=Side(style="thin", color="D7DEE7"),
            top=Side(style="thin", color="D7DEE7"),
            bottom=Side(style="thin", color="D7DEE7"),
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

                row_data = [
                    room_raw,
                    item.get("ubicacion", ""),
                    item.get("marca", ""),
                    item.get("modelo", ""),
                    item.get("serial", ""),
                    item.get("conexion", ""),
                    item.get("perifericos", ""),
                    item.get("intergo", ""),
                    item.get("comentarios", ""),
                    item.get("instalacion", ""),
                    format_datetime(item.get("createdAt")),
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
                        val_str = str(cell.value or "")
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
            download_name="Inventario_TVs.xlsx",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
            f"INSERT INTO tv_inventario ({columns_str}) VALUES ({placeholders}) RETURNING id",
            [values[f] for f in FIELDS] + [created_at],
        )
        new_id = cursor.fetchone()["id"]
        db.commit()
        cursor.execute("SELECT * FROM tv_inventario WHERE id = %s", (new_id,))
        new_row = cursor.fetchone()
    else:
        cursor.execute(
            f"INSERT INTO tv_inventario ({columns_str}) VALUES ({placeholders})",
            [values[f] for f in FIELDS] + [created_at],
        )
        db.commit()
        cursor.execute("SELECT * FROM tv_inventario WHERE id = ?", (cursor.lastrowid,))
        new_row = cursor.fetchone()

    cursor.close()
    tv_dict = row_to_dict(new_row)

    # Sincronización automática con Google Sheets
    try:
        sync_tv_to_google_sheet(tv_dict)
    except Exception as sync_err:
        print(f"Error al sincronizar con Google Sheets: {sync_err}")

    return jsonify(tv_dict), 201


@app.route("/api/tvs/<int:tv_id>", methods=["PUT"])
def update_tv(tv_id):
    payload = request.get_json(silent=True) or {}

    db = get_db()
    cursor = db.cursor()

    sel_ph = "%s" if DATABASE_URL else "?"
    cursor.execute(f"SELECT * FROM tv_inventario WHERE id = {sel_ph}", (tv_id,))
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
        f"UPDATE tv_inventario SET {set_clause} WHERE id = {eq_ph}",
        [values[f] for f in FIELDS] + [tv_id],
    )
    db.commit()

    cursor.execute(f"SELECT * FROM tv_inventario WHERE id = {sel_ph}", (tv_id,))
    updated = cursor.fetchone()
    cursor.close()
    tv_dict = row_to_dict(updated)

    # Sincronización automática con Google Sheets
    try:
        sync_tv_to_google_sheet(tv_dict)
    except Exception as sync_err:
        print(f"Error al sincronizar con Google Sheets: {sync_err}")

    return jsonify(tv_dict)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)