import asyncio
import os
import json
import re
import time
import random
import hmac
import logging
from datetime import datetime, timezone
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
from app.models import Producto, Insumo, Usuario, Pago, UsoCalculo
from app.sheets import read_urls_from_sheet
from app.scrapers import get_scraper
from app import bold as bold_client
from app.calculos import router as calculos_router

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
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(GZipMiddleware, minimum_size=500)

# ─── Security Headers ─────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# ─── Rate Limiting ────────────────────────────────────────────
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds

def _check_rate_limit(key: str, max_requests: int) -> bool:
    now = time.time()
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[key]) >= max_requests:
        return False
    _rate_limit_store[key].append(now)
    return True

def rate_limit_login(request: Request):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(f"login:{ip}", 10):
        raise HTTPException(status_code=429, detail="Demasiados intentos. Intenta en 1 minuto.")

def rate_limit_scrape(request: Request):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(f"scrape:{ip}", 5):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones de scrape. Intenta en 1 minuto.")

# Simple in-memory cache
_cache = {}
_cache_time = 0
CACHE_TTL = 10  # seconds

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

SHEET_URL = os.getenv("SHEET_URL", "")

app.include_router(calculos_router)

# ─── Schemas ──────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    sheet_url: str
    @field_validator("sheet_url")
    @classmethod
    def validate_sheet_url(cls, v):
        if not v or not v.startswith("https://"):
            raise ValueError("URL debe ser HTTPS valida")
        if "docs.google.com" not in v:
            raise ValueError("URL debe ser de Google Sheets")
        return v

class ScrapeResponse(BaseModel):
    total: int
    nuevos: int
    actualizados: int
    sin_cambio: int
    fallidos: int
    mensaje: str

class SyncResponse(BaseModel):
    total: int
    actualizados: int
    sin_cambio: int
    no_encontrados: int
    sin_categoria: int
    urls_no_encontradas: list[str] = []
    mensaje: str

class ProductoResponse(BaseModel):
    id: int
    codigo: str
    descripcion: str
    descripcion_ajustada: str | None = None
    unidad: str
    valor: float
    valor_anterior: float | None = None
    origen: str | None = None
    categoria: str | None = None
    n01: str | None = None
    n02: str | None = None
    n03: str | None = None
    proveedor: str | None = None
    tienda: str
    url_origen: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}

class InsumoRequest(BaseModel):
    descripcion: str
    un: str = "Unidad"
    valor: float = 0.0
    @field_validator("valor")
    @classmethod
    def validate_valor(cls, v):
        if v < 0:
            raise ValueError("Valor no puede ser negativo")
        return v

class InsumoResponse(InsumoRequest):
    id: int
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

class ProductoPublicResponse(BaseModel):
    id: int
    descripcion: str
    unidad: str
    valor: float
    categoria: str | None = None
    n01: str | None = None
    n02: str | None = None
    n03: str | None = None
    proveedor: str | None = None
    model_config = {"from_attributes": True}

class LoginRequest(BaseModel):
    email: str
    token: str
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email invalido")
        return v.strip().lower()

class LoginResponse(BaseModel):
    id: int
    email: str
    token: str = ""
    tipo: str
    plan: str | None = None
    fecha_pago: datetime | None = None
    plan_activo: bool = False

class UpdateAjustadaRequest(BaseModel):
    descripcion_ajustada: str | None = None
    categoria: str | None = None
    n01: str | None = None
    n02: str | None = None
    n03: str | None = None
    proveedor: str | None = None

class UsuarioRequest(BaseModel):
    email: str
    token: str = ""
    activo: bool = True
    tipo: str = "usuario"
    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        if v not in ("admin", "usuario"):
            raise ValueError("Tipo debe ser 'admin' o 'usuario'")
        return v
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email invalido")
        return v.strip().lower()

class UsuarioResponse(BaseModel):
    id: int
    email: str
    token: str
    activo: bool
    tipo: str
    fecha_pago: datetime | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class CrearLinkRequest(BaseModel):
    usuario_id: int
    amount: float
    description: str = "Suscripcion ListaMasterInsumos"
    expiration_minutes: int = 60
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v < 1000:
            raise ValueError("Monto minimo: $1,000 COP")
        return v

class CrearLinkResponse(BaseModel):
    id: int
    payment_link: str
    url: str
    reference: str
    amount: float
    status: str

class PagoResponse(BaseModel):
    id: int
    usuario_id: int
    payment_link: str
    url: str
    reference: str
    amount: float
    status: str
    transaction_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}

class ComprarPlanResponse(BaseModel):
    id: int
    url: str
    amount: float
    status: str


class ComprarPlanRequest(BaseModel):
    plan: str  # "basico" | "plus"
    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v):
        if v not in ("basico", "plus"):
            raise ValueError("Plan debe ser 'basico' o 'plus'")
        return v


class UpgradePlanResponse(BaseModel):
    id: int
    url: str
    amount: float
    monto_original: float = 15000.0
    credito_basico: float = 0.0
    status: str


class PlanInfo(BaseModel):
    plan: str  # "free" | "basico" | "plus"
    activo: bool
    dias_restantes: int | None = None
    puede_upgradear: bool = False
    upgrade: dict | None = None


# ─── Auth ─────────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    logger.info(f"[AUTH] Authorization header: {repr(authorization[:50]) if authorization else 'NONE'}")
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato invalido")
    token = authorization[7:]
    users = db.query(Usuario).filter(Usuario.activo == True).all()
    logger.info(f"[AUTH] Token from header: {token[:20]}... | Active users in DB: {len(users)}")
    for user in users:
        if user.token:
            logger.info(f"[AUTH] Comparing with user {user.email}: token_prefix={user.token[:8]}...")
        if hmac.compare_digest(token, user.token or ""):
            return user
    raise HTTPException(status_code=401, detail="Token invalido o usuario inactivo")

def require_admin(user: Usuario = Depends(get_current_user)):
    if user.tipo != "admin":
        raise HTTPException(status_code=403, detail="Se requiere permisos de admin")
    return user


# ─── URL Validation (SSRF prevention) ────────────────────────

ALLOWED_SHEET_DOMAINS = ["docs.google.com", "sheets.google.com"]

def _validate_sheet_url(url: str):
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("URL debe ser HTTPS")
        if parsed.hostname not in ALLOWED_SHEET_DOMAINS:
            raise ValueError(f"Dominio no permitido: {parsed.hostname}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Upsert ───────────────────────────────────────────────────

def _normalize_url(u: str) -> str:
    """Normaliza URL para matching: remove www, trailing slash, query params."""
    if not u:
        return ""
    u = u.strip().lower()
    u = re.sub(r"https?://(www\.)?", "https://", u)
    u = u.split("?")[0]
    u = u.rstrip("/")
    return u


def _find_by_url(db: Session, url: str) -> Producto | None:
    """Busca producto por URL exacta, luego normalizada."""
    prod = db.query(Producto).filter(Producto.url_origen == url).first()
    if prod:
        return prod
    norm = _normalize_url(url)
    if not norm:
        return None
    todos = db.query(Producto).filter(Producto.url_origen.isnot(None)).all()
    for p in todos:
        if _normalize_url(p.url_origen or "") == norm:
            return p
    return None


def _upsert_producto(db: Session, producto, origen: str = "manual", categoria: str | None = None, n01: str | None = None, n02: str | None = None, n03: str | None = None, proveedor: str | None = None) -> dict:
    if not producto.codigo:
        return "sin_cambio"
    existente = (
        db.query(Producto)
        .filter(Producto.codigo == producto.codigo, Producto.tienda == producto.tienda)
        .first()
    )
    if existente:
        existente.origen = existente.origen or origen
        if categoria and existente.categoria != categoria:
            existente.categoria = categoria
        elif categoria and not existente.categoria:
            existente.categoria = categoria
        if n01 and existente.n01 != n01:
            existente.n01 = n01
        elif n01 and not existente.n01:
            existente.n01 = n01
        if n02 and existente.n02 != n02:
            existente.n02 = n02
        elif n02 and not existente.n02:
            existente.n02 = n02
        if n03 and existente.n03 != n03:
            existente.n03 = n03
        elif n03 and not existente.n03:
            existente.n03 = n03
        if proveedor and existente.proveedor != proveedor:
            existente.proveedor = proveedor
        elif proveedor and not existente.proveedor:
            existente.proveedor = proveedor
        if abs(existente.valor - producto.valor) < 0.01:
            return "sin_cambio"
        existente.valor_anterior = existente.valor
        existente.descripcion = producto.descripcion
        existente.unidad = producto.unidad
        existente.valor = producto.valor
        existente.url_origen = producto.url
        existente.origen = existente.origen or origen
        existente.updated_at = func.now()
        return "actualizado"
    else:
        db_item = Producto(
            codigo=producto.codigo,
            descripcion=producto.descripcion,
            unidad=producto.unidad,
            valor=producto.valor,
            tienda=producto.tienda,
            url_origen=producto.url,
            origen=origen,
            categoria=categoria,
            n01=n01,
            n02=n02,
            n03=n03,
            proveedor=proveedor,
        )
        db.add(db_item)
        return "nuevo"


# ─── Auth endpoints ───────────────────────────────────────────

def _plan_info(user: Usuario) -> dict:
    if user.tipo == "admin":
        return {"plan": "plus", "activo": True, "dias_restantes": 9999}
    if not user.fecha_pago:
        return {"plan": "free", "activo": True, "dias_restantes": None}
    delta = (datetime.utcnow() - user.fecha_pago).days
    if delta >= 30:
        return {"plan": "free", "activo": True, "dias_restantes": None}
    plan = user.plan or "plus"
    return {"plan": plan, "activo": True, "dias_restantes": 30 - delta}


def _plan_activo(user: Usuario) -> bool:
    if user.tipo == "admin":
        return True
    if not user.fecha_pago:
        return False
    delta = datetime.utcnow() - user.fecha_pago
    return delta.days < 30

@app.post("/api/auth/register", response_model=LoginResponse)
def register(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit_login(request)
    existente = db.query(Usuario).filter(Usuario.email == req.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="Email ya registrado. Contacta al administrador.")
    import secrets
    token = secrets.token_hex(32)
    user = Usuario(email=req.email, token=token, activo=True, tipo="usuario")
    db.add(user)
    db.commit()
    db.refresh(user)
    info = _plan_info(user)
    return LoginResponse(id=user.id, email=user.email, token=user.token, tipo=user.tipo, plan=info["plan"], fecha_pago=user.fecha_pago, plan_activo=_plan_activo(user))

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit_login(request)
    user = db.query(Usuario).filter(
        Usuario.email == req.email,
        Usuario.activo == True
    ).first()
    if not user or not hmac.compare_digest(req.token, user.token or ""):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    info = _plan_info(user)
    return LoginResponse(id=user.id, email=user.email, tipo=user.tipo, plan=info["plan"], fecha_pago=user.fecha_pago, plan_activo=_plan_activo(user))

@app.get("/api/auth/me", response_model=LoginResponse)
def auth_me(user: Usuario = Depends(get_current_user)):
    info = _plan_info(user)
    return LoginResponse(id=user.id, email=user.email, tipo=user.tipo, plan=info["plan"], fecha_pago=user.fecha_pago, plan_activo=_plan_activo(user))

@app.get("/api/auth/planes", response_model=PlanInfo)
def ver_planes(user: Usuario = Depends(get_current_user)):
    info = _plan_info(user)
    result = {"plan": info["plan"], "activo": info["activo"], "dias_restantes": info["dias_restantes"]}
    if info["plan"] == "free":
        result["puede_upgradear"] = True
        result["upgrade"] = {"basico": 10000, "plus": 15000}
    elif info["plan"] == "basico":
        result["puede_upgradear"] = True
        dias_rest = info["dias_restantes"] or 0
        credito = round((10000 * dias_rest) / 30, 0)
        a_pagar = max(5000, round(15000 - credito, 0))
        result["upgrade"] = {"a_pagar": a_pagar, "credito": credito, "plus_full": 15000, "formula": f"$15.000 - ($10.000 × {dias_rest}/30) = ${a_pagar:,.0f}"}
    else:
        result["puede_upgradear"] = False
    return result


@app.post("/api/auth/comprar-plan", response_model=ComprarPlanResponse)
async def comprar_plan(
    req: ComprarPlanRequest,
    request: Request,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit_scrape(request)
    info = _plan_info(user)
    if info["plan"] != "free":
        raise HTTPException(status_code=400, detail="Ya tienes un plan activo. Usa /upgrade-plan para mejorar.")
    amounts = {"basico": 10000, "plus": 15000}
    amount = amounts.get(req.plan, 10000)
    desc = {"basico": "Plan Basico - Insumos ilimitados", "plus": "Plan Plus - Acceso completo"}
    reference = f"{req.plan}_usr_{user.id}_{int(time.time())}"
    try:
        payload = await bold_client.create_payment_link(
            amount_total=amount,
            description=desc.get(req.plan, "Plan ListaMasterInsumos"),
            reference=reference,
            payer_email=user.email,
            expiration_minutes=120,
        )
    except Exception as e:
        logger.error(f"[comprar-plan] Error Bold: {e}")
        raise HTTPException(status_code=502, detail=f"Error en pasarela de pago: {str(e)}")
    pago = Pago(
        usuario_id=user.id,
        payment_link=payload["payment_link"],
        url=payload["url"],
        reference=reference,
        amount=amount,
        status="ACTIVE",
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return ComprarPlanResponse(id=pago.id, url=pago.url, amount=pago.amount, status=pago.status)


@app.post("/api/auth/upgrade-plan", response_model=UpgradePlanResponse)
async def upgrade_plan(
    request: Request,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit_scrape(request)
    info = _plan_info(user)
    if info["plan"] != "basico":
        raise HTTPException(status_code=400, detail="Solo puedes hacer upgrade desde el plan Basico.")
    dias_rest = info["dias_restantes"] or 0
    if dias_rest <= 0:
        raise HTTPException(status_code=400, detail="Tu plan Basico ya vencio. Compra Plus directamente.")
    credito = round((10000 * dias_rest) / 30, 0)
    amount = max(5000, round(15000 - credito, 0))
    reference = f"upgrade_usr_{user.id}_{int(time.time())}"
    try:
        payload = await bold_client.create_payment_link(
            amount_total=amount,
            description="Upgrade a Plan Plus - Acceso completo",
            reference=reference,
            payer_email=user.email,
            expiration_minutes=120,
        )
    except Exception as e:
        logger.error(f"[upgrade-plan] Error Bold: {e}")
        raise HTTPException(status_code=502, detail=f"Error en pasarela de pago: {str(e)}")
    pago = Pago(
        usuario_id=user.id,
        payment_link=payload["payment_link"],
        url=payload["url"],
        reference=reference,
        amount=amount,
        status="ACTIVE",
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return UpgradePlanResponse(
        id=pago.id, url=pago.url, amount=amount,
        monto_original=15000.0, credito_basico=credito,
        status=pago.status,
    )
@app.get("/api/usuarios", response_model=list[UsuarioResponse])
def listar_usuarios(_admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(Usuario).order_by(Usuario.email).all()

@app.post("/api/usuarios", response_model=UsuarioResponse)
def crear_usuario(req: UsuarioRequest, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == req.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if not req.token:
        import secrets
        req.token = secrets.token_hex(32)
    item = Usuario(email=req.email, token=req.token, activo=req.activo, tipo=req.tipo)
    db.add(item)
    db.commit()
    db.refresh(item)
    return UsuarioResponse(id=item.id, email=item.email, token=item.token, activo=item.activo, tipo=item.tipo, fecha_pago=item.fecha_pago, created_at=item.created_at)

@app.put("/api/usuarios/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(usuario_id: int, req: UsuarioRequest, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if req.email:
        item.email = req.email
    if req.token:
        item.token = req.token
    item.activo = req.activo
    item.tipo = req.tipo
    db.commit()
    db.refresh(item)
    return UsuarioResponse(id=item.id, email=item.email, token=item.token, activo=item.activo, tipo=item.tipo, fecha_pago=item.fecha_pago, created_at=item.created_at)

@app.delete("/api/usuarios/{usuario_id}")
def eliminar_usuario(usuario_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}

@app.post("/api/usuarios/{usuario_id}/pago", response_model=UsuarioResponse)
def renovar_pago(usuario_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    item.fecha_pago = func.now()
    db.commit()
    db.refresh(item)
    return UsuarioResponse(id=item.id, email=item.email, token=item.token, activo=item.activo, tipo=item.tipo, fecha_pago=item.fecha_pago, created_at=item.created_at)

@app.post("/api/usuarios/{usuario_id}/reset-token")
def resetear_token(usuario_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    import secrets
    item.token = secrets.token_hex(16)
    db.commit()
    return {"token": item.token}


# ─── Scraping ─────────────────────────────────────────────────

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_from_sheet(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    _admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rate_limit_scrape(request)
    _validate_sheet_url(req.sheet_url)
    try:
        urls = await read_urls_from_sheet(req.sheet_url)
    except Exception:
        raise HTTPException(status_code=400, detail="Error al leer Google Sheets")
    if not urls:
        raise HTTPException(status_code=400, detail="No se encontraron URLs en la hoja")
    background_tasks.add_task(_procesar_urls_bg, urls)
    return ScrapeResponse(
        total=len(urls), nuevos=0, actualizados=0, sin_cambio=0, fallidos=0,
        mensaje=f"Procesando {len(urls)} URLs en segundo plano",
    )

def _procesar_urls_bg(entries: list[dict]):
    bg_db = SessionLocal()
    try:
        for i, entry in enumerate(entries):
            url = entry["url"] if isinstance(entry, dict) else entry
            cat = entry.get("categoria") if isinstance(entry, dict) else None
            n01 = entry.get("n01") if isinstance(entry, dict) else None
            n02 = entry.get("n02") if isinstance(entry, dict) else None
            n03 = entry.get("n03") if isinstance(entry, dict) else None
            prov = entry.get("proveedor") if isinstance(entry, dict) else None
            scraper = get_scraper(url)
            if not scraper:
                if cat or prov or n01 or n02 or n03:
                    prod = _find_by_url(bg_db, url)
                    if prod:
                        prod.origen = prod.origen or "sheet"
                        if cat and prod.categoria != cat: prod.categoria = cat
                        if n01 and prod.n01 != n01: prod.n01 = n01
                        if n02 and prod.n02 != n02: prod.n02 = n02
                        if n03 and prod.n03 != n03: prod.n03 = n03
                        if prov and prod.proveedor != prov: prod.proveedor = prov
                        bg_db.commit()
                continue
            try:
                producto = scraper.scrape()
                _upsert_producto(bg_db, producto, origen="sheet", categoria=cat, n01=n01, n02=n02, n03=n03, proveedor=prov)
                bg_db.commit()
            except Exception:
                bg_db.rollback()
                if cat or prov or n01 or n02 or n03:
                    prod = _find_by_url(bg_db, url)
                    if prod:
                        prod.origen = prod.origen or "sheet"
                        if cat and prod.categoria != cat: prod.categoria = cat
                        if n01 and prod.n01 != n01: prod.n01 = n01
                        if n02 and prod.n02 != n02: prod.n02 = n02
                        if n03 and prod.n03 != n03: prod.n03 = n03
                        if prov and prod.proveedor != prov: prod.proveedor = prov
                        bg_db.commit()
                continue
            time.sleep(random.uniform(0.5, 1.5))
    finally:
        bg_db.close()

@app.post("/scrape/daily", response_model=ScrapeResponse)
async def scrape_daily(request: Request, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    rate_limit_scrape(request)
    if not SHEET_URL:
        raise HTTPException(status_code=400, detail="SHEET_URL no configurada en .env")
    _validate_sheet_url(SHEET_URL)
    try:
        entries = await read_urls_from_sheet(SHEET_URL)
    except Exception:
        raise HTTPException(status_code=400, detail="Error al leer Google Sheets")
    if not entries:
        raise HTTPException(status_code=400, detail="No se encontraron URLs en la hoja")
    nuevos = actualizados = sin_cambio = fallidos = 0
    for entry in entries:
        url = entry["url"] if isinstance(entry, dict) else entry
        cat = entry.get("categoria") if isinstance(entry, dict) else None
        n01 = entry.get("n01") if isinstance(entry, dict) else None
        n02 = entry.get("n02") if isinstance(entry, dict) else None
        n03 = entry.get("n03") if isinstance(entry, dict) else None
        prov = entry.get("proveedor") if isinstance(entry, dict) else None
        scraper = get_scraper(url)
        if not scraper:
            if cat or prov or n01 or n02 or n03:
                prod = _find_by_url(db, url)
                if prod:
                    prod.origen = prod.origen or "sheet"
                    if cat and prod.categoria != cat: prod.categoria = cat; actualizados += 1
                    if n01 and prod.n01 != n01: prod.n01 = n01
                    if n02 and prod.n02 != n02: prod.n02 = n02
                    if n03 and prod.n03 != n03: prod.n03 = n03
                    if prov and prod.proveedor != prov: prod.proveedor = prov
            fallidos += 1
            continue
        try:
            producto = scraper.scrape()
            resultado = _upsert_producto(db, producto, origen="sheet", categoria=cat, n01=n01, n02=n02, n03=n03, proveedor=prov)
            if resultado == "nuevo":
                nuevos += 1
            elif resultado == "actualizado":
                actualizados += 1
            else:
                sin_cambio += 1
        except Exception:
            db.rollback()
            if cat or prov or n01 or n02 or n03:
                prod = _find_by_url(db, url)
                if prod:
                    prod.origen = prod.origen or "sheet"
                    if cat and prod.categoria != cat: prod.categoria = cat; actualizados += 1
                    if n01 and prod.n01 != n01: prod.n01 = n01
                    if n02 and prod.n02 != n02: prod.n02 = n02
                    if n03 and prod.n03 != n03: prod.n03 = n03
                    if prov and prod.proveedor != prov: prod.proveedor = prov
            fallidos += 1
            continue
        await asyncio.sleep(random.uniform(0.5, 1.5))
    db.commit()
    global _cache_time
    _cache_time = 0  # invalidate cache
    return ScrapeResponse(
        total=len(urls), nuevos=nuevos, actualizados=actualizados,
        sin_cambio=sin_cambio, fallidos=fallidos,
        mensaje=f"Nuevos: {nuevos} | Actualizados: {actualizados} | Sin cambio: {sin_cambio} | Fallidos: {fallidos}",
    )

@app.post("/sync/categories", response_model=SyncResponse)
async def sync_categories(request: Request, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    """Sincroniza SOLO categorias desde Google Sheet sin hacer scrape. Rapido."""
    rate_limit_scrape(request)
    if not SHEET_URL:
        raise HTTPException(status_code=400, detail="SHEET_URL no configurada")
    _validate_sheet_url(SHEET_URL)
    try:
        entries = await read_urls_from_sheet(SHEET_URL)
    except Exception:
        raise HTTPException(status_code=400, detail="Error al leer Google Sheets")
    actualizados = 0
    sin_categoria = 0
    no_encontrados = 0
    urls_no_encontradas = []
    for entry in entries:
        url = entry.get("url", "")
        cat = entry.get("categoria", "")
        n01 = entry.get("n01", "")
        n02 = entry.get("n02", "")
        n03 = entry.get("n03", "")
        prov = entry.get("proveedor", "")
        if not url:
            continue
        if not cat and not prov and not n01 and not n02 and not n03:
            sin_categoria += 1
            continue
        prod = _find_by_url(db, url)
        if prod:
            prod.origen = prod.origen or "sheet"
            if cat and prod.categoria != cat: prod.categoria = cat; actualizados += 1
            if n01 and prod.n01 != n01: prod.n01 = n01
            if n02 and prod.n02 != n02: prod.n02 = n02
            if n03 and prod.n03 != n03: prod.n03 = n03
            if prov and prod.proveedor != prov: prod.proveedor = prov
        else:
            no_encontrados += 1
            urls_no_encontradas.append(url)
    db.commit()
    global _cache_time
    _cache_time = 0
    sin_cambio = len(entries) - actualizados - no_encontrados - sin_categoria
    return SyncResponse(
        total=len(entries), actualizados=actualizados, sin_cambio=sin_cambio,
        no_encontrados=no_encontrados, sin_categoria=sin_categoria,
        urls_no_encontradas=urls_no_encontradas[:20],
        mensaje=f"Actualizados: {actualizados} | No encontrados: {no_encontrados} | Sin categoría en sheet: {sin_categoria}",
    )


# ─── Productos ────────────────────────────────────────────────

@app.get("/productos", response_model=list[ProductoResponse])
def listar_productos(
    tienda: str | None = None,
    skip: int = 0,
    limit: int = 500,
    _user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    global _cache, _cache_time

    if not _plan_activo(_user):
        total = db.query(func.count(Producto.id)).scalar() or 0
        prods = db.query(Producto).filter(
            Producto.n01.isnot(None), Producto.n01 != ""
        ).order_by(Producto.n01, Producto.n02, Producto.n03, Producto.descripcion).all()
        from collections import OrderedDict
        cats = OrderedDict()
        for p in prods:
            cats.setdefault(p.n01, []).append(p)
        result = []
        for items in cats.values():
            result.extend(items[:10])
        data = json.dumps(jsonable_encoder(result))
        response = JSONResponse(content=json.loads(data))
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Free-Tier"] = "1"
        response.headers["X-Free-Cats"] = str(len(cats))
        return response

    now = time.time()
    if (now - _cache_time) < CACHE_TTL and not tienda:
        return JSONResponse(content=json.loads(_cache["data"]), headers={"X-Cache":"HIT","ETag":_cache["etag"]})

    query = db.query(Producto)
    if tienda:
        query = query.filter(Producto.tienda.ilike(f"%{tienda}%"))
    result = query.order_by(Producto.created_at.desc()).offset(skip).limit(limit).all()
    data = json.dumps(jsonable_encoder(result))
    etag = f'W/"prod-{hash(data)}"'
    _cache = {"data": data, "etag": etag}
    _cache_time = now
    return JSONResponse(content=json.loads(data), headers={"X-Cache":"MISS","ETag":etag})

@app.get("/productos/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return prod

@app.put("/productos/{producto_id}/ajustada", response_model=ProductoResponse)
def actualizar_ajustada(producto_id: int, req: UpdateAjustadaRequest, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if req.descripcion_ajustada is not None:
        prod.descripcion_ajustada = req.descripcion_ajustada
    if req.categoria is not None:
        prod.categoria = req.categoria
    if req.n01 is not None:
        prod.n01 = req.n01
    if req.n02 is not None:
        prod.n02 = req.n02
    if req.n03 is not None:
        prod.n03 = req.n03
    if req.proveedor is not None:
        prod.proveedor = req.proveedor
    db.commit()
    db.refresh(prod)
    return prod

@app.get("/scrape/sync", response_model=ProductoResponse)
def scrape_sync(url: str, categoria: str | None = None, n01: str | None = None, n02: str | None = None, n03: str | None = None, proveedor: str | None = None, request: Request = None, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    rate_limit_scrape(request)
    # Validar que la URL sea HTTPS (SSRF prevention)
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("URL debe ser HTTPS")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    scraper = get_scraper(url)
    if not scraper:
        raise HTTPException(status_code=400, detail="URL no soportada")
    try:
        producto = scraper.scrape()
    except Exception:
        raise HTTPException(status_code=500, detail="Error al scrapear URL")
    _upsert_producto(db, producto, origen="sheet", categoria=categoria, n01=n01, n02=n02, n03=n03, proveedor=proveedor)
    db.commit()
    global _cache_time
    _cache_time = 0
    existente = (
        db.query(Producto)
        .filter(Producto.codigo == producto.codigo, Producto.tienda == producto.tienda)
        .first()
    )
    return existente


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


# ─── Pagos Bold ───────────────────────────────────────────────

@app.post("/api/pagos/crear-link", response_model=CrearLinkResponse)
async def crear_link_pago(
    req: CrearLinkRequest,
    request: Request,
    _admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rate_limit_scrape(request)
    usuario = db.query(Usuario).filter(Usuario.id == req.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    reference = f"usr_{req.usuario_id}_{int(time.time())}"
    payload = await bold_client.create_payment_link(
        amount_total=req.amount,
        description=req.description,
        reference=reference,
        payer_email=usuario.email,
        expiration_minutes=req.expiration_minutes,
    )

    pago = Pago(
        usuario_id=req.usuario_id,
        payment_link=payload["payment_link"],
        url=payload["url"],
        reference=reference,
        amount=req.amount,
        status="ACTIVE",
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return CrearLinkResponse(
        id=pago.id,
        payment_link=pago.payment_link,
        url=pago.url,
        reference=pago.reference,
        amount=pago.amount,
        status=pago.status,
    )


@app.get("/api/pagos", response_model=list[PagoResponse])
def listar_pagos(
    usuario_id: int | None = None,
    _admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Pago).order_by(Pago.created_at.desc())
    if usuario_id:
        query = query.filter(Pago.usuario_id == usuario_id)
    return query.limit(200).all()


@app.get("/api/pagos/{pago_id}", response_model=PagoResponse)
def obtener_pago(pago_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago


@app.put("/api/pagos/sync/{pago_id}", response_model=PagoResponse)
async def sync_pago(pago_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    try:
        data = await bold_client.get_payment_link_status(pago.payment_link)
        new_status = data.get("status", pago.status)
        pago.status = new_status
        pago.transaction_id = data.get("transaction_id") or pago.transaction_id
        if new_status == "PAID" and pago.usuario_id:
            usuario = db.query(Usuario).filter(Usuario.id == pago.usuario_id).first()
            if usuario:
                usuario.fecha_pago = func.now()
                ref = pago.reference or ""
                if ref.startswith("basico_"):
                    usuario.plan = "basico"
                elif ref.startswith("upgrade_") or ref.startswith("plus_"):
                    usuario.plan = "plus"
        db.commit()
        db.refresh(pago)
        return pago
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sincronizando: {str(e)}")


@app.delete("/api/pagos/{pago_id}")
def eliminar_pago(pago_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    db.delete(pago)
    db.commit()
    return {"status": "ok"}


@app.post("/api/webhooks/bold")
async def webhook_bold(request: Request, db: Session = Depends(get_db)):
    import hashlib
    import base64

    body = await request.body()
    signature = request.headers.get("x-bold-signature", "")

    body_str = body.decode("utf-8")
    encoded = base64.b64encode(body_str.encode("utf-8"))
    computed = hmac.new(
        key=bold_client.BOLD_SECRET.encode(),
        digestmod=hashlib.sha256,
        msg=encoded,
    ).hexdigest()

    if not hmac.compare_digest(computed, signature):
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
    Base.metadata.create_all(bind=engine)

    if not IS_SQLITE:
        with engine.connect() as conn:
            try:
                conn.execute(text(
                    "DO $$ BEGIN "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='updated_at') THEN "
                    "ALTER TABLE productos ADD COLUMN updated_at TIMESTAMP DEFAULT NOW(); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='valor_anterior') THEN "
                    "ALTER TABLE productos ADD COLUMN valor_anterior FLOAT; "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='origen') THEN "
                    "ALTER TABLE productos ADD COLUMN origen VARCHAR(20); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='categoria') THEN "
                    "ALTER TABLE productos ADD COLUMN categoria VARCHAR(200); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_producto_codigo_tienda') THEN "
                    "ALTER TABLE productos ADD CONSTRAINT uq_producto_codigo_tienda UNIQUE (codigo, tienda); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='insumos' AND column_name='categoria') THEN "
                    "ALTER TABLE insumos ADD COLUMN categoria VARCHAR(200); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='descripcion_ajustada') THEN "
                    "ALTER TABLE productos ADD COLUMN descripcion_ajustada VARCHAR(500); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usuarios' AND column_name='fecha_pago') THEN "
                    "ALTER TABLE usuarios ADD COLUMN fecha_pago TIMESTAMP; "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='proveedor') THEN "
                    "ALTER TABLE productos ADD COLUMN proveedor VARCHAR(200); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='n01') THEN "
                    "ALTER TABLE productos ADD COLUMN n01 VARCHAR(200); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='n02') THEN "
                    "ALTER TABLE productos ADD COLUMN n02 VARCHAR(200); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='n03') THEN "
                    "ALTER TABLE productos ADD COLUMN n03 VARCHAR(200); "
                    "END IF; "
                    "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='usuarios' AND column_name='plan') THEN "
                    "ALTER TABLE usuarios ADD COLUMN plan VARCHAR(10); "
                    "END IF; "
                    "END $$;"
                ))
                conn.commit()
            except Exception:
                conn.rollback()
    else:
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

    global _index_html, _index_mtime
    index_path = static_dir / "index.html"
    if index_path.exists():
        _index_html = index_path.read_text(encoding="utf-8")
        _index_mtime = index_path.stat().st_mtime

    db = SessionLocal()
    try:
        # Migrar usuarios legacy (con fecha_pago pero sin plan) → Plus
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

@app.get("/landing")
def landing_page():
    from fastapi.responses import HTMLResponse
    landing = static_dir / "landing.html"
    if landing.exists():
        return HTMLResponse(content=landing.read_text(encoding="utf-8"))
    return {"error": "landing.html not found"}
