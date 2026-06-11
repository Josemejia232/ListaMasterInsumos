"""Router de scraping."""
import asyncio
import time
import random
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import Producto
from app.services.auth_service import require_admin
from app.services.product_service import _find_by_url, _upsert_producto
from app.sheets import read_urls_from_sheet
from app.scrapers import get_scraper
from app.schemas import ScrapeResponse, SyncResponse, ProductoResponse, ScrapeRequest
from app.dependencies import rate_limit_scrape, _validate_sheet_url, _validate_scrape_url, _invalidate_cache, SHEET_URL

router = APIRouter()

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

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_from_sheet(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    _admin = Depends(require_admin),
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

@router.post("/scrape/daily", response_model=ScrapeResponse)
async def scrape_daily(request: Request, _admin = Depends(require_admin), db: Session = Depends(get_db)):
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
    _invalidate_cache("productos", db)
    return ScrapeResponse(
        total=len(entries), nuevos=nuevos, actualizados=actualizados,
        sin_cambio=sin_cambio, fallidos=fallidos,
        mensaje=f"Nuevos: {nuevos} | Actualizados: {actualizados} | Sin cambio: {sin_cambio} | Fallidos: {fallidos}",
    )

@router.post("/sync/categories", response_model=SyncResponse)
async def sync_categories(request: Request, _admin = Depends(require_admin), db: Session = Depends(get_db)):
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
    _invalidate_cache("productos", db)
    sin_cambio = len(entries) - actualizados - no_encontrados - sin_categoria
    return SyncResponse(
        total=len(entries), actualizados=actualizados, sin_cambio=sin_cambio,
        no_encontrados=no_encontrados, sin_categoria=sin_categoria,
        urls_no_encontradas=urls_no_encontradas[:20],
        mensaje=f"Actualizados: {actualizados} | No encontrados: {no_encontrados} | Sin categoría en sheet: {sin_categoria}",
    )

@router.get("/scrape/sync", response_model=ProductoResponse)
def scrape_sync(url: str, categoria: str | None = None, n01: str | None = None, n02: str | None = None, n03: str | None = None, proveedor: str | None = None, request: Request = None, _admin = Depends(require_admin), db: Session = Depends(get_db)):
    rate_limit_scrape(request)
    _validate_scrape_url(url)
    scraper = get_scraper(url)
    if not scraper:
        raise HTTPException(status_code=400, detail="URL no soportada")
    try:
        producto = scraper.scrape()
    except Exception:
        raise HTTPException(status_code=500, detail="Error al scrapear URL")
    _upsert_producto(db, producto, origen="sheet", categoria=categoria, n01=n01, n02=n02, n03=n03, proveedor=proveedor)
    db.commit()
    _invalidate_cache("productos", db)
    existente = (
        db.query(Producto)
        .filter(Producto.codigo == producto.codigo, Producto.tienda == producto.tienda)
        .first()
    )
    return existente
