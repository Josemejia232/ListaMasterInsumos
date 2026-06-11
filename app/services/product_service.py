"""Servicios de producto y scraping."""
import re
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Producto
from app.scrapers import get_scraper


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


def _update_category_fields(prod: Producto, categoria: str | None, n01: str | None, n02: str | None, n03: str | None, proveedor: str | None, updated_count: list):
    """Helper para actualizar campos de categoría y contar cambios."""
    prod.origen = prod.origen or "sheet"
    if categoria and prod.categoria != categoria:
        prod.categoria = categoria
        updated_count[0] += 1
    if n01 and prod.n01 != n01:
        prod.n01 = n01
    if n02 and prod.n02 != n02:
        prod.n02 = n02
    if n03 and prod.n03 != n03:
        prod.n03 = n03
    if proveedor and prod.proveedor != proveedor:
        prod.proveedor = proveedor
