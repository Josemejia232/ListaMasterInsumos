# ListaMasterInsumos — Requisitos

> Este documento describe exactamente la estructura de la base de datos y el comportamiento de la aplicación.
> Cualquier cambio en la BD debe reflejarse aquí y viceversa.

## 1. Autenticación y roles
- 1.1. Login con email + token (el administrador proporciona el token)
- 1.2. Registro gratuito: solo ingresa si esta interesado debe comunicarse con el admin para obtener uno. 
- 1.3. Login con token pre-asignado
- 1.4. Dos roles: **admin** y **usuario**
- 1.5. Admin seed automático al iniciar: `admin@example.com` / `admin123`
- 1.6. Admin puede CRUD de usuarios (email, token, activo, tipo)
- 1.7. Bearer token en header `Authorization` para endpoints protegidos
- 1.8. El usuario no ve el contenido del admin




## 2. Base de datos
- 2.1. Usar **exclusivamente** Neon PostgreSQL (sin archivos locales ni SQLite)
- 2.2. Tabla `productos`: id (PK), codigo, descripcion, unidad, valor, valor_anterior, origen ('sheet'|'manual'), categoria, tienda, url_origen, created_at, updated_at
- 2.3. Tabla `insumos` (legacy): id (PK), descripcion, un, valor, categoria, created_at
- 2.4. Tabla `usuarios`: id (PK), email (unique), token, activo (bool), tipo ('admin'|'usuario'), created_at
- 2.5. Unique constraint `(codigo, tienda)` en productos
- 2.6. `origen` columna: "sheet" (Google Sheets) o "manual" (scrape directo)
- 2.7. `DATABASE_URL` desde variable de entorno (`.env` en local, env var en Render)
- 2.8. La BD debe identificar automáticamente si ingresa un nuevo insumo desde Google Sheets y copiarlo en la BD (ver sección 6)
- 2.9. El Google Sheet debe actualizarse cuando se detecta un cambio de precio (ver sección 6)


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
- 4.2. Página de login con dos tabs: "Registrarse gratis" (información de contacto) e "Ingresar" (email + token para usuarios ya registrados)
- 4.3. Sidebar colapsible, oculto por defecto, responsive (media queries)
- 4.3.1. El menú tiene dos módulos según el rol:
  - **Admin**: módulo **ADMIN** (Productos, Usuarios) + módulo **LISTA INSUMOS** (Insumos) con contador total
  - **Usuario**: módulo **LISTA INSUMOS** (Insumos) con contador total
- 4.4. Vista admin (sidebar): Productos, Usuarios
- 4.5. Vista usuario (sidebar): Insumos
- 4.6. Tabla Insumos para admin (datos originales + ajustados): columnas ID, DESCRIPCION, DESCRIPCION., UNIDAD, VALOR, VALOR., CATEGORIA
  - DESCRIPCION = descripción original del scraper
  - DESCRIPCION. = descripción homologada (misma que ve el usuario)
  - VALOR = precio original sin ajustes
  - VALOR. = precio ajustado (mismo que ve el usuario)
- 4.6.1. La sección "Usuario — datos ajustados" NO debe aparecer en el panel del admin
- 4.6.2. La vista admin debe mostrar el número total de insumos (ej: "Total: X insumos") sobre la tabla
- 4.7. Tabla Insumos para usuario (datos ajustados): columnas ID (formato 0001), DESCRIPCION., UNIDAD, VALOR., CATEGORIA
  - DESCRIPCION. = descripción homologada, NO es la misma descripción original (ver 4.9)
  - VALOR. = precio con reducción % aplicada (ver 4.8)
- 4.8. Columna VALOR. para usuario: precio original reducido aleatoriamente 0.02%-0.04% (entero, sin decimales)
- 4.9. Columna DESCRIPCION. para usuario: descripción homologada con sufijo aleatorio para diferir de la original
- 4.10. Flechas de cambio de precio: rojo ↑ si subió, verde ↓ si bajó, con porcentaje
- 4.11. Auto-refresh de productos cada 30 segundos
- 4.12. La URL de Google Sheets **no** se expone al frontend

## 5. Despliegue
- 5.1. Servir con uvicorn via Procfile en Render
- 5.2. Python 3.12.7 (runtime.txt)
- 5.3. Variables de entorno: `DATABASE_URL`, `SHEET_URL`, `ADMIN_EMAIL`, `ADMIN_TOKEN`
- 5.4. Comando dev local: `uvicorn app.main:app --reload`

## 6. Sincronización Google Sheets ↔ BD

- 6.1. **Sheet → BD**: Al ejecutar `/scrape/daily` o `python -m app.daily`, la app lee las URLs y categorías desde Google Sheets, scrapea los precios y los upserta en la tabla `productos`. Si una URL nueva aparece en el sheet, se crea un nuevo registro en BD. Si cambia la categoría en el sheet, se actualiza en BD aunque el precio no haya cambiado.
- 6.2. **BD → Sheet (pendiente)**: Cuando el scraper detecta un cambio de precio en una URL, ese nuevo precio debe escribirse de vuelta en el Google Sheet (columna ÚLTIMO PRECIO). Actualmente esto no está implementado. Se requiere Google Apps Script (`scripts/syncPrices.gs`) que:
  - Se ejecuta periódicamente (time-driven trigger)
  - Llama a `/scrape/daily` para actualizar la BD
  - Consulta `/productos` y escribe los precios actuales en el sheet
  - Para producción, la API debe tener URL pública (Render). Para local, usar ngrok.
- 6.3. La URL del Google Sheet (`SHEET_URL`) nunca se expone al frontend.
