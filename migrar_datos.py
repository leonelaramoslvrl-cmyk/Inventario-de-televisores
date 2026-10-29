# -*- coding: utf-8 -*-
"""
import sqlite3
import os
import psycopg2
import io
import pandas as pd
from flask import send_file



# Pega aquí tu URL externa de Render (la que empieza con postgresql://...)
database_url = os.getenv('DATABASE_URL', 'postgresql://inventario_db_e9b1_user:XmfUZfxW0Q80mrvEiDFw0NGEmMAgwmzQ@dpg-db4gjpbncjis73cuab2g-a.oregon-postgres.render.com/inventario_db_e9b1')

import io
import pandas as pd
from flask import send_file

# API: Exportar registros a Excel
@app.route('/api/export', methods=['GET'])
def export_excel():
    try:
        tvs = TVInventario.query.all()
        if not tvs:
            return jsonify({'error': 'No hay registros para exportar'}), 404

        # Convertir los datos a un DataFrame de pandas
        data = [tv.to_dict() for tv in tvs]
        df = pd.DataFrame(data)

        # Crear un archivo Excel en memoria usando BytesIO
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Inventario TVs')
        
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='inventario_televisores.xlsx'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

try:
    pg_conn = psycopg2.connect(database_url)
    cursor_pg = pg_conn.cursor()
    print("¡Conectado a la base de datos de Render exitosamente!")
except Exception as e:
    print(f"Error al conectar con PostgreSQL: {e}")
    exit()

archivos_sqlite = ['inventario.db', 'televisores.db']
total_migrados = 0

for archivo in archivos_sqlite:
    if os.path.exists(archivo):
        print(f"\n📂 Leyendo registros de: {archivo}")
        try:
            conn = sqlite3.connect(archivo)
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA table_info(tvs);")
            columnas_info = [col[1] for col in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM tvs;")
            filas = cursor.fetchall()
            print(f"   -> Encontrados {len(filas)} registros en '{archivo}'.")
            
            for reg in filas:
                reg_dict = {columnas_info[i]: reg[i] for i in range(len(columnas_info))}
                
                room = str(reg_dict.get('room', 'N/A'))[:20]
                ubicacion = str(reg_dict.get('ubicacion'))[:50] if reg_dict.get('ubicacion') else None
                marca = str(reg_dict.get('marca', 'Desconocida'))[:50]
                modelo = str(reg_dict.get('modelo', 'Desconocido'))[:100]
                serial = str(reg_dict.get('serial', 'N/A'))[:100]
                
                conexion_val = reg_dict.get('conexion') or reg_dict.get('conectado')
                conexion = str(conexion_val)[:50] if conexion_val else None
                
                perifericos = str(reg_dict.get('perifericos'))[:10] if reg_dict.get('perifericos') else None
                intergo = str(reg_dict.get('intergo'))[:10] if reg_dict.get('intergo') else None
                comentarios = reg_dict.get('comentarios')
                
                instalacion_val = reg_dict.get('instalacion')
                instalacion = str(instalacion_val)[:50] if instalacion_val else None

                try:
                    cursor_pg.execute("""
                        INSERT INTO tv_inventario (room, ubicacion, marca, modelo, serial, conexion, perifericos, intergo, comentarios, instalacion)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (room, ubicacion, marca, modelo, serial, conexion, perifericos, intergo, comentarios, instalacion))
                    pg_conn.commit()
                    total_migrados += 1
                except Exception as ex:
                    pg_conn.rollback() # Limpia la transacción para que no afecte a los demás
                    print(f"   ⚠️ Error al insertar un registro: {ex}")
            conn.close()
        except Exception as e:
            print(f"   ❌ Error al procesar {archivo}: {e}")

cursor_pg.close()
pg_conn.close()

print(f"\n==========================================")
print(f"¡Migración completa!")
print(f"Total de registros subidos a Render: {total_migrados}")
print(f"==========================================")

"""