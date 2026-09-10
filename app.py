import html
import os
import random
import sqlite3

import pandas as pd
from flask import Flask, redirect, render_template, request, send_file

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "estudio_global.db")

# Catálogo único de servicios (clave -> (nombre bonito, precio))
SERVICIOS = {
    "marketing_digital": ("Marketing Digital", 150000),
    "desarrollo_web": ("Desarrollo Web", 300000),
    "gestion_redes": ("Gestión de Redes", 200000),
    "automatizacion_ia": ("Automatización con IA", 250000),
    "diseno_grafico": ("Diseño Gráfico", 100000),
    "produccion_audiovisual": ("Producción Audiovisual", 180000),
}

# Alias para aceptar tanto los values nuevos (claves) como los textos
# que enviaba el formulario antiguo de index.html
ALIASES = {
    "marketing digital": "marketing_digital",
    "desarrollo web": "desarrollo_web",
    "gestión de redes": "gestion_redes",
    "gestion de redes": "gestion_redes",
    "automatización": "automatizacion_ia",
    "automatizacion": "automatizacion_ia",
    "automatización con ia": "automatizacion_ia",
    "automatización con python": "automatizacion_ia",
    "automatizacion con python": "automatizacion_ia",
    "diseño gráfico": "diseno_grafico",
    "diseno grafico": "diseno_grafico",
    "producción audiovisual": "produccion_audiovisual",
    "produccion audiovisual": "produccion_audiovisual",
}
# Las propias claves también son válidas
for _k in SERVICIOS:
    ALIASES[_k] = _k


def normalizar_servicio(valor):
    clave = (valor or "").strip().lower()
    clave = ALIASES.get(clave, clave)
    if clave in SERVICIOS:
        return clave, SERVICIOS[clave][0], SERVICIOS[clave][1]
    return None, "Servicio General", 0


def get_db():
    conexion = sqlite3.connect(DB_PATH)
    return conexion


# Función para crear la base de datos (ventas + mensajes)
def crear_db():
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       nombre TEXT,
                       servicio TEXT,
                       total REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS mensajes
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       nombre TEXT, email TEXT, telefono TEXT,
                       servicio TEXT, mensaje TEXT)''')
    conexion.commit()
    conexion.close()


crear_db()


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


@app.route('/enviar-mensaje', methods=['POST'])
def enviar_mensaje():
    nombre = (request.form.get('nombre') or '').strip()
    email = (request.form.get('email') or '').strip()
    telefono = (request.form.get('telefono') or '').strip()
    servicio = (request.form.get('servicio') or '').strip()
    mensaje = (request.form.get('mensaje') or '').strip()

    if not nombre or not email or not mensaje:
        return "Faltan campos obligatorios (nombre, email, mensaje).", 400

    try:
        conexion = get_db()
        cursor = conexion.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensajes
                          (id INTEGER PRIMARY KEY AUTOINCREMENT,
                           nombre TEXT, email TEXT, telefono TEXT,
                           servicio TEXT, mensaje TEXT)''')
        cursor.execute(
            "INSERT INTO mensajes (nombre, email, telefono, servicio, mensaje) VALUES (?, ?, ?, ?, ?)",
            (nombre, email, telefono, servicio, mensaje))
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
def cotizar():
    if request.method == 'GET':
        # Los botones de servicios.html apuntaban aquí; el formulario vive en /
        return redirect('/')

    nombre = (request.form.get('nombre') or '').strip()
    # Acepta el formato nuevo (servicio_id) y el antiguo (servicio)
    servicio_raw = request.form.get('servicio_id') or request.form.get('servicio') or ''
    es_referido = request.form.get('referido')

    if not nombre:
        return "El nombre es obligatorio.", 400

    _clave, nombre_servicio_limpio, subtotal = normalizar_servicio(servicio_raw)
    descuento = subtotal * 0.10 if es_referido == "S" else 0
    total = subtotal - descuento

    # Guardar en base de datos
    try:
        conexion = get_db()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO ventas (nombre, servicio, total) VALUES (?, ?, ?)",
                       (nombre, nombre_servicio_limpio, total))
        conexion.commit()
        conexion.close()
    except Exception as e:
        print(f"Error al guardar en DB: {e}")
        return "Error guardando la cotización.", 500

    frase_ia = generar_frase_ia(nombre, nombre_servicio_limpio)

    nombre_seguro = html.escape(nombre.upper())
    servicio_seguro = html.escape(nombre_servicio_limpio)
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
            <p>Subtotal: ${subtotal:,.0f}</p>
            <p style="color: #ff4444;">Descuento: -${descuento:,.0f}</p>
            <div class="total">TOTAL A PAGAR: ${total:,.0f}</div>
            <a href="/" class="btn">NUEVA COTIZACIÓN</a>
        </div>
    </body>
    </html>
    """


@app.route('/reportes')
def reportes():
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, servicio, total FROM ventas")
    datos_ventas = cursor.fetchall()
    conexion.close()
    return render_template('reportes.html', registros=datos_ventas)


@app.route('/mensajes')
def ver_mensajes():
    """Vista admin simple para verificar los mensajes de contacto guardados."""
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, email, telefono, servicio, mensaje FROM mensajes ORDER BY id DESC")
    datos = cursor.fetchall()
    conexion.close()
    return render_template('mensajes.html', registros=datos)


@app.route('/eliminar/<int:id>')
def eliminar(id):
    conexion = get_db()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM ventas WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()
    return redirect('/reportes')


@app.route('/descargar_excel')
def descargar_excel():
    conexion = get_db()
    df = pd.read_sql_query("SELECT nombre, servicio, total FROM ventas", conexion)
    conexion.close()
    nombre_archivo = os.path.join(BASE_DIR, "Reporte_G-Global_Studios.xlsx")
    df.to_excel(nombre_archivo, index=False)
    return send_file(nombre_archivo, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
