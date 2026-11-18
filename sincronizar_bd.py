import urllib.request
import os
import sqlite3

# URL de tu app en Render
RENDER_URL = "https://global-5jl5.onrender.com"
DB_DESTINO = "estudio_global.db"

def sincronizar():
    print("=" * 65)
    print(" SINCRONIZADOR DE BASE DE DATOS G-GLOBAL (RENDER -> SQLITE LOCAL)")
    print("=" * 65)
    print("\nNota: Para descargar la base de datos de producción con tus usuarios:")
    print(f"1. Abre en tu navegador: {RENDER_URL}/admin")
    print("2. Haz clic en el botón verde: '💾 Descargar Base de Datos SQLite (.db)'")
    print(f"3. Guarda el archivo descargado reemplazando el archivo local en:")
    print(f"   {os.path.abspath(DB_DESTINO)}")
    print("\n¡Al reemplazarlo, podrás ver todos los usuarios reales en tu PC con:")
    print("   python consultar_bd.py")
    print("=" * 65)

if __name__ == "__main__":
    sincronizar()
