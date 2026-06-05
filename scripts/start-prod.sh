#!/bin/bash
echo "[PROD] Cargando entorno de produccion..."
cp -f config/.env.production .env
echo "[PROD] Iniciando servidor en produccion..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --timeout-keep-alive 30 --limit-concurrency 100
