"""Sesiones con cookies firmadas (HTTP-only, sin dependencias externas)."""
import os
import json
import base64
import hmac
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from fastapi import Response

logger = logging.getLogger("app")

SESSION_COOKIE = "session"
SESSION_DAYS = 7


def _get_secret() -> bytes:
    secret = os.getenv("ADMIN_TOKEN", "")
    if not secret:
        secret = secrets.token_hex(32)
    return secret.encode()


def crear_cookie(user_id: int, response: Response):
    """Crea una cookie firmada con user_id y expiry, y la setea en la response."""
    exp = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).timestamp()
    payload = json.dumps({"uid": user_id, "exp": exp})
    b64 = base64.urlsafe_b64encode(payload.encode()).rstrip(b"=").decode()
    sig = hmac.new(_get_secret(), b64.encode(), hashlib.sha256).hexdigest()
    token = f"{b64}.{sig}"
    secure = os.getenv("FORCE_HTTPS", "true").lower() in ("true", "1", "yes")
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def eliminar_cookie(response: Response):
    """Elimina la cookie de sesión."""
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
    )


def leer_cookie(token: str | None) -> dict | None:
    """Verifica y decodifica una cookie firmada. Retorna dict con 'uid' o None."""
    if not token or "." not in token:
        return None
    b64, sig = token.rsplit(".", 1)
    expected = hmac.new(_get_secret(), b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        padded = b64 + "=" * (4 - len(b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None
    exp = payload.get("exp", 0)
    if datetime.now(timezone.utc).timestamp() > exp:
        return None
    return payload
