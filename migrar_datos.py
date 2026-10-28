# -*- coding: utf-8 -*-
import sqlite3
import os

archivos_sqlite = ['inventario.db', 'televisores.db']

print("=== DIAGNÓSTICO DE ARCHIVOS SQLITE ===")
for archivo in archivos_sqlite:
    if os.path.exists(archivo):
        print(f"\n📂 Analizando archivo: {archivo}")
        try:
            conn = sqlite3.connect(archivo)
            cursor = conn.cursor()
            
            # Ver todas las tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tablas = [t[0] for t in cursor.fetchall()]
            print(f"   Tablas encontradas: {tablas}")
            
            for tabla in tablas:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla};")
                count = cursor.fetchone()[0]
                print(f"   - Tabla '{tabla}': {count} registros")
                
                # Mostrar las columnas de la tabla
                cursor.execute(f"PRAGMA table_info({tabla});")
                columnas = [col[1] for col in cursor.fetchall()]
                print(f"     Columnas: {columnas}")
            
            conn.close()
        except Exception as e:
            print(f"   ❌ Error al leer {archivo}: {e}")
    else:
        print(f"\n📂 El archivo {archivo} NO existe en esta carpeta.")
print("\n=======================================")