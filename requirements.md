# ListaMasterInsumos

Aplicación web para consulta de precios de insumos de construcción en Colombia, con scraping automatizado de múltiples tiendas.

## Funcionalidades

### Usuario Free
- Registro gratuito con email
- Acceso a 10 insumos por categoría de primer nivel (n01)
- **3 cálculos por tipo** (mezclas, mampostería, anclajes) — luego se bloquea
- Filtro por descripción o categoría
- Vista pública con descripción, unidad, valor y proveedor

### Usuario Básico (Plan Activo)
- Acceso **ilimitado a productos** (toda la base de datos)
- **Sin calculadora** (no incluye mezclas, mampostería ni anclajes)
- Plan de **$10,000 COP por 30 días**
- Pasarela de pago integrada con Bold

### Usuario Plus (Plan Activo)
- Acceso **ilimitado a todo** (productos + calculadora completa)
- Plan de **$15,000 COP por 30 días**
- Pasarela de pago integrada con Bold
- Renovación automática al pagar

### Upgrade Básico → Plus (prorrateo)
- Se calcula el crédito por los días **no usados** del Básico: `$10,000 × días_restantes / 30`
- El usuario paga: `$15,000 - crédito`
- Al pagar, el ciclo **reinicia por 30 días limpios** de Plus

### Módulo Cálculos

| Sección | Tipos | Unidades | Precios |
|---------|-------|----------|---------|
| **Mezclas** | 6 concretos (3.500–1.800 psi) + 6 morteros (1:10–1:6) | m³ | Cemento/arena/gravilla desde BD; agua, MO, mezcladora fijos |
| **Mampostería** | 37 ítems (5 legacy + 32 Ladrillera Santafé) | m² | Fallback por ítem; Arena Base/Sello para adoquines; Mortero para estructurales/fachadas/divisorios |
| **Anclajes** | Calculadora Sika AnchorFix | ø varilla (mm), profundidad (mm), cantidad puntos | Tubos 300ml, varilla, tuercas, broca, kit limpieza, MO |

- **Plan Free**: 3 usos por tipo (mezclas, mampostería, anclajes). Bloqueo con mensaje de upgrade.
- **Plan Básico**: Sin acceso a calculadora (403).
- **Plan Plus**: Uso ilimitado.
- Selector desplegable para elegir la mezcla/mampostería/anclaje a calcular
- Campos editables en la interfaz: **Material, Unidad y Vr Unitario** (tabla InsCal)
- CRUD completo de materiales en InsCal: agregar filas (`+ Agregar material`), editar en línea, eliminar (`✕`)
- **Auto-clasificación** de categoría desde el nombre del material (keyword mapping)
- Overrides de materiales por usuario (`UserMaterialOverride`) — cada usuario guarda sus propios ajustes
- Recalculo automático del total al modificar valores
- Input de volumen (m³ mezclas / m² mampostería / puntos anclajes) para escalar
- Conversión automática a unidades enteras prácticas:
  - Cemento → Bolsas de 50 kg
  - Arena / Gravilla → Viajes de 1.05 m³
  - Agua → Litros
  - Mano de obra → Horas cuadrilla (hc)
  - Mezcladora → Horas (hr)
- **Nota final** en lista con resumen de cantidades a comprar (excluye MO/mezcladora/agua)
- **Indicadores de carga** con spinner animado en todas las consultas de calculadora
- **Caché frontend** (`_calcCache`) para evitar re-consultas al servidor al cambiar filtros

### Insumos (Vista Unificada)
- **Todos los usuarios** (free, básico, plus, admin) ven la misma vista de insumos
- Estructura de **árbol categorizado** (n01 → n02 → n03) con expand/colapsar
- **Solo lectura** — no se permite editar desde esta vista (el CRUD está en InsCal)
- Eliminada la tabla cruda admin-only; ahora hay una única interfaz consistente
- El admin gestiona los productos vía la sección **InsCal** (añadir/editar/eliminar materiales)

### Admin
- Vista completa de productos con datos originales (código, URL, tienda)
- **InsCal:** Gestión de materiales de calculadora con tabla editable (Material, Unidad, Vr Unit, Cantidad)
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
- **Base de datos:** PostgreSQL (Neon, producción) / SQLite (desarrollo)
- **Frontend:** HTML + CSS + JavaScript vanilla (SPA) con responsive design
- **Scraping:** BeautifulSoup4 + lxml + httpx
- **Pagos:** Bold API (integration link)
- **Fuente de datos:** Google Sheets (`gspread`)
- **Hosting:** Render (servicio unificado — backend API + frontend SPA en el mismo `uvicorn`)
  - Frontend: servido como archivos estáticos desde el backend (`/app`, `/`)
  - Backend: `uvicorn app.main:app` (FastAPI)

## Landing Page

Página de marketing premium (`/landing`) con diseño dark theme y glassmorphism:
- **Hero:** Headline emocional, stats dinámicos en tiempo real (5+ tiendas, 12 mezclas, 37 mamposterías), card de precios en vivo
- **El Dolor:** 3 pain points (precios cambian, cálculos fallan, horas perdidas)
- **La Solución:** 3 pasos (consulta precios → calcula → elige plan)
- **Funciones:** 6 cards (Insumos Actualizados, Consulta Precios, Gestión Usuarios, Panel Admin, Pagos Bold)
- **Calculadoras:** 3 cards (Mezclas, Mampostería, Anclajes)
- **Planes:** 3 cards (Free, Plus, Básico) con botones de compra unificados
- **WhatsApp:** Botón flotante verde (+57 324 622 5685)
- **Animaciones:** Scroll reveal, floating elements, hover effects
- **Stats dinámicos:** Se cargan en tiempo real desde `/api/calculos/stats`

## Responsive Design

- **Desktop:** Layout completo con tablas, formularios en línea y tarjetas de plan en fila
- **Tablet (≤768px):** Formularios apilados, tablas con scroll horizontal, tarjetas de plan en columna
- **Móvil (≤480px):** Inputs 100% ancho, tipografía reducida, anclajes en columna vertical
- **Spinner de carga:** Indicador visual animado mientras se consultan datos del servidor
- **Caché frontend:** `_calcCache` evita re-consultas innecesarias a la lista de mezclas/mampostería
- **Login → Landing:** Link "Página de inicio" en el login para volver al marketing

## Endpoints Principales

### Auth
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/auth/register` | Registro de usuario free |
| POST | `/api/auth/login` | Login con email + token |
| GET | `/api/auth/me` | Datos del usuario actual (incluye `plan`) |
| GET | `/api/auth/planes` | Ver plan actual + opciones de upgrade |
| POST | `/api/auth/comprar-plan` | Crear link de pago Bold (`{plan: "basico" \| "plus"}`) |
| POST | `/api/auth/upgrade-plan` | Upgrade Básico → Plus (prorrateo automático) |

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

### Cálculos
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/calculos` | Listar mezclas/mampostería (filtro `?tipo=concreto\|mortero\|mamposteria`) |
| GET | `/api/calculos/stats` | Estadísticas de cálculos (mezclas, mamposterías, tiendas) — público |
| GET | `/api/calculos/{id}` | Obtener mezcla/mampostería por ID (Free limitado a 3 usos por tipo) |
| POST | `/api/calculos/anclajes` | Calcular anclajes químicos (Sika AnchorFix) — Free limitado a 3 usos |
| DELETE | `/api/calculos/overrides/{nombre}` | Eliminar override de material por nombre |

### Materiales (InsCal)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/materiales/inscal` | Listar todos los materiales de InsCal |
| GET | `/api/materiales/inscal/{id}` | Obtener un material de InsCal por ID |
| PUT | `/api/materiales/inscal/{id}` | Actualizar material de InsCal (Material, Unidad, Vr Unit, Cantidad, Categoría) |
| DELETE | `/api/materiales/inscal/{id}` | Eliminar material de InsCal |
| POST | `/api/materiales/inscal/clasificar` | Auto-clasificar categoría desde nombre de material |

### Pagos Bold (Admin)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/pagos` | Listar pagos |
| POST | `/api/pagos/crear-link` | Crear link de pago para un usuario |
| GET | `/api/pagos/{id}` | Ver detalle de pago |
| PUT | `/api/pagos/sync/{id}` | Sincronizar estado desde Bold |
| POST | `/api/webhooks/bold` | Webhook de Bold (actualización automática) |

### Landing Page
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/landing` | **Redirige 301 a `/`** — la landing page ya no existe como ruta separada |
| GET | `/` | Aplicación principal (SPA) |

## Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `DATABASE_URL` | URL de conexión a la base de datos | Si |
| `SHEET_URL` | URL del Google Sheet con las URLs a scrapear | Si |
| `ADMIN_EMAIL` | Email del administrador | Si |
| `ADMIN_TOKEN` | Token del administrador (min 32 chars) | Si |
| `DB_POOL_SIZE` | Tamaño del pool de conexiones | No |
| `DB_MAX_OVERFLOW` | Conexiones extra máximas | No |
| `DB_POOL_RECYCLE` | Tiempo de reciclaje de conexiones | No |
| `BOLD_API_KEY` | API key de Bold | Si |
| `BOLD_SECRET_KEY` | Secret key de Bold | Si |
| `BOLD_BASE_URL` | URL base de la API de Bold | No |
| `ALLOWED_ORIGINS` | Dominios permitidos para CORS (ej: `https://tudominio.com`) | Si |
| `FORCE_HTTPS` | Forzar redirección HTTPS (`true`/`false`) | No |
| `BOLD_WEBHOOK_IPS` | IPs permitidas para webhook Bold (ej: `1.2.3.4,5.6.7.8`) | No |

**Nota:** Nunca commitear archivos `.env` con credenciales reales. El archivo `config/.env.develop` fue eliminado del control de versiones y ahora está en `.gitignore`.

## Planes y Límites

| Plan | Precio | Duración | Productos | Calculadora |
|------|--------|----------|-----------|-------------|
| Free | Gratis | Ilimitado | 10 insumos por categoría (n01) | 3 cálculos por tipo (mezcla, mampostería, anclajes) |
| Básico | $10,000 COP | 30 días | Ilimitados | ❌ Sin calculadora |
| Plus | $15,000 COP | 30 días | Ilimitados | ✅ Ilimitada |

**Upgrade Básico → Plus:** prorrateo automático por días no usados del Básico. Pago mínimo $5,000 (día 0). Al pagar, reinicia a 30 días limpios de Plus.

## Seguridad

### Mejoras implementadas

| Mejora | Descripción | Archivo |
|--------|-------------|---------|
| **CORS restrictivo** | Sin fallback a `*`; credenciales requieren origen explícito | `main.py` |
| **SSRF prevention** | Validación de dominios permitidos en `/scrape/sync` | `main.py` |
| **Rate limiting DB** | Límites por IP persistidos en base de datos (multi-worker) | `main.py` |
| **Cache DB** | Caché de productos compartida entre workers vía BD | `main.py` |
| **Tokens enmascarados** | Listado de usuarios solo muestra `****XXXX` | `main.py`, `index.html` |
| **Reset token seguro** | Tokens de 64 chars; no se retornan en listados | `main.py` |
| **Admin token min 32** | Validación en startup; rechaza tokens cortos | `main.py` |
| **CSP headers** | Content-Security-Policy restrictivo | `main.py` |
| **HTTPS redirect** | Redirección automática HTTP → HTTPS en producción | `main.py` |
| **Webhook IP whitelist** | Validación de IPs de origen para webhook Bold | `main.py` |
| **No logs de tokens** | Eliminación de logs de autenticación con prefijos de tokens | `main.py` |
| **Auth por índice** | Búsqueda directa `Usuario.token == token` en lugar de full scan | `main.py` |
| **Limpieza Git** | Historial de Git purgado de credenciales con `git filter-branch` | `repo` |
| **Git cleanup script** | Script automatizado para sanitización de historial | `_git_cleanup.py` |
| **Token validation GAS** | Validación de token en Apps Script (triggers + manual) | `syncPrices.gs` |

### Post-configuración obligatoria (Pendiente)
1. ✅ ~~Eliminar credenciales de archivos de desarrollo~~ — Completado
2. ✅ ~~Limpiar historial de Git~~ — Completado con `git filter-branch` (commits reescritos)
3. ⚠️ **Rotar credenciales** en Bold (API key y Secret key) — **URGENTE**
4. ⚠️ **Generar nuevo `ADMIN_TOKEN`** (mínimo 32 caracteres) — **URGENTE**
5. Configurar `ALLOWED_ORIGINS` en Render con el dominio de producción.
6. Configurar `BOLD_WEBHOOK_IPS` con las IPs oficiales de Bold (consultar documentación Bold).
7. Actualizar celda I2 del Google Sheet con el nuevo admin token.
8. Ejecutar `git push origin --force --all` para sincronizar el historial limpio con GitHub.

### Notas sobre la limpieza de Git
- **Commits eliminados del historial:** `64861c1`, `ff9e85d`, `bf08c29`, `129eed8` (contenían credenciales expuestas)
- **Backup creado:** `../ListaMasterInsumos-backup.git` (copia del repo original antes de la limpieza)
- **Verificación:** `git log -S` confirma que ninguna credencial expuesta permanece en el historial
- **Todos los hashes de commits cambiaron** — se requiere `git push --force` para actualizar el remoto

## Performance

### Optimizaciones implementadas

| Optimización | Impacto | Archivo |
|--------------|---------|---------|
| **Listado ligero** (`MezclaMetaResponse`) | Reducción de ~500ms a ~30ms en listar mezclas | `router.py` |
| **Caché frontend** (`_calcCache`) | Evita re-consultas al cambiar filtros de tipo/categoría | `index.html` |
| **Indicadores de carga** | Spinner animado mientras se cargan datos | `index.html` |
| **Lazy loading** | Resultados de cálculo solo se renderizan al hacer clic en "Calcular" | `index.html` |
| **Responsive CSS** | Media queries para 768px y 480px | `index.html` |
| **Auth por token** (`Usuario.token == token`) | Busca directo en BD en lugar de traer todos los usuarios | `router.py` |
| **Queries unificadas** (`or_` en palabras clave) | Reduce de N queries a 2 por material (Insumo + Producto) | `router.py` |
| **Sin carga automática** | Al cambiar filtro de tipo/categoría, no recarga la mezcla automáticamente | `index.html` |
| **Landing page** | Página de marketing separada con stats dinámicos | `landing.html` |
| **Botón WhatsApp** | Botón flotante verde en landing page | `landing.html` |
| **Stats dinámicos** | `/api/calculos/stats` retorna conteos en tiempo real | `router.py` |
| **UX Login** | Link a landing page desde el login | `index.html` |

### DNS / Localhost
- En Windows, `localhost` puede tener delay de ~2s por resolución DNS
- **Solución:** Usar `127.0.0.1` para pruebas locales; en producción (Render) no aplica

## Módulo Cálculos — Datos

Las recetas de concretos y morteros provienen del archivo `20191013 Base De Datos JM.xls` (hoja "Conc-Mort"), con rendimientos basados en Construdata 2014.

### Estructura del módulo

```
app/
├── calculos/
│   ├── __init__.py          → Re-exporta componentes
│   ├── schemas.py           → Pydantic models (MezclaResponse, MaterialCalculado, AnclajeRequest, AnclajeResponse)
│   ├── data.py              → 12 recetas (6 concretos + 6 morteros)
│   ├── data_mamposteria.py  → 37 recetas de mampostería (5 legacy + 32 Ladrillera Santafé)
│   ├── data_anclajes.py     → Lógica volumétrica de anclajes (cilindro πr²h, factor 20%, tubos 300ml)
│   └── router.py            → Endpoints FastAPI + lógica de búsqueda en BD + control de planes
├── routers/
│   └── materiales.py        → CRUD de materiales InsCal + auto-clasificación
├── models.py                → Producto (con columna `material`), UserMaterialOverride
└── schemas.py               → MaterialInscalRequest, MaterialInscalResponse, UpdateAjustadaRequest
```

### Lógica de precios (3 fuentes)

| Fuente | Descripción |
|--------|-------------|
| `db` | Precio obtenido de la tabla `insumos` o `productos` (búsqueda por palabras clave) |
| `fijo` | Agua ($57/LT), M.O. ($19,888/$11,288 hc), Mezcladora ($4,125/hr) |
| `fallback` | Precios del Excel cuando la BD está vacía (cemento $546/kl, arena $38–45K/m³, etc.) |

## Estructura de Categorías

Los productos se organizan en 3 niveles jerárquicos:
- `n01` — Categoría principal (ej: Materiales, Herramientas, Acabados)
- `n02` — Subcategoría
- `n03` — Sub-subcategoría

### Campo `material` en Producto

- Nueva columna `material` (VARCHAR 200, nullable) en la tabla `productos`
- Se usa para la tabla **InsCal** — cada fila de la calculadora corresponde a un `Producto` con `material` asignado
- **Auto-clasificación:** el backend mapea keywords del nombre del material a categorías (`categoria`):
  - `arena`, `gravilla`, `agregado` → `Materiales`
  - `cemento` → `Materiales`
  - `agua` → `Materiales`
  - `mano de obra`, `cuadrilla` → `Mano de Obra`
  - `mezcladora` → `Maquinaria`
  - (más mappings en `app/routers/materiales.py`)
- Si no hay match, la categoría queda `NULL` y aparece en **"Sin categoría"** en el árbol de insumos

### Tabla `UserMaterialOverride`

- Permite que cada usuario guarde sus propios ajustes de cantidad, unidad y valor unitario para cada material de InsCal
- Clave: `(usuario_id, producto_id)` — única por usuario-material
- El frontend consulta `GET /api/calculos/{id}` y aplica los overrides del usuario logueado antes de renderizar

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

### Solución de problemas GAS

- **401 en `/scrape/sync` o `/productos`**: El token en I2 no coincide con el del admin en la BD. Verificar en Render → Environment Variables que `ADMIN_TOKEN` coincida con el token real del admin (loguearse en la app para confirmarlo).
- **Columna J vacía**: El script ejecuta una semilla automática que copia F → J en el primer sync. Revisar Logs de Cloud (Editor Apps Script → Ejecuciones → ver log detallado) para confirmar `Semilla col J: X filas`.
- **"PRECIO ANTERIOR" aparece en I1**: Versión vieja del script pisó la API URL. Borrar I1 y restaurar `https://listamasterinsumos.onrender.com`, o actualizar el script a la versión más reciente de `scripts/syncPrices.gs`.

## Auditoría de Seguridad (cotejado vs SeguridadStack.md)

Evaluación realizada el 19/06/2026 comparando `SeguridadStack.md` contra el código actual.

### 🟢 Implementado correctamente

| Control | Archivo |
|---------|---------|
| CORS restrictivo (sin `*`, dominios desde env) | `app/main.py:64-78` |
| Validación de inputs (Pydantic v2 + domain allowlist) | `app/schemas.py`, `app/dependencies.py:98-115` |
| SQLAlchemy ORM (sin SQL injection) | Toda la app |
| Rate limiting DB-backed (login 10/min, scrape 5/min) | `app/dependencies.py:27-74` |
| CSP headers (`frame-ancestors`, `base-uri`, `form-action`) | `app/main.py:93-103` |
| `X-Frame-Options: DENY` | `app/main.py:109` |
| `X-Content-Type-Options: nosniff` | `app/main.py:108` |
| `Referrer-Policy: strict-origin-when-cross-origin` | `app/main.py:110` |
| `Permissions-Policy` | `app/main.py:111` |
| HTTPS redirect (configurable via `FORCE_HTTPS`) | `app/main.py:82-90` |
| Timing-safe comparison (`hmac.compare_digest`) | `app/services/auth_service.py:18` |
| Token masking en respuestas (`****XXXX`) | `app/schemas.py:150-155` |
| Admin endpoints protegidos (`require_admin`) | `app/routers/*.py` |
| `.env` en `.gitignore` | `.gitignore:11-14` |
| API keys solo en variables de entorno | `app/bold.py:11-13` |

### 🟡 Parcialmente implementado o con riesgo bajo

| Control | Riesgo | Archivo |
|---------|--------|---------|
| `'unsafe-inline'` en CSP para scripts/styles | XSS potencial | `app/main.py:94-95` |
| Errores de Bold exponen `str(e)` al usuario | Fuga de info interna | `app/routers/auth.py:97,137` |
| Sin global exception handler | Error 500 genérico sin control | `app/main.py` |
| Background tasks sin colas dedicadas | Bloqueo en tareas largas | `app/routers/scraping.py` |

### 🔴 No implementado (priorizado)

| Control | Prioridad | Impacto |
|---------|:---------:|---------|
| `Strict-Transport-Security` (HSTS) | Alta | Seguridad de conexión |
| Tokens hasheados en DB (SHA-256) | **Crítica** | Exposición de tokens si DB comprometida |
| `ADMIN_TOKEN` débil | **Crítica** | Adivinación/fuerza bruta |
| Sentry / monitoreo de errores | Alta | Sin alertas de ataque |
| CAPTCHA en registro | Media | Bots automatizados |
| JWT con expiración + refresh tokens | Media | Sesiones sin expiración |
| Rate limiting por usuario (no solo IP) | Media | Abuso por usuario legítimo |
| Auditoría de acciones admin | Media | Sin trazabilidad |
| Cloudflare / WAF | Baja | DDoS |
| Secrets vault (Doppler, AWS) | Baja | Gestión de secrets en prod |

### 🎯 Plan de remediación — 3 cambios urgentes

**Objetivo:** Máxima seguridad con mínimo riesgo operacional (0 usuarios activos en producción).

| # | Cambio | Archivos a modificar |
|---|--------|----------------------|
| 1 | **Token de admin fuerte**: Generar `ADMIN_TOKEN` con `secrets.token_hex(32)` (64 chars). Agregar startup migration para actualizar token admin en DB si cambia la env var. | `app/main.py`, Render Dashboard |
| 2 | **Tokens hasheados en DB**: Almacenar SHA-256(token) en lugar de token plano. Comparar hash vs hash en `get_current_user`, login, register, reset token. | `app/models.py`, `app/services/auth_service.py`, `app/routers/auth.py`, `app/routers/users.py`, `app/calculos/router.py` |
| 3 | **Sentry**: Agregar `sentry-sdk>=2.0.0`, inicializar en `main.py` con `Sentry.init()`, agregar `SENTRY_DSN` a env vars. | `requirements.txt`, `app/main.py`, Render Dashboard |

**Nota:** Con 0 usuarios, no se requiere migración de datos — los cambios son deploy-and-go.

Creado por JM
