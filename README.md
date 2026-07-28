# 🎬 Cinépolis — Proyecto Vision

Backend y Frontend para el sistema integral de gestión de Cinépolis: cartelera, dulcería, ventas, Club Cinépolis y operación de caja.

---

## 📁 Estructura del Proyecto

```
Cinepolis Part II/
├── backend/                  # API REST en Python/FastAPI
│   ├── controllers/          # Rutas HTTP (Vista/Controlador)
│   ├── services/             # Lógica de negocio y consultas SQL (Modelo)
│   ├── schemas/              # Modelos de validación Pydantic
│   ├── core/                 # Configuración central (DB, settings)
│   ├── workers/              # Scripts de scraping y carga de datos
│   ├── main.py               # Punto de entrada de la API
│   ├── requirements.txt      # Dependencias Python
│   ├── .env.example          # Plantilla de variables de entorno
│   └── .gitignore
│
└── cinepolis-frontend/       # SPA en React + TypeScript + Vite
```

---

## 🖥️ Backend (FastAPI + PostgreSQL)

### Tech Stack

| Tecnología | Versión | Uso |
|---|---|---|
| Python | 3.14 | Lenguaje principal |
| FastAPI | 0.139 | Framework API REST |
| SQLAlchemy | 2.0 | ORM / consultas a BD |
| PostgreSQL | — | Base de datos |
| Pydantic | 2.13 | Validación de datos |
| Uvicorn | 0.50 | Servidor ASGI |
| python-dotenv | 1.2 | Variables de entorno |
| Playwright | 1.58 | Scraping de cartelera |

### Requisitos previos

- Python 3.11+
- PostgreSQL 14+ corriendo localmente
- Base de datos `secret_wars` creada con el DDL del proyecto

### Instalación

```bash
# 1. Entra a la carpeta del backend
cd "Cinepolis Part II/backend"

# 2. (Opcional pero recomendado) Crea un entorno virtual
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Configura las variables de entorno
cp .env.example .env
# Edita .env con tus credenciales de PostgreSQL
```

### Variables de entorno (`.env`)

```env
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/secret_wars
ENVIRONMENT=development
SECRET_KEY=tu_clave_secreta_aqui
```

### Levantar el servidor

```bash
uvicorn main:app --reload
```

El servidor correrá en `http://localhost:8000`

### Documentación interactiva

FastAPI genera automáticamente la documentación de todos los endpoints:

| URL | Descripción |
|---|---|
| `http://localhost:8000/docs` | Swagger UI (recomendado para probar) |
| `http://localhost:8000/redoc` | Documentación ReDoc |

---

## 🗺️ Endpoints principales

| Módulo | Prefijo | Descripción |
|---|---|---|
| Sistema | `GET /` `GET /api/health` | Estado del servidor y BD |
| Cartelera | `GET /api/cartelera/{slug}` | Películas y funciones por complejo |
| Películas | `GET /api/pelicula/{id}` | Detalle, director y elenco |
| Asientos | `GET /api/funcion/{id}/asientos` | Mapa de sala en tiempo real |
| Precios | `GET /api/funcion/{id}/precios` | Tarifario por función |
| Dulcería | `GET /api/dulceria/{slug}` | Catálogo con personalizaciones |
| Carrito | `POST /api/carrito` | Crear, agregar, pagar y abandonar |
| Autenticación | `POST /api/auth/otp/solicitar` | Login/Registro por OTP |
| Club | `GET /api/club/{socio_id}` | Perfil, puntos y movimientos |
| Personal | `POST /api/personal/login` | Login de empleados |
| Sesión de Caja | `POST /api/sesiones/abrir` | Apertura y corte de caja |
| Garantías | `POST /api/garantia/reclamo` | Reembolsos y reclamos |
| Marketing | `GET /api/banners/{slug}` | Banners y promociones activas |

---

## 🌐 Frontend (React + TypeScript + Vite)

### Tech Stack

| Tecnología | Uso |
|---|---|
| React 19 | UI Library |
| TypeScript 6 | Tipado estático |
| Vite 8 | Build tool |
| TailwindCSS 4 | Estilos |
| React Router 7 | Navegación |
| TanStack Query | Fetching y caché de datos |
| Zustand | Estado global |
| Axios | Cliente HTTP |

### Instalación y ejecución

```bash
# 1. Entra a la carpeta del frontend
cd "Cinepolis Part II/cinepolis-frontend/cinepolis-frontend"

# 2. Instala las dependencias
pnpm install

# 3. Levanta el servidor de desarrollo
pnpm dev
```

El frontend correrá en `http://localhost:5173`

> Asegúrate de que el backend esté corriendo en `localhost:8000` antes de iniciar el frontend.

---

## 🔧 Workers (Scraping y carga de datos)

Los scripts en `backend/workers/` se usan para poblar la base de datos:

| Script | Descripción |
|---|---|
| `matilde_v6_worker_playwright.py` | Scraper principal de cartelera (Playwright) |
| `enriquecer_elenco.py` | Enriquece datos de elenco desde fuentes externas |
| `dump_graphql.py` | Dump de datos vía GraphQL |
| `inspect_graphql.py` | Inspección del esquema GraphQL |

### Ejecutar un worker

```bash
cd "Cinepolis Part II/backend"
python workers/matilde_v6_worker_playwright.py
```

> **Nota:** Algunos workers requieren que los navegadores de Playwright estén instalados:
> ```bash
> playwright install chromium
> ```

---

## 🗄️ Base de Datos

- Motor: **PostgreSQL**
- Nombre de la BD: `secret_wars`
- El DDL completo está en los archivos `.sql` del proyecto (`SW_SCRIPT/`)
- Se usa **SQLAlchemy con SQL crudo** (`text()`) en lugar de ORM declarativo, para mayor control sobre las consultas

---

## 🏗️ Arquitectura MVC

```
HTTP Request
     │
     ▼
controllers/       ← Recibe la petición, valida parámetros
     │
     ▼
services/          ← Lógica de negocio, consultas SQL
     │
     ▼
PostgreSQL         ← Base de datos
     │
     ▼
HTTP Response
```

Los **schemas** (`schemas/models.py`) validan los cuerpos de las peticiones con Pydantic antes de que lleguen a los servicios.

---

## 👥 Equipo

Proyecto académico — Cinépolis Vision System
