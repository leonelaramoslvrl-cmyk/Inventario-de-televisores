# Inventario de televisores — backend Python (Flask) + PostgreSQL (Neon)

Versión completamente independiente de Claude, hecha con software libre:

- **Backend:** Python + [Flask](https://flask.palletsprojects.com/) (framework web gratuito y open source)
- **Base de datos:** [PostgreSQL](https://www.postgresql.org/), alojada gratis y por separado en [Neon](https://neon.tech) — la base de datos vive en su propio servidor, independiente de donde alojes la app, y sigue funcionando aunque reinicies o cambies el hosting del backend
- **Frontend:** HTML + CSS + JavaScript planos, con las librerías gratuitas [SheetJS](https://sheetjs.com/) (exportar a Excel) y [jsQR](https://github.com/cozmo/jsQR) (leer códigos QR desde fotos)

## Estructura de archivos

```
inventario-app/
├── app.py                 ← Backend Flask (rutas /, /api/tvs)
├── requirements.txt       ← Dependencias de Python
├── .env.example           ← Plantilla para tu cadena de conexión (sin secretos)
├── templates/
│   └── index.html         ← Estructura de la página
└── static/
    ├── style.css          ← Todos los estilos
    └── script.js          ← Toda la lógica de la app (formulario, pisos, QR, Excel)
```

## 1. Crear tu base de datos gratis en Neon

1. Ve a https://neon.tech y crea una cuenta gratuita.
2. Crea un nuevo proyecto (te da automáticamente una base de datos llamada `neondb`).
3. En el panel del proyecto, busca **"Connection string"** (cadena de conexión). Cópiala completa — se ve algo así:
   ```
   postgresql://usuario:contraseña@ep-xxxxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. **Guarda esa cadena en un lugar seguro** — es la contraseña de tu base de datos.

## 2. Configurar el proyecto con tu cadena de conexión

1. Dentro de la carpeta `inventario-app`, copia el archivo `.env.example` y renómbralo a `.env`.
2. Abre `.env` y reemplaza el valor de `DATABASE_URL` por la cadena que copiaste de Neon.
3. **Nunca compartas el archivo `.env` real** (solo `.env.example`, que no tiene datos sensibles) — por eso la contraseña nunca está escrita dentro de `app.py`.

## 3. Correrlo en tu computadora

```
pip install -r requirements.txt
python app.py
```

La primera vez que arranca, crea automáticamente la tabla `tvs` en tu base de
datos de Neon si no existe. Abre `http://localhost:5000` en el navegador.

## 4. Desplegarlo para usarlo desde el celular sin dejar una terminal abierta

Con la base de datos ya en Neon (fuera de tu computadora), solo necesitas
alojar el backend Flask en algún lado gratis, por ejemplo:

- **PythonAnywhere** (https://www.pythonanywhere.com) — sube estos archivos, y en la configuración de tu Web App agrega la variable de entorno `DATABASE_URL` (pestaña "Web" → sección "Environment variables") con la misma cadena de conexión de Neon. No necesitas usar `.env` ahí, solo esa variable de entorno.
- **Render** o **Railway** — ambos permiten definir variables de entorno (`DATABASE_URL`) desde su panel, de la misma forma.

En cualquiera de estas opciones, como la base de datos vive en Neon (no en el
servidor de la app), tus datos son seguros incluso si el servidor gratuito se
reinicia, se duerme, o lo migras a otro proveedor más adelante.

## Seguridad

- La contraseña de la base de datos **nunca** está escrita en el código — solo existe en la variable de entorno `DATABASE_URL`, que configuras por separado en cada lugar donde corras la app.
- La conexión a Neon siempre usa `sslmode=require` (cifrada).
- No se pueden borrar registros desde la interfaz (a propósito, para evitar errores) — solo editar.

## ⚠️ Aviso importante

Este código sigue el patrón estándar y bien documentado de `psycopg2` para
conectarse a PostgreSQL, pero no pude probarlo contra un servidor Postgres
real en este entorno (sin acceso a internet para instalar el driver o
conectarme a Neon). Antes de usarlo en producción, ejecútalo una vez con tus
credenciales reales y confirma que crear, editar y listar registros funciona
correctamente.
"# Inventario-de-televisores" 
