import asyncio
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import engine, get_db, Base
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

    background_tasks.add_task(procesar_urls, urls, db)
    return ScrapeResponse(
        total=len(urls),
        exitosos=0,
        fallidos=0,
        mensaje=f"Procesando {len(urls)} URLs en segundo plano",
    )


def procesar_urls(urls: list[str], db: Session):
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
            db.add(db_item)
            db.commit()
        except Exception:
            db.rollback()
            continue


@app.get("/productos")
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


@app.get("/productos/{producto_id}")
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return prod


@app.get("/scrape/sync")
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
    return db_item


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
