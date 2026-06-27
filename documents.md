# ListaMasterInsumos — Documentación del Proyecto

## Stack Técnico
- **Backend:** FastAPI + SQLAlchemy + Pydantic
- **Base de datos:** PostgreSQL (producción) / SQLite (desarrollo)
- **Frontend:** HTML + CSS + JavaScript vanilla (SPA)
- **Scraping:** BeautifulSoup4 + lxml + httpx
- **Pagos:** Bold API
- **Sesiones:** Cookies HTTP-only firmadas (HMAC-SHA256)
- **Hosting:** Render

## Estructura del Proyecto

```
ListaMasterInsumos/
├── app/
│   ├── main.py                    → Punto de entrada FastAPI, startup, seed admin
│   ├── database.py                → Configuración de BD (SQLite/PostgreSQL)
│   ├── models.py                  → Modelos SQLAlchemy principales
│   ├── models_nomina.py           → 10 modelos de nómina
│   ├── schemas.py                 → Schemas Pydantic principales
│   ├── dependencies.py            → Rate limiting, dependencias
│   ├── daily.py                   → Tarea diaria de scraping
│   ├── nomina/
│   │   ├── schemas.py             → Schemas Pydantic de nómina
│   │   └── router.py             → CRUD endpoints nómina (606 líneas)
│   ├── calculos/
│   │   ├── schemas.py, data.py, data_mamposteria.py, data_anclajes.py
│   │   └── router.py             → Endpoints de calculadora
│   ├── routers/
│   │   ├── auth.py                → Login, registro, planes, pagos
│   │   ├── productos.py / materiales.py / scraping.py / payments.py / users.py
│   ├── services/
│   │   ├── session_service.py     → Cookie firmada
│   │   ├── auth_service.py        → Auth logic
│   │   └── email_service.py       → SMTP
│   └── static/
│       ├── index.html             → SPA principal (676 líneas)
│       ├── css/app.css            → Estilos (521 líneas)
│       └── js/app.js              → Lógica frontend (2760+ líneas)
├── alembic/                       → Migraciones de BD
├── scripts/syncPrices.gs          → Google Apps Script
└── requirements.md                → Requerimientos detallados
```

## Módulos del Frontend

### Login
- 3 tabs: Token, Código email, Usuario gratis
- Password toggle (ícono ojo SVG)
- Sesión con cookie HTTP-only

### InsCal (Materiales de calculadora)
- CRUD completo de materiales con edición inline
- Auto-clasificación de categoría por keywords
- Overrides por usuario

### Cálculos (colapsable)
- **Mezclas:** 6 concretos + 6 morteros
- **Mampostería:** 37 ítems
- **Anclajes:** Sika AnchorFix
- **Boquilla:** 5 formatos × 4 anchos
- **Drywall** (colapsable anidado): Muro Doble Cara, Cielo Raso, Muro Una Cara

### Nómina
Módulo completo de gestión de nómina de obra entre InsCal y Cálculos.

| Sub-módulo | Descripción |
|------------|-------------|
| Proyectos | CRUD con Uso (modal), edición inline |
| Personas | CRUD con EPS/AFP/Cargo (modales), edición inline |
| Vinculaciones | Persona ↔ Proyecto, Cargo con modal CRUD |
| Quincenas | Pago quincenal con cálculo de neto |
| Préstamos | Con sub-tabla expandible de Abonos |

## Edición Inline (Nómina)
- ✏️ Convierte celdas en inputs/selects editables
- 💾 Guarda vía POST (nuevo) o PUT (edición)
- ✕ Restaura valores originales
- Dropdowns muestran opción correcta seleccionada (fix: regex replace selected)
- Fechas vacías se envían como fecha actual (fix: `new Date().toISOString().slice(0,10)`)

## Historial de Cambios (versiones)

### v2.1.0
- Alineación de columnas entre préstamos y abonos (padding, text-align)
- Tabla responsive sin `table-layout:fixed`
- Cargo modal con CRUD desde Vinculaciones (botón ⚙️ sobre tabla y + en inline edit)
- Fix: fecha vacía → fecha actual en todos los saves de nómina (evita 422)
- Fix: dropdown selects muestran valor correcto al editar inline
- Bump cache static assets v3

### v2.0.1
- Password visibility toggle en login
- Fix dropdown selected en inline edit

### v2.0.0
- Módulo nómina completo con edición inline
- Abonos como sub-tabla expandible en Préstamos
- Cálculos colapsable con Drywall anidado
- PUT endpoints para quincenas, préstamos, abonos

## Endpoints Nómina
`/api/nomina/*` — 30+ endpoints CRUD para 10 tablas.

## Seguridad
- Cookies HTTP-only firmadas (HMAC-SHA256)
- Tokens hasheados (SHA-256)
- CORS restrictivo
- Rate limiting (login 5/15min)
- IP block tras 5 fallos
- CSP, HSTS, X-Frame-Options
