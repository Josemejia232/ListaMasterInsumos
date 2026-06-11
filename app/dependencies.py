"""Dependencias compartidas: rate limiting, cache, validaciones."""
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RateLimit, CacheEntry

RATE_LIMIT_WINDOW = 60  # seconds
CACHE_TTL = 10  # seconds

SHEET_URL = os.getenv("SHEET_URL", "")

ALLOWED_SHEET_DOMAINS = ["docs.google.com", "sheets.google.com"]
ALLOWED_SCRAPE_DOMAINS = [
    "easy.com", "easy.com.co", "easy.com.ar",
    "homecenter.com.co", "homecenter.com.pe",
    "maestro.com.pe",
    "promart.pe",
    "sodimac.com.pe", "sodimac.com.co", "sodimac.com.cl",
    "falabella.com.pe", "falabella.com.cl",
]

# ─── Rate Limiting ───────────────────────────────────────────
def _check_rate_limit_db(key: str, max_requests: int, db: Session) -> bool:
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    db.query(RateLimit).filter(RateLimit.window_start < window_start).delete(synchronize_session=False)
    db.commit()
    entry = db.query(RateLimit).filter(RateLimit.key == key, RateLimit.window_start >= window_start).first()
    if not entry:
        entry = RateLimit(key=key, window_start=now, request_count=1)
        db.add(entry)
        db.commit()
        return True
    if entry.request_count >= max_requests:
        return False
    entry.request_count += 1
    db.commit()
    return True

def rate_limit_login(request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit_db(f"login:{ip}", 10, db):
        raise HTTPException(status_code=429, detail="Demasiados intentos. Intenta en 1 minuto.")

def rate_limit_scrape(request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit_db(f"scrape:{ip}", 5, db):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones de scrape. Intenta en 1 minuto.")

# ─── Cache ───────────────────────────────────────────────────
def _get_cache(key: str, db: Session) -> str | None:
    now = datetime.utcnow()
    entry = db.query(CacheEntry).filter(CacheEntry.key == key, CacheEntry.expires_at > now).first()
    return entry.value if entry else None

def _set_cache(key: str, value: str, db: Session):
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=CACHE_TTL)
    entry = db.query(CacheEntry).filter(CacheEntry.key == key).first()
    if entry:
        entry.value = value
        entry.expires_at = expires_at
    else:
        entry = CacheEntry(key=key, value=value, expires_at=expires_at)
        db.add(entry)
    db.commit()

def _invalidate_cache(key: str, db: Session):
    db.query(CacheEntry).filter(CacheEntry.key == key).delete(synchronize_session=False)
    db.commit()

# ─── URL Validation ──────────────────────────────────────────
def _validate_domain(url: str, allowed_domains: list[str]):
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("URL debe ser HTTPS")
        hostname = parsed.hostname or ""
        allowed = any(hostname == d or hostname.endswith("." + d) for d in allowed_domains)
        if not allowed:
            raise ValueError(f"Dominio no permitido: {parsed.hostname}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def _validate_sheet_url(url: str):
    _validate_domain(url, ALLOWED_SHEET_DOMAINS)

def _validate_scrape_url(url: str):
    _validate_domain(url, ALLOWED_SCRAPE_DOMAINS)
