# -*- coding: utf-8 -*-
import os
import psycopg2

# Conexión directa a tu base de datos Neon
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_e0lH1htOjFzT@ep-blue-term-bfbq01c5-pooler.c-5.us-west-2.aws.neon.tech/neondb?sslmode=require'
)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Lista completa de registros parseados
registros = [
    # PISO 1
    ("103", "Habitación", "Samsung", "QN50Q7FAAPXPA", "0JPW3CBY601287Z", "Inalámbrica", "Sí", "Sí", "—", "Base fija"),
    ("104", "Habitación", "Samsung", "QN50Q7FAAPXPA", "0JPW3CVY700716R", "Cableado", "Sí", "Sí", "Ya tiene intergo instalado solo falta configurarlo", "Base fija"),
    ("105", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM402785X", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("106", "Habitación", "Samsung", "QN50Q7FAAPXPA", "0JPW3CVY700718W", "Inalámbrica", "Sí", "Sí", "Intergo instalado solo falta configurarlo", "Base fija"),
    ("107", "Habitación", "Samsung", "UN50AU7090PXPA", "-", "Inalámbrica", "No", "Sí", "No sé pueden ver el número de serie está en la parte de atrás del televisor. Intergo instalado pero falta configurar lo", "Base fija"),
    ("109", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC00541Z", "Inalámbrica", "Sí", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("113", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01343R", "Inalámbrica", "Sí", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("114", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM402778Y", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("115", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403109F", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("120TV 1/4", "Sala", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01169T", "Inalámbrica", "Sí", "No", "No aparece en la tienda de aplicaciones", "Base fija"),
    ("120TV 2/4", "Habitación complementaria", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC00687K", "Inalámbrica", "Sí", "No", "Intergo no aparece en la tienda de aplicaciones.", "Base movible"),
    ("120TV 3/4", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC00593E", "Inalámbrica", "Sí", "No", "Intergo no aparece en la tienda de aplicaciones", "Escritorio/Mueble"),
    ("120TV 4/4", "Habitación", "Samsung", "UN55CU8000DXZA", "0FAU3CYW900293Z", "Inalámbrica", "Sí", "Sí", "—", "Base fija"),
    ("125", "Habitación", "Samsung", "UN50AU7090PXPA", "-", "Inalámbrica", "No", "Sí", "No aparece el serial y falta configurar intergo", "Base fija"),
    ("127", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM402752Y", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("129", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM402753W", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("132", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM402985R", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("133", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403129M", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Escritorio/Mueble"),
    ("134", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403105B", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("135", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01062X", "Cableado", "Sí", "Sí", "—", "Escritorio/Mueble"),
    ("137", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01277W", "Inalámbrica", "Sí", "Sí", "—", "Escritorio/Mueble"),
    ("142", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM402782E", "—", "No", "No", "No reconoce los periféricos y no aparece intergo", "Escritorio/Mueble"),
    ("143", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC00656A", "Inalámbrica", "Sí", "Sí", "—", "Escritorio/Mueble"),
    ("144", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403103M", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base fija"),
    ("148", "Habitación", "Samsung", "UN50DU7000PXPA", "0GUQ3CVX600205F", "Inalámbrica", "No", "Sí", "Tiene instalado intergo pero falta configurarlo", "Escritorio/Mueble"),
    ("161", "Habitación", "Samsung", "UN50AU7090PXPA", "-", "Inalámbrica", "No", "Sí", "El número de serie está en la parte de atrás del televisor", "Base fija"),

    # PISO 2
    ("201", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01205W", "Inalámbrica", "Sí", "Sí", "—", "Base movible"),
    ("222", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM402628F", "—", "—", "—", "—", "Base fija"),
    ("250", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01134F", "Inalámbrica", "—", "—", "—", "Base fija"),

    # PISO 3
    ("315", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403090J", "Cableado", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("317TV 1/2", "Sala", "Samsung", "UN50AU7090PXPA", "-", "Cableado", "No", "Sí", "El serial está en la parte de atrás del televisor", "Base fija"),
    ("317TV 2/2", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC00509B", "Cableado", "Sí", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("318", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01120H", "Cableado", "Sí", "Sí", "—", "Base movible"),
    ("327", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403036V", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("329", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM402992W", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("331", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403042N", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("333", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403092T", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("339", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01160L", "Inalámbrica", "Sí", "Sí", "—", "Base movible"),
    ("342", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403044J", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("343", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC00520R", "Inalámbrica", "Sí", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("344", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403100V", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("346", "Habitación", "Samsung", "UN50NU7090", "07VL3CXM403046T", "Inalámbrica", "No", "No", "Intergo no aparece en la tienda de aplicaciones", "Base movible"),
    ("347", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC00445X", "Inalámbrica", "Sí", "—", "No agarra internet", "Base movible"),

    # PISO 5
    ("509", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC00489A", "—", "—", "—", "—", "Base fija"),
    ("532", "Habitación", "Samsung", "UN50RU7100PXPA", "08EJ3CXMC01271N", "—", "—", "—", "—", "Base fija")
]

def migrar():
    print("Conectando a la base de datos Neon...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # 1. Asegurar que la tabla existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tv_inventario (
                id SERIAL PRIMARY KEY,
                room VARCHAR(50),
                ubicacion VARCHAR(100),
                marca VARCHAR(50),
                modelo VARCHAR(100),
                serial VARCHAR(100),
                conexion VARCHAR(50),
                perifericos VARCHAR(50),
                intergo VARCHAR(50),
                comentarios TEXT,
                instalacion VARCHAR(100)
            );
        """)

        # 2. Insertar registros
        print(f"Insertando {len(registros)} registros...")
        for r in registros:
            cursor.execute("""
                INSERT INTO tv_inventario (room, ubicacion, marca, modelo, serial, conexion, perifericos, intergo, comentarios, instalacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, r)

        conn.commit()
        cursor.close()
        conn.close()
        print(f"¡Éxito total! Se han importado los {len(registros)} registros correctamente a Neon.")

    except Exception as e:
        print(f"Error al importar los datos: {e}")

if __name__ == "__main__":
    migrar()