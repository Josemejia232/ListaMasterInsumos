#!/bin/bash
echo "[DEV] Cargando entorno de desarrollo..."
cp -f .env.develop .env
echo "[DEV] Iniciando servidor con hot-reload en puerto 8000..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
