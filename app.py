import pandas as pd
import sqlite3
import sqlite3
import random
import openai
from flask import Flask, render_template, request, redirect, send_file

app = Flask(__name__)

# Función para crear la base de datos
def crear_db():
    conexion = sqlite3.connect("estudio_global.db")
    cursor = conexion.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       nombre TEXT, 
                       servicio TEXT, 
                       total REAL)''')
    conexion.commit()
    conexion.close()

crear_db()

#  llave de OpenAI
openai.api_key = "TU_LLAVE_AQUI" # Asegúrate de tener tu llave activa

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
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    telefono = request.form.get('telefono')
    servicio = request.form.get('servicio')
    mensaje = request.form.get('mensaje')
    
    try:
        conexion = sqlite3.connect("estudio_global.db")
        cursor = conexion.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensajes 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                           nombre TEXT, email TEXT, telefono TEXT, 
                           servicio TEXT, mensaje TEXT)''')
        cursor.execute("INSERT INTO mensajes (nombre, email, telefono, servicio, mensaje) VALUES (?, ?, ?, ?, ?)",
                       (nombre, email, telefono, servicio, mensaje))
        conexion.commit()
        conexion.close()
    except Exception as e:
        print(f"Error: {e}")
    
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
            <p>Gracias {nombre}, nos pondremos en contacto pronto.</p>
            <a href="/contacto">Volver</a>
        </div>
    </body>
    </html>
    """

@app.route('/cotizar', methods=['POST'])
def cotizar():
    # DEBE DECIR ASÍ:
    nombre = request.form.get('nombre')
    servicio_id = request.form.get('servicio_id') # <--- Verifica que tenga el _id
    es_referido = request.form.get('referido')
    # 2. DICCIONARIOS DE PRECIOS Y NOMBRES REALES
    precios = {
        "marketing_digital": 150000, 
        "desarrollo_web": 300000, 
        "gestion_redes": 200000, 
        "automatizacion_ia": 250000
    }
    
    nombres = {
        "marketing_digital": "Marketing Digital", 
        "desarrollo_web": "Desarrollo Web", 
        "gestion_redes": "Gestión de Redes", 
        "automatizacion_ia": "Automatización con IA"
    }

    # 3. CÁLCULOS
    # Si servicio_id no está en el diccionario, ponemos un nombre por defecto para evitar el KeyError
    nombre_servicio_limpio = nombres.get(servicio_id, "Servicio General")
    subtotal = precios.get(servicio_id, 0)
    descuento = subtotal * 0.10 if es_referido == "S" else 0
    total = subtotal - descuento

    # 4. GUARDAR EN BASE DE DATOS
    try:
        conexion = sqlite3.connect("estudio_global.db")
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO ventas (nombre, servicio, total) VALUES (?, ?, ?)", 
                       (nombre, nombre_servicio_limpio, total))
        conexion.commit()
        conexion.close()
    except Exception as e:
        print(f"Error al guardar en DB: {e}")

    # 5. GENERAR FRASE (IA o LOCAL)
    try:
        prompt = f"Genera una frase de impacto de máximo 20 palabras para el cliente {nombre} que acaba de contratar {nombre_servicio_limpio}. Usa un tono futurista."
        respuesta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        frase_ia = respuesta.choices[0].message.content
    except:
        opciones = [
            f"¡{nombre}, el futuro de tu marca despega hoy con {nombre_servicio_limpio}!",
            f"G-Global Studios: Innovación para {nombre}."
        ]
        frase_ia = random.choice(opciones)

    # 6. RETORNO DE LA TARJETA NEÓN
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
            <h2 style="margin:0;">{nombre.upper()}</h2>
            <div class="frase">"{frase_ia}"</div>
            <p>Servicio: {nombre_servicio_limpio}</p>
            <p>Subtotal: ${subtotal:,.0f}</p>
            <p style="color: #ff4444;">Descuento: -${descuento:,.0f}</p>
            <div class="total">TOTAL A PAGAR: ${total:,.0f}</div>
            <a href="/" class="btn">NUEVA COTIZACIÓN</a>
        </div>
    </body>
    </html>
    """

# RUTAS DE REPORTES Y EXCEL (Mantengo tu código original que estaba bien)
@app.route('/reportes')
def reportes():
    conexion = sqlite3.connect("estudio_global.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, servicio, total FROM ventas")
    datos_ventas = cursor.fetchall()
    conexion.close()
    return render_template('reportes.html', registros=datos_ventas)

@app.route('/eliminar/<int:id>')
def eliminar(id):
    conexion = sqlite3.connect("estudio_global.db")
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM ventas WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()
    return redirect('/reportes')

@app.route('/descargar_excel')
def descargar_excel():
    conexion = sqlite3.connect("estudio_global.db")
    df = pd.read_sql_query("SELECT nombre, servicio, total FROM ventas", conexion)
    conexion.close()
    nombre_archivo = "Reporte_G-Global_Studios.xlsx"
    df.to_excel(nombre_archivo, index=False)
    return send_file(nombre_archivo, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)