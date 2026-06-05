# ListaMasterInsumos — Requisitos

> Este documento describe la estructura de la base de datos, el comportamiento de la aplicacion y la seguridad.
> Cualquier cambio en la BD debe reflejarse aqui y viceversa.

## 1. Autenticacion y roles
- 1.1. Login con email + token (token pre-asignado por el admin)
- 1.2. Usuario gratis: modo prueba gratuita para consultar la app. No se genera token automaticamente. Si el usuario paga, el admin le asigna un token de acceso.
- 1.3. Login con token pre-asignado: usuario ingresa email + token -> se guardan en localStorage por separado (`user` = {id, email, tipo}, `auth_token` = token)
- 1.4. Dos roles: **admin** y **usuario**
- 1.5. Admin seed automatico al iniciar: lee `ADMIN_EMAIL` y `ADMIN_TOKEN` desde `.env` (token de 16 caracteres hex). Si no estan configurados, no crea admin.
- 1.6. Admin puede CRUD de usuarios (email, activo, tipo). El token se expone en la API de usuarios (`UsuarioResponse` incluye campo `token`) solo para el panel admin (requiere auth de admin).
- 1.6.1. Panel USUARIOS (solo admin): tabla con ID, Email, Activo, Tipo, Token (primeros 16 chars + boton Copiar), FechaPago, Dias, Accion
  - FechaPago: fecha del ultimo pago del usuario (columna `fecha_pago` en BD)
  - Dias: dias restantes desde FechaPago hasta completar 30 dias. Si <= 0 -> rojo (vencido), <= 5 -> amarillo, > 5 -> verde
  - Accion: boton $ (Pagar) que actualiza FechaPago a la fecha actual, reiniciando el ciclo de 30 dias
  - Accion: boton Editar, Activar/Bloquear, Eliminar
- 1.7. Bearer token en header `Authorization` para endpoints protegidos
- 1.8. El usuario no ve el contenido del admin
- 1.9. Token generation: `secrets.token_hex(8)` (16 caracteres hex)
- 1.10. Token comparison: `hmac.compare_digest()` (timing-safe)
- 1.11. Frontend almacena token por separado: `localStorage.user` = {id, email, tipo}, `localStorage.auth_token` = token. La funcion `apiFetch()` lee `auth_token` para el header Authorization.

## 2. Seguridad

### 2.1. Endpoints publicos (sin auth)
- `GET /api/insumos` — datos de productos con categorias (descripcion, unidad, valor, categoria, n01, n02, n03, proveedor). Consulta la tabla `productos`.
- `GET /api/stats` — estadisticas generales (total, valor total, tiendas)

### 2.2. Endpoints protegidos (requieren Bearer token)
- `GET /productos` — precios de scraping, proveedores, URLs de origen
- `GET/POST/PUT/DELETE /api/insumos/*` — CRUD de insumos
- `PUT /productos/{id}` — edicion de productos
- `POST /scrape` — trigger de scraping
- `POST /scrape/daily` — scrape diario (cambiado de GET a POST)
- `POST /sync/categories` — sincronizacion de categorias
- `GET /scrape/sync` — scrape de URL individual
- `GET/POST/PUT/DELETE /api/usuarios/*` — gestion de usuarios
- `GET /api/auth/me` — verificar sesion

### 2.3. CORS
- Middleware configurado con origenes permitidos via variable `ALLOWED_ORIGINS`
- Si no se configura, permite todos (`*`)

### 2.4. Rate limiting
- Login: 10 intentos/minuto por IP
- Scrape: 5 peticiones/minuto por IP

### 2.5. Security headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

### 2.6. XSS Protection
- Funcion `escapeHtml()` en frontend para datos de API en innerHTML
- Todos los datos de scraping, usuarios y categorias se escapan antes de inyectar en DOM

### 2.7. Validacion de entrada
- Pydantic validators en schemas: email, tipo de usuario, URLs
- URLs de scraping restringidas a dominios Google Sheets (`docs.google.com`)
- Valores negativos rechazados en insumos

### 2.8. Proteccion de credenciales
- `.env` en `.gitignore` (nunca se sube a git)
- `.env.develop` y `.env.production` en `config/`
- Token admin no se loguea ni se expone en API
- Password de BD rotada periodicamente

## 3. Base de datos
- 3.1. Usar **exclusivamente** Neon PostgreSQL (sin archivos locales ni SQLite)
- 3.2. Tabla `productos`: id (PK), codigo, descripcion, unidad, valor, valor_anterior, origen ('sheet'|'manual'), categoria, n01, n02, n03, proveedor, descripcion_ajustada, tienda, url_origen, created_at, updated_at
- 3.3. Tabla `insumos` (legacy CRUD): id (PK), descripcion, un, valor, categoria, created_at. Solo usada por endpoints CRUD admin (`POST/PUT/DELETE /api/insumos`). El GET publico `/api/insumos` consulta la tabla `productos`.
- 3.4. Tabla `usuarios`: id (PK), email (unique), token, activo (bool), tipo ('admin'|'usuario'), fecha_pago, created_at
- 3.5. Unique constraint `(codigo, tienda)` en productos
- 3.6. `origen` columna: "sheet" (Google Sheets) o "manual" (scrape directo)
- 3.7. `DATABASE_URL` desde variable de entorno (`config/.env.develop` o `config/.env.production`, env var en Render)
- 3.8. Columnas `n01`, `n02`, `n03`: niveles jerarquicos de agrupacion desde Google Sheets (Nivel 1, Nivel 2, Nivel 3)
- 3.9. La BD debe identificar automaticamente si ingresa un nuevo insumo desde Google Sheets y copiarlo en la BD (ver seccion 6)
- 3.10. El Google Sheet debe actualizarse cuando se detecta un cambio de precio (ver seccion 6)

## 4. Scraping
- 4.1. Leer URLs desde Google Sheets (export CSV via HTTP, sin gspread)
- 4.2. Columna `URL` obligatoria, columnas `N01`, `N02`, `N03`, `CATEGORIA` y `PROVEEDOR` opcionales
- 4.3. Scrapers por tienda: Sodimac, Homecenter, Promart, Maestro, Easy
- 4.4. GenericScraper multi-estrategia: JSON-LD (gana), embedded state, meta tags, HTML patterns
- 4.5. JSON-LD case-insensitive para `@type`, `offers` como array
- 4.6. Upsert: si precio cambio -> guarda valor anterior y actualiza; si no cambio -> saltea (pero siempre actualiza categoria)
- 4.7. Endpoint `POST /scrape/daily` (admin): procesa todas las URLs de la hoja configurada en `SHEET_URL`
- 4.8. Endpoint `GET /scrape/sync` (admin): scrapea una URL especifica y devuelve el producto
- 4.9. Script standalone `app/daily.py` para cron externo
- 4.10. Validacion de URLs: solo se permiten dominios Google Sheets (`docs.google.com`)

## 5. Frontend
- 5.1. Single-page application (HTML + CSS + JS vanilla) servida por FastAPI como estatico
- 5.2. Pagina de login con dos tabs: "Usuario gratis" (prueba gratuita, debe ingresar email) e "Ingresar con token" (login con email + token asignado por el admin)
- 5.3. Sidebar colapsible, oculto por defecto, responsive (media queries)
- 5.3.1. El menu tiene dos modulos segun el rol:
  - **Admin**: modulo **ADMIN** (Productos, Usuarios) + modulo **LISTA INSUMOS** (Insumos) con contador total
  - **Usuario/Guest**: modulo **LISTA INSUMOS** (Insumos) con contador total
- 5.4. Vista admin (sidebar): Productos, Usuarios
- 5.5. Vista usuario/guest (sidebar): Insumos
- 5.6. Guest mode: usa `/api/insumos` (publico) en vez de `/productos` (protegido). `/api/insumos` retorna los mismos datos de la tabla `productos` con categorias (n01, n02, n03, proveedor).
- 5.7. Tabla unica para admin, usuario e invitado: columnas DESCRIPCION, UNIDAD, VALOR, PROVEEDOR
  - Muestra los datos reales del scraper sin ajustes ni variaciones
  - Los insumos se agrupan jerarquicamente por N01 > N02 > N03 con encabezados colapsables
  - Solo N01 es colapsable (expande/contrae todo su subnivel)
  - N02 y N03 son headers visuales con padding .05rem
  - Botones "Expandir todo" y "Contraer todo" para controlar la vista
  - Admin adicionalmente tiene vista raw (datos originales editables) y panel USUARIOS
  - La vista muestra el numero total de insumos (ej: "Total: X insumos") sobre la tabla
- 5.8. Flechas de cambio de precio: rojo si subio, verde si bajo, con porcentaje
- 5.9. Auto-refresh de productos cada 30 segundos
- 5.10. La URL de Google Sheets **no** se expone al frontend
- 5.11. Paleta de colores: SAS Premium (navy blue + gradients)
- 5.12. XSS protection: funcion `escapeHtml()` en todos los innerHTML

## 6. Despliegue
- 6.1. Servir con uvicorn via Procfile en Render
- 6.2. Python 3.12.7 (runtime.txt)
- 6.3. Variables de entorno: `DATABASE_URL`, `SHEET_URL`, `ADMIN_EMAIL`, `ADMIN_TOKEN` (16 chars hex), `ALLOWED_ORIGINS`
- 6.4. Comando dev local: `scripts/start-dev.bat` (Windows) o `bash scripts/start-dev.sh` (Linux/Mac)
- 6.5. Comando prod local: `scripts/start-prod.bat` (Windows) o `bash scripts/start-prod.sh` (Linux/Mac)
- 6.6. Estructura de archivos:
  - `app/` — codigo Python
  - `config/` — archivos de entorno (.env.develop, .env.production)
  - `docs/` — documentacion (STACK.md, REQUIREMENTS.md)
  - `scripts/` — scripts de inicio y auxiliares

## 7. Sincronizacion Google Sheets <-> BD

- 7.1. **Sheet -> BD**: Al ejecutar `POST /scrape/daily` o `python -m app.daily`, la app lee las URLs y categorias desde Google Sheets, scrapea los precios y los upserta en la tabla `productos`. Si una URL nueva aparece en el sheet, se crea un nuevo registro en BD. Si cambia la categoria en el sheet, se actualiza en BD aunque el precio no haya cambiado.
- 7.2. **BD -> Sheet (pendiente)**: Cuando el scraper detecta un cambio de precio en una URL, ese nuevo precio debe escribirse de vuelta en el Google Sheet (columna ULTIMO PRECIO). Actualmente esto no esta implementado. Se requiere Google Apps Script (`scripts/syncPrices.gs`) que:
  - Se ejecuta periodicamente (time-driven trigger)
  - Llama a `POST /scrape/daily` para actualizar la BD
  - Consulta `/productos` y escribe los precios actuales en el sheet
  - Para produccion, la API debe tener URL publica (Render). Para local, usar ngrok.
- 7.3. La URL del Google Sheet (`SHEET_URL`) nunca se expone al frontend.
