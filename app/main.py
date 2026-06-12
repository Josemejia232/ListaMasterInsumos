import asyncio
import os
import json
import re
import time
import random
import hmac
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

from app.database import engine, get_db, SessionLocal, Base, IS_SQLITE
from app.models import Producto, Insumo, Usuario, Pago, UsoCalculo, RateLimit, CacheEntry
from app.sheets import read_urls_from_sheet
from app.scrapers import get_scraper
from app import bold as bold_client
from app.calculos import router as calculos_router
from app.services.auth_service import get_current_user, require_admin, _plan_info, _plan_activo
from app.services.product_service import _normalize_url, _find_by_url, _upsert_producto
from app.dependencies import (
    rate_limit_login, rate_limit_scrape,
    _get_cache, _set_cache, _invalidate_cache,
    _validate_sheet_url, _validate_scrape_url,
    SHEET_URL,
)
from app.schemas import (
    ScrapeRequest, ScrapeResponse, SyncResponse,
    ProductoResponse, InsumoRequest, InsumoResponse, ProductoPublicResponse,
    LoginRequest, LoginResponse, UpdateAjustadaRequest,
    UsuarioRequest, UsuarioResponse,
    CrearLinkRequest, CrearLinkResponse, PagoResponse,
    ComprarPlanResponse, ComprarPlanRequest, UpgradePlanResponse, PlanInfo,
)

# Import routers
from app.routers import auth as auth_router
from app.routers import users as users_router
from app.routers import products as products_router
from app.routers import payments as payments_router
from app.routers import scraping as scraping_router
from app.routers import materiales as materiales_router

load_dotenv()

logger = logging.getLogger("app")

app = FastAPI(
    title="ListaMasterInsumos",
    description="API para scrapeo de insumos de construccion desde Google Sheets",
)

# ─── CORS ─────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

if not ALLOWED_ORIGINS:
    logger.warning("ALLOWED_ORIGINS no configurado. CORS deshabilitado (solo origen del mismo sitio).")
    ALLOWED_ORIGINS = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(GZipMiddleware, minimum_size=500)

# ─── HTTPS Redirect ───────────────────────────────────────────
FORCE_HTTPS = os.getenv("FORCE_HTTPS", "true").lower() in ("true", "1", "yes")

@app.middleware("http")
async def https_redirect(request: Request, call_next):
    if FORCE_HTTPS and request.url.scheme == "http" and "localhost" not in request.url.hostname and "127.0.0.1" not in request.url.hostname and "testserver" not in request.url.hostname:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(str(request.url.replace(scheme="https")), status_code=301)
    return await call_next(request)

# ─── Security Headers ─────────────────────────────────────────
CSP_HEADER = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data: https:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = CSP_HEADER
    return response

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(calculos_router)
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router.router, prefix="/api/usuarios", tags=["usuarios"])
app.include_router(products_router.router, prefix="/productos", tags=["productos"])
app.include_router(payments_router.router, prefix="/api/pagos", tags=["pagos"])
app.include_router(scraping_router.router, prefix="", tags=["scraping"])
app.include_router(materiales_router.router)

# ─── Debug ────────────────────────────────────────────────────

@app.get("/debug/sin-categoria", response_model=list[ProductoResponse])
def debug_sin_categoria(_admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    """Lista productos que no tienen categoría asignada (NULL o vacío)."""
    prods = (
        db.query(Producto)
        .filter(
            (Producto.categoria == None) | (Producto.categoria == "")
        )
        .order_by(Producto.created_at.desc())
        .limit(100)
        .all()
    )
    return prods


# ─── Stats ────────────────────────────────────────────────────

@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Producto.id)).scalar() or 0
    total_valor = db.query(func.coalesce(func.sum(Producto.valor), 0)).scalar() or 0.0
    hoy = db.query(func.count(Producto.id)).filter(
        func.date(Producto.created_at) == func.current_date()
    ).scalar() or 0
    tiendas = [
        r[0] for r in db.query(Producto.tienda).distinct().order_by(Producto.tienda).all()
    ]
    return {"total": total, "total_valor": total_valor, "scrapeados_hoy": hoy, "tiendas": tiendas}


# ─── Webhook Bold ─────────────────────────────────────────────

import hashlib
import base64
import hmac as hmac_lib
from app import bold as bold_client

BOLD_WEBHOOK_IPS = os.getenv("BOLD_WEBHOOK_IPS", "").split(",")
BOLD_WEBHOOK_IPS = [ip.strip() for ip in BOLD_WEBHOOK_IPS if ip.strip()]

@app.post("/api/webhooks/bold")
async def webhook_bold(request: Request, db: Session = Depends(get_db)):
    # Validar IP de origen (si está configurada)
    if BOLD_WEBHOOK_IPS:
        client_ip = request.headers.get("x-forwarded-for", request.client.host or "")
        client_ip = client_ip.split(",")[0].strip()
        if client_ip not in BOLD_WEBHOOK_IPS:
            logger.warning(f"[Webhook] IP no autorizada: {client_ip}")
            raise HTTPException(status_code=403, detail="IP no autorizada")

    body = await request.body()
    signature = request.headers.get("x-bold-signature", "")

    body_str = body.decode("utf-8")
    encoded = base64.b64encode(body_str.encode("utf-8"))
    computed = hmac_lib.new(
        key=bold_client.BOLD_SECRET.encode(),
        digestmod=hashlib.sha256,
        msg=encoded,
    ).hexdigest()

    if not hmac_lib.compare_digest(computed, signature):
        logger.warning("[Webhook] Firma invalida")
        raise HTTPException(status_code=400, detail="Firma invalida")

    try:
        event = json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=400, detail="JSON invalido")

    logger.info(f"[Webhook] Evento recibido: type={event.get('type')} subject={event.get('subject')}")

    event_type = event.get("type", "")
    if event_type not in ("SALE_APPROVED", "SALE_REJECTED"):
        return {"status": "ignored", "type": event_type}

    data = event.get("data", {})
    reference = data.get("metadata", {}).get("reference", "")

    if not reference:
        return {"status": "no_reference"}

    pago = db.query(Pago).filter(Pago.reference == reference).first()
    if not pago:
        logger.info(f"[Webhook] Pago no encontrado para referencia: {reference}")
        return {"status": "pago_no_encontrado"}

    if event_type == "SALE_APPROVED":
        pago.status = "PAID"
        pago.transaction_id = data.get("payment_id", "")
        usuario = db.query(Usuario).filter(Usuario.id == pago.usuario_id).first()
        if usuario:
            usuario.fecha_pago = func.now()
            ref = pago.reference or ""
            if ref.startswith("basico_"):
                usuario.plan = "basico"
            elif ref.startswith("upgrade_") or ref.startswith("plus_"):
                usuario.plan = "plus"
    else:
        pago.status = "REJECTED"
        pago.transaction_id = data.get("payment_id", "")

    db.commit()
    logger.info(f"[Webhook] Pago {pago.id} actualizado a {pago.status}")
    return {"status": "ok", "pago_id": pago.id, "pago_status": pago.status}


# ─── Insumos CRUD (legacy) ────────────────────────────────────

@app.get("/api/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    existe = db.query(Usuario).filter(Usuario.email == email).first()
    return {"registrado": existe is not None}

@app.get("/api/insumos", response_model=list[ProductoPublicResponse])
def listar_insumos(db: Session = Depends(get_db)):
    return db.query(Producto).order_by(Producto.descripcion).all()

@app.post("/api/insumos", response_model=InsumoResponse)
def crear_insumo(req: InsumoRequest, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = Insumo(descripcion=req.descripcion, un=req.un, valor=req.valor)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.put("/api/insumos/{insumo_id}", response_model=InsumoResponse)
def actualizar_insumo(insumo_id: int, req: InsumoRequest, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    item.descripcion = req.descripcion
    item.un = req.un
    item.valor = req.valor
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/insumos/{insumo_id}")
def eliminar_insumo(insumo_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── Root ─────────────────────────────────────────────────────

_index_html = None
_index_mtime = 0

@app.on_event("startup")
def startup():
    if IS_SQLITE:
        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            try:
                result = conn.execute(text("PRAGMA table_info(usuarios)")).fetchall()
                cols = [r[1] for r in result]
                if "plan" not in cols:
                    conn.execute(text("ALTER TABLE usuarios ADD COLUMN plan VARCHAR(10)"))
                    conn.commit()
                    logger.info("[Migration] Added plan column to usuarios (SQLite)")
            except Exception as e:
                logger.warning(f"[Migration] plan column skipped: {e}")
            try:
                result = conn.execute(text("PRAGMA table_info(productos)")).fetchall()
                cols = [r[1] for r in result]
                if "material" not in cols:
                    conn.execute(text("ALTER TABLE productos ADD COLUMN material VARCHAR(200)"))
                    conn.commit()
                    logger.info("[Migration] Added material column to productos (SQLite)")
            except Exception as e:
                logger.warning(f"[Migration] material column skipped: {e}")
            try:
                result = conn.execute(text("PRAGMA table_info(user_material_overrides)")).fetchall()
                cols = [r[1] for r in result]
                if "mezcla_id" not in cols:
                    conn.execute(text("ALTER TABLE user_material_overrides ADD COLUMN mezcla_id VARCHAR(100) DEFAULT ''"))
                    conn.commit()
                    logger.info("[Migration] Added mezcla_id column to user_material_overrides (SQLite)")
            except Exception as e:
                logger.warning(f"[Migration] mezcla_id column skipped: {e}")
    else:
        try:
            from alembic.config import Config
            from alembic import command
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            logger.info("[Alembic] Migrations applied successfully")
        except Exception as e:
            logger.warning(f"[Alembic] Migration failed, falling back to create_all: {e}")
            Base.metadata.create_all(bind=engine)
            try:
                command.stamp(alembic_cfg, "head")
                logger.info("[Alembic] Stamped as head to prevent future failures")
            except Exception as stamp_e:
                logger.info(f"[Alembic] Stamp skipped: {stamp_e}")

    global _index_html, _index_mtime
    index_path = static_dir / "index.html"
    if index_path.exists():
        _index_html = index_path.read_text(encoding="utf-8")
        _index_mtime = index_path.stat().st_mtime

    db = SessionLocal()
    try:
        from datetime import timedelta
        ahora = datetime.utcnow()
        legacy = db.query(Usuario).filter(
            Usuario.fecha_pago.isnot(None),
            Usuario.plan.is_(None),
            Usuario.tipo != "admin",
        ).all()
        for u in legacy:
            u.plan = "plus"
            logger.info(f"[Migration] Legacy user {u.email} → plan=plus")
        if legacy:
            db.commit()

        admin = db.query(Usuario).filter(Usuario.tipo == "admin").first()
        if not admin:
            admin_email = os.getenv("ADMIN_EMAIL")
            admin_token = os.getenv("ADMIN_TOKEN")
            if not admin_email or not admin_token:
                logger.warning("ADMIN_EMAIL o ADMIN_TOKEN no configurados en .env — seed admin omitido")
            else:
                db.add(Usuario(email=admin_email, token=admin_token, activo=True, tipo="admin"))
                db.commit()
                logger.info(f"Admin seed creado: {admin_email}")
    except Exception as e:
        db.rollback()
        logger.warning(f"Seed admin skipped: {e}")
    finally:
        db.close()

@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

@app.get("/")
def root():
    from fastapi.responses import HTMLResponse
    landing = static_dir / "landing.html"
    if landing.exists():
        return HTMLResponse(content=landing.read_text(encoding="utf-8"))
    return {"app": "ListaMasterInsumos", "status": "ok"}

@app.get("/landing")
def landing():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=301)

@app.get("/app")
def app_page():
    global _index_html, _index_mtime
    index = static_dir / "index.html"
    if index.exists():
        current_mtime = index.stat().st_mtime
        if not _index_html or current_mtime != _index_mtime:
            _index_html = index.read_text(encoding="utf-8")
            _index_mtime = current_mtime
    if _index_html:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=_index_html)
    return {"app": "ListaMasterInsumos", "status": "ok"}
    return {"error": "landing.html not found"}
