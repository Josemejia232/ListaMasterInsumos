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
│   │   ├── schemas.py (sin drywall schemas)
│   │   ├── data.py, data_mamposteria.py, data_anclajes.py
│   │   ├── data_boquilla.py
│   │   ├── data_yeso.py (no usado - módulo Drywall eliminado)
│   │   ├── data_yeso_una_cara.py (no usado - módulo Drywall eliminado)
│   │   ├── data_cielo_raso.py (no usado - módulo Drywall eliminado)
│   │   └── router.py             → Endpoints de calculadora
│   ├── routers/
│   │   ├── auth.py                → Login, registro, planes, pagos
│   │   ├── productos.py / materiales.py / scraping.py / payments.py / users.py
│   ├── services/
│   │   ├── session_service.py     → Cookie firmada
│   │   ├── auth_service.py        → Auth logic
│   │   └── email_service.py       → SMTP
│   └── static/
│       ├── index.html             → SPA principal (600+ líneas)
│       ├── css/app.css            → Estilos (521 líneas)
│       └── js/app.js              → Lógica frontend (2300+ líneas)
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
- **Drywall:** Muro Doble Cara, Muro Una Cara, Cielo Raso (subtítulo dentro de Cálculos)

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

### v2.3.0 — Plan Pro ($20.000/mes)
- Nuevo plan "Pro": Plus + Nómina completa
- Backend: amounts incluye pro ($20.000), upgrade soporta basico→pro y plus→pro
- Backend: webhook y sync_pago manejan ref pro_ y upgrade_pro_
- Backend: nómina protegida con dependency _requiere_nomina (solo plan pro o admin)
- Frontend: tarjeta Pro en landing page y plan banner
- Frontend: sidebar nómina solo visible para plan pro o admin
- Landing: 5 calculadoras (Mezclas, Mampostería, Anclajes, Drywall, Boquilla para Pisos)
- Landing: 4 planes, descripción actualizada con todas las funciones
- Fix: admin token ya no se sobreescribe en cada reinicio del servidor
- Tests: 72/72 pasan

### v2.2.0 — Integración Drywall a Cálculos
- Integración del módulo Drywall dentro de Cálculos (subtítulo "Drywall" con 3 subsecciones)
- Backend: 3 endpoints POST (/yeso, /yeso-una-cara, /cielo-raso)
- Frontend: 3 formularios directos con botón ⚙️ Parámetros
- 3 modales de parámetros (precios y rendimientos editables, guardados en localStorage)
- Sidebar: 1 entrada "Drywall"
- Fix: Drywall encapsulado en `section-drywall` (no aparece en otros módulos)
- Tests: 5 cálculos verificados, 14 endpoints OK

### Final calculos-nomina
- Eliminación completa del módulo Drywall (HTML, JS, Backend)
- Fix: abonos no guardaban actualización (case mismatch `dataset.prestamoId` vs `prestamoid`)
- Fix: abonos creaban copias al guardar (selectores `data-prestamo-id` vs `data-prestamoid`)
- Selectores unificados para `.nom-abono-row` y `.nom-abono-info`
- Commits: c4e66e5, 8fbf548, 69c17c1, 853b893

### CHECK POINT Drywall-Caluclos (commit c4e66e5)
- Eliminación completa del módulo Drywall
- Secciones eliminadas del HTML: Muro Yeso DC, Cielo Raso, Muro Una Cara
- Modales eliminados: modal-yeso, modal-yesouc, modal-cr
- Funciones JS eliminadas: calcularYeso, calcularCieloRaso, calcularYesoUnaCara y modales
- Sidebar: eliminadas entradas Drywall (Muro Yeso DC, Muro Yeso 1C, Cielo Raso)
- Backend: eliminadas rutas /yeso, /yeso/una-cara, /cielo-raso
- Archivos modificados: router.py, index.html, app.js (-700 líneas)

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
