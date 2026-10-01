# G-Global Studios - Sitio Web Corporativo

Sitio web completo para G-Global Studios desarrollado con **Flask (Python)**, **SQLite** y **HTML/CSS/JS** vanilla. Incluye autenticación de usuarios, cotizador inteligente con IA, panel de reportes y gestión de contactos.

## 🚀 Características Principales

### 🔐 Sistema de Autenticación (Flask-Login)
- **Registro de usuarios** con validación de email único y contraseña segura (hash bcrypt)
- **Login/Logout** con opción "Recordarme"
- **Protección de rutas** con `@login_required`
- **Datos aislados por usuario** - cada usuario ve solo sus cotizaciones y mensajes

### 💰 Cotizador Inteligente
- 6 servicios predefinidos con precios
- Cálculo automático de precios al seleccionar servicio
- Descuento del 10% para referidos
- Generación de frase de impacto con **OpenAI GPT-3.5** (opcional)
- Guardado en base de datos asociado al usuario autenticado

### 📊 Panel de Reportes
- Listado de cotizaciones del usuario autenticado
- Eliminación individual de registros
- **Descarga a Excel** (pandas/openpyxl)

### 📬 Formulario de Contacto
- Envío de mensajes guardados en BD
- Asociado al usuario si está logueado
- Vista `/mensajes` para consultar historial

### 🎨 Páginas Públicas
- **Inicio** - Hero + Cotizador + Proyectos destacados
- **Servicios** - 6 tarjetas de servicios con precios
- **Nosotros** - Misión, Visión, Valores
- **Testimonios** - 6 testimonios con avatares
- **Contacto** - Info de contacto + Formulario

## 🛠 Stack Tecnológico

| Tecnología | Versión | Uso |
|------------|---------|-----|
| Python | 3.11+ | Backend |
| Flask | 3.1.3 | Web Framework |
| Flask-Login | 0.6.3 | Autenticación |
| SQLite | - | Base de datos |
| Pandas | 3.0.1 | Exportar Excel |
| OpenAI | 2.16.0 | Frases IA (opcional) |
| Gunicorn | 23.0.0 | WSGI Server (Producción) |
| Werkzeug | 3.1.3 | Security (hash passwords) |

## 📁 Estructura del Proyecto

```
G_Global_Web/
├── app.py                 # Aplicación principal Flask
├── requirements.txt       # Dependencias Python
├── runtime.txt           # Python version para Render
├── render.yaml           # Configuración auto-deploy Render
├── .gitignore            # Archivos ignorados por Git
├── estudio_global.db     # Base de datos SQLite (generada auto)
├── README.md             # Este archivo
└── templates/            # Plantillas HTML
    ├── index.html        # Inicio + Cotizador
    ├── login.html        # Login
    ├── register.html     # Registro
    ├── servicios.html    # Servicios
    ├── nosotros.html     # Nosotros
    ├── testimonios.html  # Testimonios
    ├── contacto.html     # Contacto
    ├── reportes.html     # Panel reportes
    └── mensajes.html     # Historial mensajes
```

## ⚙️ Instalación Local

```bash
# 1. Clonar repositorio
git clone https://github.com/johnpuellob-hue/global.git
cd global

# 2. Crear entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno (opcional)
# Crear archivo .env:
SECRET_KEY=tu-clave-secreta-super-segura
OPENAI_API_KEY=sk-tu-api-key-openai  # Para frases IA

# 5. Ejecutar
python app.py
# Abrir http://127.0.0.1:5000
```

## 🌐 Despliegue en Render (Gratis)

1. **Cuenta en Render** → Conectar GitHub
2. **New Web Service** → Seleccionar repo `global`
3. Render detecta `render.yaml` automáticamente:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
   - Python: 3.11.0
4. **Environment Variables** (Settings → Environment):
   - `SECRET_KEY` = clave aleatoria larga
   - `OPENAI_API_KEY` = (opcional) para frases IA
5. **Create Web Service** → Esperar deploy (~3 min)

URL resultante: `https://g-global-studios.onrender.com`

## 🗄️ Base de Datos (SQLite)

### Tablas

**usuarios**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | ID único |
| nombre | TEXT | Nombre completo |
| email | TEXT UNIQUE | Email (login) |
| password_hash | TEXT | Hash bcrypt |
| telefono | TEXT | Teléfono opcional |
| fecha_registro | TIMESTAMP | Auto |

**ventas** (cotizaciones)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | ID único |
| user_id | INTEGER FK | Usuario propietario |
| nombre | TEXT | Nombre cliente |
| servicio | TEXT | Servicio cotizado |
| total | REAL | Precio final |
| fecha | TIMESTAMP | Auto |

**mensajes** (contacto)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | INTEGER PK | ID único |
| user_id | INTEGER FK | Usuario (NULL si anónimo) |
| nombre | TEXT | Nombre |
| email | TEXT | Email |
| telefono | TEXT | Teléfono |
| servicio | TEXT | Servicio interés |
| mensaje | TEXT | Contenido |
| fecha | TIMESTAMP | Auto |

## 🔧 Variables de Entorno

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `SECRET_KEY` | Sí | Clave secreta Flask (generar con `secrets.token_hex(32)`) |
| `OPENAI_API_KEY` | No | API Key OpenAI para frases IA en cotizaciones |
| `PORT` | No | Puerto (Render lo asigna automáticamente) |

## 📦 Servicios y Precios

| Clave | Servicio | Precio Base |
|-------|----------|-------------|
| `desarrollo_web` | Desarrollo Web | $300.000 |
| `marketing_digital` | Marketing Digital | $150.000 |
| `automatizacion_ia` | Automatización con IA | $250.000 |
| `gestion_redes` | Gestión de Redes | $200.000 |
| `diseno_grafico` | Diseño Gráfico | $100.000 |
| `produccion_audiovisual` | Producción Audiovisual | $180.000 |

*Descuento 10% para referidos (checkbox en formulario)*

## 🔒 Seguridad

- **Password hashing**: bcrypt via Werkzeug
- **SQL Injection**: Queries parametrizadas (`?` placeholders)
- **XSS Protection**: `html.escape()` en salidas dinámicas
- **CSRF**: Recomendado agregar Flask-WTF para formularios críticos
- **HTTPS**: Render provee SSL automático

## 🧪 Testing Local

```bash
# Ejecutar con debug
python app.py

# Verificar BD
sqlite3 estudio_global.db ".tables"
sqlite3 estudio_global.db "SELECT * FROM usuarios;"
```

## 📝 API Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| GET | `/` | Público | Home + Cotizador |
| GET/POST | `/login` | Público | Login |
| GET/POST | `/register` | Público | Registro |
| GET | `/logout` | Requerido | Cerrar sesión |
| GET | `/servicios` | Público | Lista servicios |
| GET | `/nosotros` | Público | Info empresa |
| GET | `/testimonios` | Público | Testimonios |
| GET | `/contacto` | Público | Formulario contacto |
| POST | `/enviar-mensaje` | Público | Guardar mensaje |
| POST | `/cotizar` | **Requerido** | Generar cotización |
| GET | `/reportes` | **Requerido** | Ver mis cotizaciones |
| GET | `/mensajes` | **Requerido** | Ver mis mensajes |
| GET | `/eliminar/<id>` | **Requerido** | Borrar cotización propia |
| GET | `/descargar_excel` | **Requerido** | Exportar mis cotizaciones |

## 🤝 Contribuir

1. Fork del repo
2. Crear rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m "Add: nueva funcionalidad"`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

## 📄 Licencia

Proyecto privado - G-Global Studios © 2024

---

**Desarrollado con ❤️ por G-Global Studios**