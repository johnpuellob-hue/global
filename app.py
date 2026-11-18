from datetime import timedelta
import html
import os
import random
import sqlite3

import pandas as pd
from flask import Flask, redirect, render_template, request, send_file, flash, url_for, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'g-global-studios-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=60)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=60)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "estudio_global.db")
DATABASE_URL = os.environ.get('DATABASE_URL')

def is_postgres():
    return bool(DATABASE_URL and (DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://')))

class DBRow:
    """Permite acceder a los datos de la fila como dict row['col'] o tupla row[0]."""
    def __init__(self, data, description):
        self._data = data
        self._desc = [d[0] for d in description] if description else []
        self._dict = {k: v for k, v in zip(self._desc, data)} if description else {}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._data[key]
        return self._dict[key]

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def keys(self):
        return self._dict.keys()

class DBCursor:
    def __init__(self, cursor, is_pg=False):
        self.cursor = cursor
        self.is_pg = is_pg

    def execute(self, sql, params=None):
        if self.is_pg:
            sql = sql.replace('?', '%s')
        if params is not None:
            return self.cursor.execute(sql, params)
        return self.cursor.execute(sql)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        if self.is_pg:
            return DBRow(row, self.cursor.description)
        return row

    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.is_pg:
            desc = self.cursor.description
            return [DBRow(r, desc) for r in rows]
        return rows

    @property
    def rowcount(self):
        return self.cursor.rowcount

class DBConnection:
    def __init__(self, raw_conn, is_pg=False):
        self.raw_conn = raw_conn
        self.is_pg = is_pg

    def cursor(self):
        return DBCursor(self.raw_conn.cursor(), self.is_pg)

    def commit(self):
        self.raw_conn.commit()

    def rollback(self):
        self.raw_conn.rollback()

    def close(self):
        self.raw_conn.close()

def get_db():
    if is_postgres():
        import psycopg2
        url = DATABASE_URL
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        raw = psycopg2.connect(url)
        return DBConnection(raw, is_pg=True)
    else:
        raw = sqlite3.connect(DB_PATH)
        raw.row_factory = sqlite3.Row
        return DBConnection(raw, is_pg=False)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'info'

# Catálogo único de servicios (clave -> (nombre bonito, precio))
SERVICIOS = {
    "desarrollo_web": ("Desarrollo Web", 300000),
    "automatizacion_ia": ("Automatización con IA", 250000),
    "gestion_datos": ("Gestión de Datos", 200000),
}

# Sub-servicios por categoría
SUB_SERVICIOS = {
    "desarrollo_web": [
        ("creacion_sitio", "Creación de sitio web desde cero", 300000),
        ("mantenimiento_soporte", "Mantenimiento y soporte mensual", 150000),
        ("actualizacion_codigo", "Actualización y mejoras de código", 200000),
    ],
    "automatizacion_ia": [
        ("automatizacion_procesos", "Automatización de procesos empresariales", 250000),
        ("chatbots_asistentes", "Chatbots y asistentes virtuales IA", 200000),
        ("analisis_datos_ia", "Análisis de datos con IA/ML", 300000),
    ],
    "gestion_datos": [
        ("migracion_datos", "Migración y limpieza de datos", 180000),
        ("dashboards_reportes", "Dashboards y reportes automatizados", 220000),
        ("bases_datos_admin", "Administración de bases de datos", 200000),
    ],
}

# Alias para aceptar tanto los values nuevos (claves) como los textos
# que enviaba el formulario antiguo de index.html
ALIASES = {
    "desarrollo web": "desarrollo_web",
    "automatización": "automatizacion_ia",
    "automatizacion": "automatizacion_ia",
    "automatización con ia": "automatizacion_ia",
    "automatización con python": "automatizacion_ia",
    "automatizacion con python": "automatizacion_ia",
    "gestión de datos": "gestion_datos",
    "gestion de datos": "gestion_datos",
    "gestión de redes": "gestion_datos",
    "gestion de redes": "gestion_datos",
}
# Las propias claves también son válidas
for _k in SERVICIOS:
    ALIASES[_k] = _k


def normalizar_servicio(valor):
    clave = (valor or "").strip().lower()
    clave = ALIASES.get(clave, clave)
    if clave in SERVICIOS:
        return clave, SERVICIOS[clave][0], SERVICIOS[clave][1]
    
    # Buscar en sub-servicios
    for cat, subs in SUB_SERVICIOS.items():
        for sub_clave, sub_nombre, sub_precio in subs:
            if clave == sub_clave or clave == sub_nombre.lower():
                return f"{cat}:{sub_clave}", sub_nombre, sub_precio
    
    return None, "Servicio General", 0


# Función para crear la base de datos (ventas + mensajes + usuarios)
def crear_db():
    conexion = get_db()
    cursor = conexion.cursor()
    
    if conexion.is_pg:
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            telefono TEXT,
            is_admin INTEGER DEFAULT 0,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES usuarios (id),
            nombre TEXT,
            servicio TEXT,
            sub_servicio TEXT,
            total REAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensajes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES usuarios (id),
            nombre TEXT, email TEXT, telefono TEXT,
            servicio TEXT, mensaje TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    else:
        cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           nombre TEXT NOT NULL,
                           email TEXT UNIQUE NOT NULL,
                           password_hash TEXT NOT NULL,
                           telefono TEXT,
                           is_admin INTEGER DEFAULT 0,
                           fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           user_id INTEGER,
                           nombre TEXT,
                           servicio TEXT,
                           sub_servicio TEXT,
                           total REAL,
                           fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           FOREIGN KEY (user_id) REFERENCES usuarios (id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensajes
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           user_id INTEGER,
                           nombre TEXT, email TEXT, telefono TEXT,
                           servicio TEXT, mensaje TEXT,
                           fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           FOREIGN KEY (user_id) REFERENCES usuarios (id))''')
        
        # Migraciones: agregar columnas si no existen en bases de datos previas
        for tabla, columnas in [
            ('usuarios', [('is_admin', 'INTEGER DEFAULT 0')]),
            ('ventas', [('user_id', 'INTEGER'), ('sub_servicio', 'TEXT'), ('fecha', 'TIMESTAMP')]),
            ('mensajes', [('user_id', 'INTEGER'), ('fecha', 'TIMESTAMP')])
        ]:
            for col, col_type in columnas:
                try:
                    cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {col_type}")
                except Exception:
                    pass
        
        try:
            cursor.execute("UPDATE ventas SET fecha = CURRENT_TIMESTAMP WHERE fecha IS NULL")
            cursor.execute("UPDATE mensajes SET fecha = CURRENT_TIMESTAMP WHERE fecha IS NULL")
        except Exception:
            pass

    # Asegurar que el usuario administrador del dueño siempre existe y tiene rol admin
    admin_email = 'puellobatista02@hotmail.com'
    try:
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (admin_email,))
        admin_row = cursor.fetchone()
        if not admin_row:
            pw_hash = generate_password_hash('password123')
            cursor.execute(
                "INSERT INTO usuarios (nombre, email, password_hash, is_admin) VALUES (?, ?, ?, 1)",
                ('John Jairo Puello', admin_email, pw_hash)
            )
        else:
            cursor.execute("UPDATE usuarios SET is_admin = 1 WHERE email = ?", (admin_email,))
        conexion.commit()
    except Exception as e:
        print(f"Aviso al asegurar admin: {e}")
        try:
            conexion.rollback()
        except Exception:
            pass
    finally:
        conexion.close()


crear_db()


# User model para Flask-Login
class User(UserMixin):
    def __init__(self, id, nombre, email, password_hash, telefono=None, is_admin=False):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.password_hash = password_hash
        self.telefono = telefono
        self.is_admin = bool(is_admin)

    @staticmethod
    def get_by_id(user_id):
        conexion = get_db()
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conexion.close()
        if row:
            return User(row['id'], row['nombre'], row['email'], row['password_hash'], row['telefono'], row['is_admin'])
        return None

    @staticmethod
    def get_by_email(email):
        conexion = get_db()
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        row = cursor.fetchone()
        conexion.close()
        if row:
            return User(row['id'], row['nombre'], row['email'], row['password_hash'], row['telefono'], row['is_admin'])
        return None

    @staticmethod
    def create(nombre, email, password, telefono=None, is_admin=False):
        password_hash = generate_password_hash(password)
        conexion = get_db()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (nombre, email, password_hash, telefono, is_admin) VALUES (?, ?, ?, ?, ?)",
                (nombre, email, password_hash, telefono, 1 if is_admin else 0)
            )
            conexion.commit()
            conexion.close()
            return User.get_by_email(email)
        except Exception as e:
            print(f"Error creando usuario: {e}")
            try:
                conexion.rollback()
            except Exception:
                pass
            conexion.close()
            return None

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


# Decorador para rutas solo admin
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function


def generar_frase_ia(nombre, nombre_servicio):
    """Intenta usar la API nueva de OpenAI; si no hay llave o falla, frase local."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            prompt = (
                f"Genera una frase de impacto de máximo 20 palabras para el cliente "
                f"{nombre} que acaba de contratar {nombre_servicio}. Usa un tono futurista."
            )
            respuesta = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
            )
            texto = respuesta.choices[0].message.content
            if texto:
                return texto.strip()
        except Exception as e:
            print(f"OpenAI no disponible, usando frase local: {e}")
    opciones = [
        f"¡{nombre}, el futuro de tu marca despega hoy con {nombre_servicio}!",
        f"G-Global Studios: Innovación para {nombre}.",
    ]
    return random.choice(opciones)


@app.route('/')
def inicio():
    return render_template('index.html')


@app.route('/servicios')
def servicios():
    return render_template('servicios.html')


@app.route('/nosotros')
def nosotros():
    return render_template('nosotros.html')


@app.route('/testimonios')
def testimonios():
    return render_template('testimonios.html')


@app.route('/contacto')
def contacto():
    return render_template('contacto.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('inicio'))
    
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        remember = request.form.get('remember', 'on') == 'on'
        
        if not email or not password:
            flash('Email y contraseña son obligatorios.', 'error')
            return render_template('login.html')
        
        user = User.get_by_email(email)
        if user and user.check_password(password):
            session.permanent = True
            login_user(user, remember=remember)
            flash(f'¡Bienvenido de nuevo, {user.nombre}!', 'success')
            next_page = request.form.get('next') or request.args.get('next')
            return redirect(next_page or url_for('inicio'))
        else:
            flash('Email o contraseña incorrectos.', 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('inicio'))
    
    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        password2 = request.form.get('password2') or ''
        telefono = (request.form.get('telefono') or '').strip()
        
        if not nombre or not email or not password:
            flash('Todos los campos son obligatorios.', 'error')
            return render_template('register.html')
        
        if password != password2:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
            return render_template('register.html')
        
        es_admin_principal = (email == 'puellobatista02@hotmail.com')
        user = User.create(nombre, email, password, telefono, is_admin=es_admin_principal)
        if user:
            session.permanent = True
            login_user(user, remember=True)
            flash(f'¡Cuenta creada exitosamente! Bienvenido, {nombre}.', 'success')
            next_page = request.form.get('next') or request.args.get('next')
            return redirect(next_page or url_for('inicio'))
        else:
            flash('Este email ya está registrado.', 'error')
    
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('inicio'))


@app.route('/enviar-mensaje', methods=['POST'])
def enviar_mensaje():
    nombre = (request.form.get('nombre') or '').strip()
    email = (request.form.get('email') or '').strip()
    telefono = (request.form.get('telefono') or '').strip()
    servicio = (request.form.get('servicio') or '').strip()
    mensaje = (request.form.get('mensaje') or '').strip()
    
    if not nombre or not email or not mensaje:
        return "Faltan campos obligatorios (nombre, email, mensaje).", 400
    
    user_id = current_user.id if current_user.is_authenticated else None
    
    try:
        conexion = get_db()
        cursor = conexion.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensajes
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           user_id INTEGER,
                           nombre TEXT, email TEXT, telefono TEXT,
                           servicio TEXT, mensaje TEXT,
                           fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           FOREIGN KEY (user_id) REFERENCES usuarios (id))''')
        cursor.execute(
            "INSERT INTO mensajes (user_id, nombre, email, telefono, servicio, mensaje) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, nombre, email, telefono, servicio, mensaje))
        conexion.commit()
        conexion.close()
    except Exception as e:
        print(f"Error: {e}")
        return "Error guardando el mensaje, intenta de nuevo.", 500
    
    nombre_seguro = html.escape(nombre)
    return f"""
    <html>
    <head>
        <style>
            body {{ background: #000; color: white; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .mensaje {{ text-align: center; }}
            h1 {{ color: #39FF14; }}
            a {{ color: #39FF14; }}
        </style>
    </head>
    <body>
        <div class="mensaje">
            <h1>¡Mensaje Enviado!</h1>
            <p>Gracias {nombre_seguro}, nos pondremos en contacto pronto.</p>
            <p style="color:#888;font-size:14px;">Tu mensaje quedó guardado en nuestra base de datos.</p>
            <a href="/contacto">Volver</a>
        </div>
    </body>
    </html>
    """


@app.route('/cotizar', methods=['GET', 'POST'])
@login_required
def cotizar():
    if request.method == 'GET':
        return redirect('/')
    
    # Usar nombre del usuario logueado automáticamente
    nombre = current_user.nombre
    # Acepta el formato nuevo (servicio_id) y el antiguo (servicio)
    servicio_raw = request.form.get('servicio_id') or request.form.get('servicio') or ''
    sub_servicio_raw = request.form.get('sub_servicio') or ''
    es_referido = request.form.get('referido')
    
    _clave, nombre_servicio_limpio, subtotal = normalizar_servicio(servicio_raw)
    
    # Si es un sub-servicio, extraer el nombre del sub-servicio
    sub_servicio_nombre = None
    if _clave and ':' in _clave:
        cat, sub_clave = _clave.split(':', 1)
        for sub in SUB_SERVICIOS.get(cat, []):
            if sub[0] == sub_clave:
                sub_servicio_nombre = sub[1]
                break
    
    descuento = subtotal * 0.10 if es_referido == "S" else 0
    total = subtotal - descuento
    
    # Guardar en base de datos
    try:
        conexion = get_db()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO ventas (user_id, nombre, servicio, sub_servicio, total) VALUES (?, ?, ?, ?, ?)",
                       (current_user.id, nombre, nombre_servicio_limpio, sub_servicio_nombre, total))
        conexion.commit()
        conexion.close()
    except Exception as e:
        print(f"Error al guardar en DB: {e}")
        return "Error guardando la cotización.", 500
    
    frase_ia = generar_frase_ia(nombre, nombre_servicio_limpio)
    
    nombre_seguro = html.escape(nombre.upper())
    servicio_seguro = html.escape(nombre_servicio_limpio)
    sub_servicio_seguro = html.escape(sub_servicio_nombre) if sub_servicio_nombre else ""
    frase_segura = html.escape(frase_ia)
    
    return f"""
    <html>
    <head>
        <style>
            body {{ background: #000; color: white; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .tarjeta {{ border: 2px solid #39FF14; padding: 40px; border-radius: 20px; box-shadow: 0 0 30px #39FF14; background: #050505; text-align: center; width: 450px; }}
            h1 {{ color: #39FF14; text-transform: uppercase; letter-spacing: 2px; }}
            .frase {{ font-style: italic; color: #888; margin: 20px 0; border-left: 3px solid #39FF14; padding-left: 10px; }}
            .total {{ font-size: 24px; font-weight: bold; color: #39FF14; }}
            .btn {{ display: inline-block; margin-top: 20px; padding: 10px 20px; border: 1px solid #39FF14; color: #39FF14; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="tarjeta">
            <h1>G-GLOBAL STUDIOS</h1>
            <p>Propuesta personalizada para:</p>
            <h2 style="margin:0;">{nombre_seguro}</h2>
            <div class="frase">"{frase_segura}"</div>
            <p>Servicio: {servicio_seguro}</p>
            {f'<p>Sub-servicio: {sub_servicio_seguro}</p>' if sub_servicio_seguro else ''}
            <p>Subtotal: ${subtotal:,.0f}</p>
            <p style="color: #ff4444;">Descuento: -${descuento:,.0f}</p>
            <div class="total">TOTAL A PAGAR: ${total:,.0f}</div>
            <a href="/" class="btn">NUEVA COTIZACIÓN</a>
        </div>
    </body>
    </html>
    """


@app.route('/reportes')
@login_required
def reportes():
    conexion = get_db()
    cursor = conexion.cursor()
    # Solo mostrar cotizaciones del usuario actual
    cursor.execute("SELECT id, nombre, servicio, sub_servicio, total, fecha FROM ventas WHERE user_id = ? ORDER BY fecha DESC", (current_user.id,))
    datos_ventas = cursor.fetchall()
    conexion.close()
    return render_template('reportes.html', registros=datos_ventas)


@app.route('/mensajes')
@login_required
def ver_mensajes():
    """Vista admin simple para verificar los mensajes de contacto guardados."""
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, email, telefono, servicio, mensaje, fecha FROM mensajes WHERE user_id = ? ORDER BY fecha DESC", (current_user.id,))
    datos = cursor.fetchall()
    conexion.close()
    return render_template('mensajes.html', registros=datos)


@app.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM ventas WHERE id = ? AND user_id = ?", (id, current_user.id))
    conexion.commit()
    conexion.close()
    return redirect('/reportes')


@app.route('/descargar_excel')
@login_required
def descargar_excel():
    conexion = get_db()
    sql = "SELECT nombre, servicio, sub_servicio, total, fecha FROM ventas WHERE user_id = ?"
    if conexion.is_pg:
        sql = sql.replace('?', '%s')
    df = pd.read_sql_query(sql, conexion.raw_conn, params=(current_user.id,))
    conexion.close()
    nombre_archivo = os.path.join(BASE_DIR, "Reporte_G-Global_Studios.xlsx")
    df.to_excel(nombre_archivo, index=False)
    return send_file(nombre_archivo, as_attachment=True)


# ==================== PANEL ADMIN ====================
@app.route('/admin/descargar_bd')
@login_required
@admin_required
def admin_descargar_bd():
    """Permite al administrador descargar la base de datos."""
    if is_postgres():
        flash("La base de datos está guardada permanentemente en la nube (PostgreSQL).", "info")
        return redirect(url_for('admin_dashboard'))
    if os.path.exists(DB_PATH):
        return send_file(DB_PATH, as_attachment=True, download_name="estudio_global.db")
    flash("El archivo de base de datos no existe aún.", "error")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    conexion = get_db()
    cursor = conexion.cursor()
    
    # Estadísticas generales
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ventas")
    total_cotizaciones = cursor.fetchone()[0]
    
    cursor.execute("SELECT COALESCE(SUM(total), 0) FROM ventas")
    total_ingresos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM mensajes")
    total_mensajes = cursor.fetchone()[0]
    
    # Últimos usuarios
    cursor.execute("SELECT id, nombre, email, is_admin, fecha_registro FROM usuarios ORDER BY fecha_registro DESC LIMIT 10")
    ultimos_usuarios = cursor.fetchall()
    
    # Últimas cotizaciones
    cursor.execute("""SELECT v.id, v.nombre, v.servicio, v.sub_servicio, v.total, v.fecha, u.email 
                      FROM ventas v 
                      JOIN usuarios u ON v.user_id = u.id 
                      ORDER BY v.fecha DESC LIMIT 10""")
    ultimas_cotizaciones = cursor.fetchall()
    
    # Últimos mensajes
    cursor.execute("""SELECT m.id, m.nombre, m.email, m.servicio, m.mensaje, m.fecha, u.email 
                      FROM mensajes m 
                      LEFT JOIN usuarios u ON m.user_id = u.id 
                      ORDER BY m.fecha DESC LIMIT 10""")
    ultimos_mensajes = cursor.fetchall()
    
    conexion.close()
    
    return render_template('admin.html',
                           total_usuarios=total_usuarios,
                           total_cotizaciones=total_cotizaciones,
                           total_ingresos=total_ingresos,
                           total_mensajes=total_mensajes,
                           ultimos_usuarios=ultimos_usuarios,
                           ultimas_cotizaciones=ultimas_cotizaciones,
                           ultimos_mensajes=ultimos_mensajes)


@app.route('/admin/usuarios')
@login_required
@admin_required
def admin_usuarios():
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, email, telefono, is_admin, fecha_registro FROM usuarios ORDER BY fecha_registro DESC")
    usuarios = cursor.fetchall()
    conexion.close()
    return render_template('admin_usuarios.html', usuarios=usuarios)


@app.route('/admin/cotizaciones')
@login_required
@admin_required
def admin_cotizaciones():
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("""SELECT v.id, v.nombre, v.servicio, v.sub_servicio, v.total, v.fecha, u.nombre as user_nombre, u.email as user_email 
                      FROM ventas v 
                      JOIN usuarios u ON v.user_id = u.id 
                      ORDER BY v.fecha DESC""")
    cotizaciones = cursor.fetchall()
    conexion.close()
    return render_template('admin_cotizaciones.html', cotizaciones=cotizaciones)


@app.route('/admin/mensajes')
@login_required
@admin_required
def admin_mensajes():
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("""SELECT m.id, m.nombre, m.email, m.telefono, m.servicio, m.mensaje, m.fecha, u.nombre as user_nombre 
                      FROM mensajes m 
                      LEFT JOIN usuarios u ON m.user_id = u.id 
                      ORDER BY m.fecha DESC""")
    mensajes = cursor.fetchall()
    conexion.close()
    return render_template('admin_mensajes.html', mensajes=mensajes)


@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_toggle_admin(user_id):
    if user_id == current_user.id:
        flash('No puedes quitarte tus propios permisos de admin.', 'error')
        return redirect(url_for('admin_usuarios'))
    
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("UPDATE usuarios SET is_admin = 1 - is_admin WHERE id = ?", (user_id,))
    conexion.commit()
    conexion.close()
    flash('Permisos de administrador actualizados.', 'success')
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/eliminar_usuario/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_eliminar_usuario(user_id):
    if user_id == current_user.id:
        flash('No puedes eliminarte a ti mismo.', 'error')
        return redirect(url_for('admin_usuarios'))
    
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conexion.commit()
    conexion.close()
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('admin_usuarios'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)