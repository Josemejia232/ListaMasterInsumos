#!/bin/bash
echo "[PROD] Cargando entorno de produccion..."
cp -f config/.env.production .env 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
