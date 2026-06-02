import asyncio
import os
import json
import time
import random
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Header, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from dotenv import load_dotenv

from app.database import engine, get_db, SessionLocal, Base
from app.models import Producto, Insumo, Usuario
from app.sheets import read_urls_from_sheet
from app.scrapers import get_scraper

load_dotenv()
Base.metadata.create_all(bind=engine)

# Migraciones
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
            "END $$;"
        ))
        conn.commit()
    except Exception:
        conn.rollback()

app = FastAPI(
    title="ListaMasterInsumos",
    description="API para scrapeo de insumos de construcción desde Google Sheets",
)

app.add_middleware(GZipMiddleware, minimum_size=500)

# Simple in-memory cache
_cache = {}
_cache_time = 0
CACHE_TTL = 10  # seconds

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

SHEET_URL = os.getenv("SHEET_URL", "")


# ─── Schemas ──────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    sheet_url: str

class ScrapeResponse(BaseModel):
    total: int
    nuevos: int
    actualizados: int
    sin_cambio: int
    fallidos: int
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
    tienda: str
    url_origen: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}

class InsumoRequest(BaseModel):
    descripcion: str
    un: str = "Unidad"
    valor: float = 0.0

class InsumoResponse(InsumoRequest):
    id: int
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

class LoginRequest(BaseModel):
    email: str
    token: str

class LoginResponse(BaseModel):
    id: int
    email: str
    tipo: str
    token: str = ""

class UpdateAjustadaRequest(BaseModel):
    descripcion_ajustada: str | None = None

class UsuarioRequest(BaseModel):
    email: str
    token: str = ""
    activo: bool = True
    tipo: str = "usuario"

class UsuarioResponse(BaseModel):
    id: int
    email: str
    token: str
    activo: bool
    tipo: str
    fecha_pago: datetime | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ─── Auth ─────────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato inválido")
    token = authorization[7:]
    user = db.query(Usuario).filter(Usuario.token == token, Usuario.activo == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Token inválido o usuario inactivo")
    return user

def require_admin(user: Usuario = Depends(get_current_user)):
    if user.tipo != "admin":
        raise HTTPException(status_code=403, detail="Se requiere permisos de admin")
    return user


# ─── Upsert ───────────────────────────────────────────────────

def _upsert_producto(db: Session, producto, origen: str = "manual", categoria: str | None = None) -> dict:
    if not producto.codigo:
        return "sin_cambio"
    existente = (
        db.query(Producto)
        .filter(Producto.codigo == producto.codigo, Producto.tienda == producto.tienda)
        .first()
    )
    if existente:
        if categoria and existente.categoria != categoria:
            existente.categoria = categoria
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
        )
        db.add(db_item)
        return "nuevo"


# ─── Auth endpoints ───────────────────────────────────────────

@app.post("/api/auth/register", response_model=LoginResponse)
def register(req: LoginRequest, db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == req.email).first()
    if existente:
        return LoginResponse(id=existente.id, email=existente.email, tipo=existente.tipo, token=existente.token)
    import secrets
    token = secrets.token_hex(16)
    user = Usuario(email=req.email, token=token, activo=True, tipo="usuario")
    db.add(user)
    db.commit()
    db.refresh(user)
    return LoginResponse(id=user.id, email=user.email, tipo=user.tipo, token=user.token)

@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(
        Usuario.email == req.email,
        Usuario.token == req.token,
        Usuario.activo == True
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return LoginResponse(id=user.id, email=user.email, tipo=user.tipo, token=user.token)

@app.get("/api/auth/me", response_model=LoginResponse)
def auth_me(user: Usuario = Depends(get_current_user)):
    return LoginResponse(id=user.id, email=user.email, tipo=user.tipo, token=user.token)

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
        req.token = secrets.token_hex(16)
    item = Usuario(email=req.email, token=req.token, activo=req.activo, tipo=req.tipo)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

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
    return item

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
    return item


# ─── Scraping ─────────────────────────────────────────────────

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_from_sheet(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        urls = await read_urls_from_sheet(req.sheet_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer Google Sheets: {e}")
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
            scraper = get_scraper(url)
            if not scraper:
                continue
            try:
                producto = scraper.scrape()
                cat = entry.get("categoria") if isinstance(entry, dict) else None
                _upsert_producto(bg_db, producto, origen="sheet", categoria=cat)
                bg_db.commit()
            except Exception:
                bg_db.rollback()
                continue
            time.sleep(random.uniform(1.0, 2.5))
    finally:
        bg_db.close()

@app.get("/scrape/daily", response_model=ScrapeResponse)
async def scrape_daily(db: Session = Depends(get_db)):
    if not SHEET_URL:
        raise HTTPException(status_code=400, detail="SHEET_URL no configurada en .env")
    try:
        entries = await read_urls_from_sheet(SHEET_URL)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer Google Sheets: {e}")
    if not entries:
        raise HTTPException(status_code=400, detail="No se encontraron URLs en la hoja")
    nuevos = actualizados = sin_cambio = fallidos = 0
    for entry in entries:
        url = entry["url"] if isinstance(entry, dict) else entry
        scraper = get_scraper(url)
        if not scraper:
            fallidos += 1
            continue
        try:
            producto = scraper.scrape()
            cat = entry.get("categoria") if isinstance(entry, dict) else None
            resultado = _upsert_producto(db, producto, origen="sheet", categoria=cat)
            if resultado == "nuevo":
                nuevos += 1
            elif resultado == "actualizado":
                actualizados += 1
            else:
                sin_cambio += 1
        except Exception:
            db.rollback()
            fallidos += 1
            continue
        await asyncio.sleep(random.uniform(1.0, 2.5))
    db.commit()
    global _cache_time
    _cache_time = 0  # invalidate cache
    return ScrapeResponse(
        total=len(urls), nuevos=nuevos, actualizados=actualizados,
        sin_cambio=sin_cambio, fallidos=fallidos,
        mensaje=f"Nuevos: {nuevos} | Actualizados: {actualizados} | Sin cambio: {sin_cambio} | Fallidos: {fallidos}",
    )


# ─── Productos ────────────────────────────────────────────────

@app.get("/productos", response_model=list[ProductoResponse])
def listar_productos(
    tienda: str | None = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    global _cache, _cache_time
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
    prod.descripcion_ajustada = req.descripcion_ajustada
    db.commit()
    db.refresh(prod)
    return prod

@app.get("/scrape/sync", response_model=ProductoResponse)
def scrape_sync(url: str, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    scraper = get_scraper(url)
    if not scraper:
        raise HTTPException(status_code=400, detail="URL no soportada")
    try:
        producto = scraper.scrape()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    _upsert_producto(db, producto)
    db.commit()
    existente = (
        db.query(Producto)
        .filter(Producto.codigo == producto.codigo, Producto.tienda == producto.tienda)
        .first()
    )
    return existente


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


# ─── Insumos CRUD (legacy) ────────────────────────────────────

@app.get("/api/insumos", response_model=list[InsumoResponse])
def listar_insumos(db: Session = Depends(get_db)):
    return db.query(Insumo).order_by(Insumo.descripcion).all()

@app.post("/api/insumos", response_model=InsumoResponse)
def crear_insumo(req: InsumoRequest, db: Session = Depends(get_db)):
    item = Insumo(descripcion=req.descripcion, un=req.un, valor=req.valor)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.put("/api/insumos/{insumo_id}", response_model=InsumoResponse)
def actualizar_insumo(insumo_id: int, req: InsumoRequest, db: Session = Depends(get_db)):
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
def eliminar_insumo(insumo_id: int, db: Session = Depends(get_db)):
    item = db.query(Insumo).filter(Insumo.id == insumo_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Insumo no encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── Root ─────────────────────────────────────────────────────

@app.get("/favicon.ico")
def favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

@app.get("/")
def root():
    index = static_dir / "index.html"
    if index.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(index))
    return {"app": "ListaMasterInsumos", "status": "ok"}


# ─── Seed admin ───────────────────────────────────────────────

@app.on_event("startup")
def seed_admin():
    db = SessionLocal()
    try:
        admin = db.query(Usuario).filter(Usuario.tipo == "admin").first()
        if not admin:
            admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
            admin_token = os.getenv("ADMIN_TOKEN", "admin123")
            db.add(Usuario(email=admin_email, token=admin_token, activo=True, tipo="admin"))
            db.commit()
            print(f"Admin creado: {admin_email} / token: {admin_token}")
    except Exception as e:
        db.rollback()
        print(f"Seed admin skipped: {e}")
    finally:
        db.close()
