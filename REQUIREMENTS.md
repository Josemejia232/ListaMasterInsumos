# ListaMasterInsumos — Requisitos

## 1. Autenticación y roles
- 1.1. Login con email + token (API key, no JWT)
- 1.2. Registro gratuito: genera token automáticamente
- 1.3. Login con token pre-asignado
- 1.4. Dos roles: **admin** y **usuario**
- 1.5. Admin seed automático al iniciar: `admin@example.com` / `admin123`
- 1.6. Admin puede CRUD de usuarios (email, token, activo, tipo)
- 1.7. Bearer token en header `Authorization` para endpoints protegidos

## 2. Base de datos
- 2.1. Usar **exclusivamente** Neon PostgreSQL (sin archivos locales ni SQLite)
- 2.2. Tabla `productos`: id, codigo, descripcion, unidad, valor, valor_anterior, origen, categoria, tienda, url_origen, created_at, updated_at
- 2.3. Tabla `insumos`: id, descripcion, un, valor, created_at (legacy)
- 2.4. Tabla `usuarios`: id, email, token, activo, tipo, created_at
- 2.5. Unique constraint `(codigo, tienda)` en productos
- 2.6. `origen` columna: "sheet" (Google Sheets) o "manual" (scrape directo)
- 2.7. `DATABASE_URL` desde variable de entorno (`.env` en local, env var en Render)

## 3. Scraping
- 3.1. Leer URLs desde Google Sheets (export CSV vía HTTP, sin gspread)
- 3.2. Columna `URL` obligatoria, columna `CATEGORIA` opcional
- 3.3. Scrapers por tienda: Sodimac, Homecenter, Promart, Maestro, Easy
- 3.4. GenericScraper multi-estrategia: JSON-LD (gana), embedded state, meta tags, HTML patterns
- 3.5. JSON-LD case-insensitive para `@type`, `offers` como array
- 3.6. Upsert: si precio cambió → guarda valor anterior y actualiza; si no cambió → saltea (pero siempre actualiza categoria)
- 3.7. Endpoint `/scrape/daily`: procesa todas las URLs de la hoja configurada en `SHEET_URL`
- 3.8. Endpoint `/scrape/sync` (admin): scrapea una URL específica y devuelve el producto
- 3.9. Script standalone `app/daily.py` para cron externo

## 4. Frontend
- 4.1. Single-page application (HTML + CSS + JS vanilla) servida por FastAPI como estático
- 4.2. Página de login con dos tabs: "Registrarse gratis" y "Con token"
- 4.3. Sidebar colapsible, oculto por defecto, responsive (media queries)
- 4.4. Vista admin (sidebar): Productos, Usuarios
- 4.5. Vista usuario (sidebar): Insumos
- 4.6. Tabla Insumos para admin: columnas ID, DESCRIPCION, UNIDAD, VALOR, CATEGORIA
- 4.7. Tabla Insumos para usuario: columnas ID (formato 0001), DESCRIPCION., UNIDAD, VALOR., CATEGORIA
- 4.8. Columna VALOR. para usuario: precio original reducido aleatoriamente 0.02%-0.04% (entero, sin decimales)
- 4.9. Columna DESCRIPCION. para usuario: descripción con sufijo aleatorio para diferir del original
- 4.10. Flechas de cambio de precio: rojo ↑ si subió, verde ↓ si bajó, con porcentaje
- 4.11. Auto-refresh de productos cada 30 segundos
- 4.12. La URL de Google Sheets **no** se expone al frontend

## 5. Despliegue
- 5.1. Servir con uvicorn via Procfile en Render
- 5.2. Python 3.12.7 (runtime.txt)
- 5.3. Variables de entorno: `DATABASE_URL`, `SHEET_URL`, `ADMIN_EMAIL`, `ADMIN_TOKEN`
- 5.4. Comando dev local: `uvicorn app.main:app --reload`
