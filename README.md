# KTI POS

Sistema de punto de venta para **Inversiones KTI D & E E.I.R.L.** — gestiona ventas, inventario, compras, clientes y facturacion electronica SUNAT.

## Stack

| Capa | Tecnologia |
|------|------------|
| Frontend | React 19, TypeScript, Ant Design 6, React Router 7, React Query, Recharts |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Base de datos | PostgreSQL 16 |
| AI Chat | Google Gemini 2.0 Flash (function calling) |
| Infra | Docker Compose, Nginx |

## Inicio rapido

### Requisitos
- Docker y Docker Compose

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

Variables requeridas:

```env
# Base de datos
DATABASE_URL=postgresql://ktipos:ktipos2024@localhost:5432/ktipos
POSTGRES_USER=ktipos
POSTGRES_PASSWORD=ktipos2024
POSTGRES_DB=ktipos

# JWT
SECRET_KEY=cambiar-por-clave-secreta-segura
ACCESS_TOKEN_EXPIRE_MINUTES=480

# SUNAT
SUNAT_ENV=beta
SUNAT_SOL_USER=MODDATOS
SUNAT_SOL_PASSWORD=moddatos
SUNAT_CERT_PATH=/app/certs/CertificadoPFX.pfx
SUNAT_CERT_PASSWORD=

# Empresa
EMPRESA_RUC=20525996957
EMPRESA_RAZON_SOCIAL=INVERSIONES KTI D & E E.I.R.L.
EMPRESA_DIRECCION=

# Gemini AI (chatbot)
GEMINI_API_KEY=

# Consulta RUC/DNI
PERU_CONSULT_API_TOKEN=

# Email (opcional)
SMTP_EMAIL=
SMTP_PASSWORD=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

### 2. Levantar servicios

```bash
docker compose up -d --build
```

Esto levanta:
- **PostgreSQL** en puerto `5432`
- **Backend (FastAPI)** en puerto `8000`
- **Frontend (Nginx)** en puerto `80`

### 3. Ejecutar migraciones

```bash
docker compose exec backend alembic upgrade head
```

### 4. Crear usuario admin inicial

```bash
docker compose exec backend python -c "
from app.database import SessionLocal
from app.models.user import User
from app.utils.security import hash_password
db = SessionLocal()
admin = User(username='admin', password_hash=hash_password('admin123'), full_name='Administrador', role='ADMIN')
db.add(admin)
db.commit()
print('Admin creado: admin / admin123')
"
```

### 5. Abrir la aplicacion

Ir a `http://localhost` e iniciar sesion.

## Estructura del proyecto

```
kti-pos/
├── backend/
│   ├── app/
│   │   ├── api/           # Routers FastAPI
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── clients.py
│   │   │   ├── products.py
│   │   │   ├── sales.py
│   │   │   ├── inventory.py
│   │   │   ├── purchases.py
│   │   │   ├── catalogs.py
│   │   │   ├── reports.py
│   │   │   ├── sunat.py
│   │   │   ├── chat.py
│   │   │   ├── peru_consult.py
│   │   │   └── deps.py     # Auth dependencies
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Logica de negocio (SUNAT, Gemini)
│   │   ├── utils/          # Seguridad, IGV
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── alembic/            # Migraciones DB
│   ├── seeds/              # Scripts de importacion
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/            # Clientes Axios
│   │   ├── components/     # Layout, ChatWidget
│   │   ├── contexts/       # Auth, Theme
│   │   ├── pages/          # Paginas por modulo
│   │   ├── types/          # TypeScript interfaces
│   │   ├── utils/          # Formateo
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── .env
```

## Modulos

### Ventas
- Crear preventa → aprobar → facturar (boleta/factura)
- Descuento por linea, metodo de pago (efectivo/tarjeta/mixto)
- Impresion de comprobante
- Anulacion con devolucion de stock

### Productos
- Codigo, nombre, marca, categoria, presentacion
- Precio venta, precio mayoreo, costo unitario
- Stock minimo con alertas

### Clientes
- RUC/DNI con consulta automatica a SUNAT/RENIEC
- Limite de credito y dias de credito
- Referencia comercial y zona

### Inventario
- Stock por almacen
- Ajustes manuales y transferencias entre almacenes
- Historial de movimientos
- Alertas de stock bajo

### Compras
- Ordenes de compra a proveedores
- Recepcion automatica (suma stock)

### SUNAT
- Factura electronica (envio directo, sin OSE)
- Boleta via resumen diario
- Comunicacion de baja
- Consulta de tickets

### Reportes (solo ADMIN)
- Dashboard: ventas del dia/semana/mes
- Ventas por periodo
- Productos mas vendidos
- Rentabilidad por producto

### Chatbot AI
- Asistente flotante con Gemini 2.0 Flash
- Consulta productos, clientes, ventas, stock en tiempo real
- Busqueda por nombre, codigo, marca, categoria
- Respuestas en espanol
- Historial por usuario
- Rol VENTAS no puede ver costos ni ganancias

## Roles

| Rol | Acceso |
|-----|--------|
| **ADMIN** | Todo: ventas, productos, inventario, compras, SUNAT, reportes, usuarios, config |
| **VENTAS** | Ventas, productos (sin costo), clientes, chatbot (sin datos de costo/ganancia) |

## API

Base URL: `http://localhost:8000/api/v1`

| Prefijo | Modulo |
|---------|--------|
| `/auth` | Login, sesion |
| `/users` | Usuarios (ADMIN) |
| `/clients` | Clientes |
| `/products` | Productos |
| `/sales` | Ventas |
| `/inventory` | Stock, movimientos |
| `/purchase-orders` | Compras |
| `/catalogs` | Marcas, categorias, almacenes, series, proveedores |
| `/reports` | Dashboard, reportes |
| `/sunat` | Facturacion electronica |
| `/chat` | Chatbot AI |
| `/lookup` | Consulta RUC/DNI |

Auth: Bearer token JWT en header `Authorization`.

## Desarrollo local (sin Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

El frontend corre en `http://localhost:5173` y hace proxy de `/api` a `localhost:8000`.
