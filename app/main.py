import asyncio
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import engine, get_db, SessionLocal, Base
from app.models import Producto
from app.sheets import read_urls_from_sheet
from app.scrapers import get_scraper

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ListaMasterInsumos",
    description="API para scrapeo de insumos de construcción desde Google Sheets",
)


class ScrapeRequest(BaseModel):
    sheet_url: str


class ScrapeResponse(BaseModel):
    total: int
    exitosos: int
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

    model_config = {"from_attributes": True}


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
        exitosos=0,
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
                db_item = Producto(
                    codigo=producto.codigo,
                    descripcion=producto.descripcion,
                    unidad=producto.unidad,
                    valor=producto.valor,
                    tienda=producto.tienda,
                    url_origen=producto.url,
                )
                bg_db.add(db_item)
                bg_db.commit()
            except Exception:
                bg_db.rollback()
                continue
    finally:
        bg_db.close()


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
    db_item = Producto(
        codigo=producto.codigo,
        descripcion=producto.descripcion,
        unidad=producto.unidad,
        valor=producto.valor,
        tienda=producto.tienda,
        url_origen=producto.url,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/scrape/forward")
def scrape_forward(url: str, db: Session = Depends(get_db)):
    scraper = get_scraper(url)
    if not scraper:
        raise HTTPException(status_code=400, detail="URL no soportada")
    try:
        producto = scraper.scrape()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    db_item = Producto(
        codigo=producto.codigo,
        descripcion=producto.descripcion,
        unidad=producto.unidad,
        valor=producto.valor,
        tienda=producto.tienda,
        url_origen=producto.url,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return {
        "id": db_item.id,
        "codigo": db_item.codigo,
        "descripcion": db_item.descripcion,
        "unidad": db_item.unidad,
        "valor": db_item.valor,
        "tienda": db_item.tienda,
        "url_origen": db_item.url_origen,
        "created_at": str(db_item.created_at or ""),
    }


@app.get("/")
def root():
    return {
        "app": "ListaMasterInsumos",
        "endpoints": {
            "POST /scrape": "Enviar URL de Google Sheets para scrapear",
            "GET /scrape/sync?url=...": "Scrapear una URL individual",
            "GET /productos": "Listar productos scrapeados",
            "GET /productos/{id}": "Detalle de un producto",
        },
    }
