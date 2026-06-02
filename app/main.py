import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from dotenv import load_dotenv

from app.database import engine, get_db, SessionLocal, Base
from app.models import Producto, Insumo
from app.sheets import read_urls_from_sheet
from app.scrapers import get_scraper

load_dotenv()
Base.metadata.create_all(bind=engine)

# Migración: agregar updated_at y constraint UNIQUE en tablas existentes
with engine.connect() as conn:
    try:
        conn.execute(text(
            "DO $$ BEGIN "
            "IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='productos' AND column_name='updated_at') THEN "
            "ALTER TABLE productos ADD COLUMN updated_at TIMESTAMP DEFAULT NOW(); "
            "END IF; "
            "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='uq_producto_codigo_tienda') THEN "
            "ALTER TABLE productos ADD CONSTRAINT uq_producto_codigo_tienda UNIQUE (codigo, tienda); "
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

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

SHEET_URL = os.getenv("SHEET_URL", "")


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
    unidad: str
    valor: float
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


def _upsert_producto(db: Session, producto) -> dict:
    """Inserta o actualiza según cambio de precio. Retorna: 'nuevo', 'actualizado', 'sin_cambio'"""
    if not producto.codigo:
        return "sin_cambio"

    existente = (
        db.query(Producto)
        .filter(Producto.codigo == producto.codigo, Producto.tienda == producto.tienda)
        .first()
    )

    if existente:
        if abs(existente.valor - producto.valor) < 0.01:
            return "sin_cambio"
        existente.descripcion = producto.descripcion
        existente.unidad = producto.unidad
        existente.valor = producto.valor
        existente.url_origen = producto.url
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
        )
        db.add(db_item)
        return "nuevo"


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
        total=len(urls),
        nuevos=0,
        actualizados=0,
        sin_cambio=0,
        fallidos=0,
        mensaje=f"Procesando {len(urls)} URLs en segundo plano",
    )


def _procesar_urls_bg(urls: list[str]):
    bg_db = SessionLocal()
    try:
        for url in urls:
            scraper = get_scraper(url)
            if not scraper:
                continue
            try:
                producto = scraper.scrape()
                _upsert_producto(bg_db, producto)
                bg_db.commit()
            except Exception:
                bg_db.rollback()
                continue
    finally:
        bg_db.close()


@app.get("/scrape/daily", response_model=ScrapeResponse)
async def scrape_daily(db: Session = Depends(get_db)):
    """Ejecución diaria automática: lee URLs del Sheet configurado y actualiza solo cambios de precio."""
    if not SHEET_URL:
        raise HTTPException(status_code=400, detail="SHEET_URL no configurada en .env")

    try:
        urls = await read_urls_from_sheet(SHEET_URL)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer Google Sheets: {e}")

    if not urls:
        raise HTTPException(status_code=400, detail="No se encontraron URLs en la hoja")

    nuevos = 0
    actualizados = 0
    sin_cambio = 0
    fallidos = 0

    for url in urls:
        scraper = get_scraper(url)
        if not scraper:
            fallidos += 1
            continue
        try:
            producto = scraper.scrape()
            resultado = _upsert_producto(db, producto)
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

    db.commit()
    return ScrapeResponse(
        total=len(urls),
        nuevos=nuevos,
        actualizados=actualizados,
        sin_cambio=sin_cambio,
        fallidos=fallidos,
        mensaje=f"Nuevos: {nuevos} | Actualizados: {actualizados} | Sin cambio: {sin_cambio} | Fallidos: {fallidos}",
    )


@app.get("/productos", response_model=list[ProductoResponse])
def listar_productos(
    tienda: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Producto)
    if tienda:
        query = query.filter(Producto.tienda.ilike(f"%{tienda}%"))
    return query.order_by(Producto.created_at.desc()).offset(skip).limit(limit).all()


@app.get("/productos/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return prod


@app.get("/scrape/sync", response_model=ProductoResponse)
def scrape_sync(url: str, db: Session = Depends(get_db)):
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


@app.get("/scrape/forward")
def scrape_forward(url: str, db: Session = Depends(get_db)):
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
    return {
        "id": existente.id,
        "codigo": existente.codigo,
        "descripcion": existente.descripcion,
        "unidad": existente.unidad,
        "valor": existente.valor,
        "tienda": existente.tienda,
        "url_origen": existente.url_origen,
        "created_at": str(existente.created_at or ""),
        "updated_at": str(existente.updated_at or ""),
    }


# ─── Insumos CRUD ─────────────────────────────────────────────

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


@app.get("/")
def root():
    index = static_dir / "index.html"
    if index.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(index))
    return {"app": "ListaMasterInsumos", "status": "ok"}
