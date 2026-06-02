"""Ejecución diaria automática: lee URLs del Google Sheet, scrapea y actualiza solo cambios de precio.

Uso:
    python -m app.daily                  # usa SHEET_URL del .env
    python -m app.daily <sheet_url>      # usa URL personalizada

Programar con cron (Linux/Mac) o Task Scheduler (Windows) para ejecución diaria:
    0 7 * * * cd /ruta/proyecto && python -m app.daily
"""

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import asyncio
from app.database import SessionLocal
from app.models import Producto
from app.sheets import read_urls_from_sheet
from app.scrapers import get_scraper
from sqlalchemy import func


def upsert_producto(db, producto):
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


async def main():
    sheet_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("SHEET_URL", "")
    if not sheet_url:
        print("[ERROR] SHEET_URL no configurada en .env ni pasada como argumento")
        sys.exit(1)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando scrape diario...")
    print(f"  Sheet: {sheet_url}")

    try:
        urls = await read_urls_from_sheet(sheet_url)
        urls = list(dict.fromkeys(urls))
    except Exception as e:
        print(f"[ERROR] Leyendo Google Sheets: {e}")
        sys.exit(1)

    print(f"  URLs encontradas: {len(urls)} ({len(urls)} únicas)")

    db = SessionLocal()
    nuevos = 0
    actualizados = 0
    sin_cambio = 0
    fallidos = 0

    for i, url in enumerate(urls, 1):
        scraper = get_scraper(url)
        if not scraper:
            fallidos += 1
            continue
        try:
            producto = scraper.scrape()
            resultado = upsert_producto(db, producto)
            if resultado == "nuevo":
                nuevos += 1
                print(f"  [{i}/{len(urls)}] NUEVO: {producto.descripcion[:60]} | ${producto.valor:,.2f}")
            elif resultado == "actualizado":
                actualizados += 1
                print(f"  [{i}/{len(urls)}] ACTUALIZADO: {producto.descripcion[:60]} | ${producto.valor:,.2f}")
            else:
                sin_cambio += 1
        except Exception as e:
            db.rollback()
            fallidos += 1
            print(f"  [{i}/{len(urls)}] FALLIDO: {url[:80]} — {e}")
            continue

    db.commit()
    db.close()

    print()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Resumen diario:")
    print(f"  Total URLs    : {len(urls)}")
    print(f"  Nuevos        : {nuevos}")
    print(f"  Actualizados  : {actualizados}")
    print(f"  Sin cambio    : {sin_cambio}")
    print(f"  Fallidos      : {fallidos}")
    print("  Listo.")


if __name__ == "__main__":
    asyncio.run(main())
