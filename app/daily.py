"""Ejecución diaria automática: lee URLs del Google Sheet, scrapea y actualiza solo cambios de precio.

Uso:
    python -m app.daily                  # usa SHEET_URL del .env
    python -m app.daily <sheet_url>      # usa URL personalizada

Programar con cron (Linux/Mac) o Task Scheduler (Windows) para ejecución diaria:
    0 7 * * * cd /ruta/proyecto && python -m app.daily
"""

import sys
import os
import re
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import asyncio
import random
from app.database import SessionLocal
from app.models import Producto
from app.sheets import read_urls_from_sheet
from app.scrapers import get_scraper
from sqlalchemy import func


def upsert_producto(db, producto, origen="sheet", categoria=None, n01=None, n02=None, n03=None, proveedor=None):
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


def _normalize_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip().lower()
    u = re.sub(r"https?://(www\.)?", "https://", u)
    u = u.split("?")[0]
    u = u.rstrip("/")
    return u


def _find_by_url_or_name(db, url: str) -> Producto | None:
    """Busca producto por URL exacta o normalizada."""
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


async def main():
    sheet_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("SHEET_URL", "")
    if not sheet_url:
        print("[ERROR] SHEET_URL no configurada en .env ni pasada como argumento")
        sys.exit(1)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando scrape diario...")
    print(f"  Sheet: {sheet_url}")

    try:
        entries = await read_urls_from_sheet(sheet_url)
        urls_set = set()
        entries_unicas = []
        for e in entries:
            u = e["url"] if isinstance(e, dict) else e
            if u not in urls_set:
                urls_set.add(u)
                entries_unicas.append(e)
        entries = entries_unicas
    except Exception as e:
        print(f"[ERROR] Leyendo Google Sheets: {e}")
        sys.exit(1)

    print(f"  URLs encontradas: {len(entries)} ({len(entries)} únicas)")

    db = SessionLocal()
    nuevos = 0
    actualizados = 0
    sin_cambio = 0
    fallidos = 0

    for i, entry in enumerate(entries, 1):
        url = entry["url"] if isinstance(entry, dict) else entry
        cat = entry.get("categoria") if isinstance(entry, dict) else None
        n01 = entry.get("n01") if isinstance(entry, dict) else None
        n02 = entry.get("n02") if isinstance(entry, dict) else None
        n03 = entry.get("n03") if isinstance(entry, dict) else None
        prov = entry.get("proveedor") if isinstance(entry, dict) else None
        scraper = get_scraper(url)
        if not scraper:
            if cat or prov or n01 or n02 or n03:
                prod = _find_by_url_or_name(db, url)
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
            resultado = upsert_producto(db, producto, origen="sheet", categoria=cat, n01=n01, n02=n02, n03=n03, proveedor=prov)
            if resultado == "nuevo":
                nuevos += 1
                print(f"  [{i}/{len(entries)}] NUEVO: {producto.descripcion[:60]} | ${producto.valor:,.2f}")
            elif resultado == "actualizado":
                actualizados += 1
                print(f"  [{i}/{len(entries)}] ACTUALIZADO: {producto.descripcion[:60]} | ${producto.valor:,.2f}")
            else:
                sin_cambio += 1
        except Exception as e:
            db.rollback()
            if cat or prov or n01 or n02 or n03:
                prod = _find_by_url_or_name(db, url)
                if prod:
                    prod.origen = prod.origen or "sheet"
                    if cat and prod.categoria != cat: prod.categoria = cat; actualizados += 1
                    if n01 and prod.n01 != n01: prod.n01 = n01
                    if n02 and prod.n02 != n02: prod.n02 = n02
                    if n03 and prod.n03 != n03: prod.n03 = n03
                    if prov and prod.proveedor != prov: prod.proveedor = prov
            fallidos += 1
            print(f"  [{i}/{len(entries)}] FALLIDO: {url[:80]} — {e}")
            continue
        await asyncio.sleep(random.uniform(0.5, 1.5))

    db.commit()
    db.close()

    print()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Resumen diario:")
    print(f"  Total URLs    : {len(entries)}")
    print(f"  Nuevos        : {nuevos}")
    print(f"  Actualizados  : {actualizados}")
    print(f"  Sin cambio    : {sin_cambio}")
    print(f"  Fallidos      : {fallidos}")
    print("  Listo.")


if __name__ == "__main__":
    asyncio.run(main())
