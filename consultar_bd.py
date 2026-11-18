import sqlite3
import os

DB_NAME = "estudio_global.db"

def consultar_db():
    if not os.path.exists(DB_NAME):
        print(f"Error: No se encontró el archivo {DB_NAME}")
        return

    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    print("=" * 60)
    print(" BASE DE DATOS: G-GLOBAL STUDIOS (estudio_global.db)")
    print("=" * 60)

    # 1. USUARIOS
    print("\n--- 1. TABLA: USUARIOS ---")
    usuarios = cur.execute("SELECT id, nombre, email, telefono, is_admin, fecha_registro FROM usuarios").fetchall()
    if not usuarios:
        print(" (No hay usuarios registrados aún)")
    else:
        for u in usuarios:
            admin_badge = "[ADMIN]" if u['is_admin'] == 1 else "[CLIENTE]"
            print(f" ID: {u['id']} | {admin_badge} {u['nombre']} | Email: {u['email']} | Tel: {u['telefono']} | Fecha: {u['fecha_registro']}")

    # 2. COTIZACIONES (VENTAS)
    print("\n--- 2. TABLA: COTIZACIONES (VENTAS) ---")
    ventas = cur.execute("SELECT id, nombre, servicio, sub_servicio, total, fecha FROM ventas ORDER BY id DESC LIMIT 10").fetchall()
    if not ventas:
        print(" (No hay cotizaciones registradas)")
    else:
        for v in ventas:
            sub = f" ({v['sub_servicio']})" if v['sub_servicio'] else ""
            print(f" ID: {v['id']} | Cliente: {v['nombre']} | Servicio: {v['servicio']}{sub} | Total: ${v['total']:,.0f} | Fecha: {v['fecha']}")

    # 3. MENSAJES DE CONTACTO
    print("\n--- 3. TABLA: MENSAJES DE CONTACTO ---")
    mensajes = cur.execute("SELECT id, nombre, email, telefono, servicio, mensaje, fecha FROM mensajes ORDER BY id DESC LIMIT 10").fetchall()
    if not mensajes:
        print(" (No hay mensajes registrados)")
    else:
        for m in mensajes:
            print(f" ID: {m['id']} | De: {m['nombre']} ({m['email']}) | Asunto: {m['servicio']} | Mensaje: {m['mensaje'][:40]}... | Fecha: {m['fecha']}")

    print("\n" + "=" * 60)
    con.close()

if __name__ == "__main__":
    consultar_db()
