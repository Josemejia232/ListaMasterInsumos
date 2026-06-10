# ListaMasterInsumos

Aplicación web para consulta de precios de insumos de construcción en Colombia, con scraping automatizado de múltiples tiendas.

## Funcionalidades

### Usuario Free
- Registro gratuito con email
- Acceso a 10 insumos por categoría de primer nivel (n01)
- Filtro por descripción o categoría
- Vista pública con descripción, unidad, valor y proveedor

### Usuario Pago (Plan Activo)
- Acceso completo a toda la base de datos de insumos
- Plan de $10,000 COP por 30 días
- Pasarela de pago integrada con Bold
- Renovación automática al pagar

### Admin
- Vista completa de productos con datos originales (código, URL, tienda)
- Gestión de usuarios (crear, editar, activar/bloquear, renovar pago)
- Gestión de pagos Bold (crear links, sincronizar estados)
- Sincronización manual de categorías desde Google Sheets
- Webhook de Bold para actualización automática de pagos

## Tiendas Scrapeadas

| Tienda | Scraper |
|--------|---------|
| Easy | `app/scrapers/easy.py` |
| Homecenter | `app/scrapers/homecenter.py` |
| Maestro | `app/scrapers/maestro.py` |
| Promart | `app/scrapers/promart.py` |
| Sodimac | `app/scrapers/sodimac.py` |

## Stack Técnico

- **Backend:** FastAPI + SQLAlchemy + Pydantic
- **Base de datos:** PostgreSQL (producción) / SQLite (desarrollo)
- **Frontend:** HTML + CSS + JavaScript vanilla (SPA)
- **Scraping:** BeautifulSoup4 + lxml + httpx
- **Pagos:** Bold API (integration link)
- **Fuente de datos:** Google Sheets (`gspread`)
- **Hosting:** Render

## Endpoints Principales

### Auth
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register` | Registro de usuario free |
| POST | `/api/auth/login` | Login con email + token |
| GET | `/api/auth/me` | Datos del usuario actual |
| POST | `/api/auth/comprar-plan` | Crear link de pago Bold ($10,000 COP) |

### Productos
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/productos` | Listar productos (con límite free tier) |
| POST | `/api/scrape/general` | Ejecutar scraping general (admin) |
| POST | `/api/scrape/single` | Scraping de una URL individual (admin) |
| GET | `/api/stats` | Estadísticas de la base de datos |

### Usuarios (Admin)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/usuarios` | Listar usuarios |
| POST | `/api/usuarios` | Crear usuario |
| PUT | `/api/usuarios/{id}` | Editar usuario |
| PUT | `/api/usuarios/{id}/renovar` | Renovar pago (30 días desde ahora) |
| POST | `/api/usuarios/{id}/reset-token` | Resetear token de acceso |

### Pagos Bold (Admin)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/pagos` | Listar pagos |
| POST | `/api/pagos/crear-link` | Crear link de pago para un usuario |
| GET | `/api/pagos/{id}` | Ver detalle de pago |
| PUT | `/api/pagos/sync/{id}` | Sincronizar estado desde Bold |
| POST | `/api/webhooks/bold` | Webhook de Bold (actualización automática) |

## Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | URL de conexión a la base de datos |
| `SHEET_URL` | URL del Google Sheet con las URLs a scrapear |
| `ADMIN_EMAIL` | Email del administrador |
| `ADMIN_TOKEN` | Token del administrador |
| `DB_POOL_SIZE` | Tamaño del pool de conexiones |
| `DB_MAX_OVERFLOW` | Conexiones extra máximas |
| `DB_POOL_RECYCLE` | Tiempo de reciclaje de conexiones |
| `BOLD_API_KEY` | API key de Bold |
| `BOLD_SECRET_KEY` | Secret key de Bold |
| `BOLD_BASE_URL` | URL base de la API de Bold |

## Planes y Límites

| Plan | Precio | Duración | Acceso |
|------|--------|----------|--------|
| Free | Gratis | Ilimitado | 10 insumos por categoría (n01) |
| Pago | $10,000 COP | 30 días | Acceso completo a toda la base |

## Estructura de Categorías

Los productos se organizan en 3 niveles jerárquicos:
- `n01` — Categoría principal (ej: Materiales, Herramientas, Acabados)
- `n02` — Subcategoría
- `n03` — Sub-subcategoría

## Google Sheets — Sincronización

El script `scripts/syncPrices.gs` se ejecuta en el Google Sheet vinculado y sincroniza precios con la API. Usa autenticación Bearer token (admin).

### Columnas del Sheet

| Col | Header | Descripción |
|-----|--------|-------------|
| A | URL | URL del producto a scrapear |
| B | NOMBRE PRODUCTO | Nombre del producto (escrito por el script) |
| C-E | _(libre)_ | Categoría, n01, n02, n03, proveedor, etc. |
| F | ÚLTIMO PRECIO | Precio actual (escrito por el script) |
| G | ÚLTIMA ACTUALIZACIÓN | Fecha de última actualización (solo si cambió precio) |
| H | _(libre)_ | |
| I | _(config)_ | **I1** = URL de la API, **I2** = Token de admin |
| J | PRECIO ANTERIOR | Backup del precio antes de sobrescribir |

### Protección ante caída del scraper

- Solo escribe precio si `valor > 0`
- Solo actualiza fecha (col G) si el precio realmente cambió
- Respalda el precio anterior en col J antes de sobrescribir
- Si `/productos` falla o devuelve vacío → no toca la hoja
- `forceFullScrape` pide confirmación antes de ejecutar
