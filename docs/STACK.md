# ListaMasterInsumos — Stack

| Capa | Tecnologia |
|------|-----------|
| **Runtime** | Python 3.12.7 |
| **Framework** | FastAPI |
| **ORM** | SQLAlchemy 2.0 |
| **Base de datos** | PostgreSQL 15 (Neon serverless) |
| **Driver DB** | psycopg2-binary |
| **HTTP client** | httpx |
| **HTML parsing** | BeautifulSoup4 + lxml |
| **Google Sheets** | Export CSV via HTTP (sin gspread) |
| **Auth** | Token por usuario (API key), roles admin/usuario, timing-safe comparison |
| **Seguridad** | CORS, rate limiting, security headers, XSS protection, validacion Pydantic |
| **Frontend** | HTML + CSS + JS vanilla (sin framework), paleta SAS Premium |
| **Servidor dev** | uvicorn con hot-reload |
| **Deploy** | Render (web service, Procfile) |
| **Entorno** | python-dotenv, config/.env.develop, config/.env.production |
