"""Servicios de autenticación y autorización."""
import hashlib
import hmac
import os
from datetime import datetime, timezone
from fastapi import Header, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario
from app.services.session_service import leer_cookie


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _token_valido(user: Usuario) -> bool:
    if user.tipo == "admin":
        return True
    if user.token_expires_at is None:
        return True
    exp = user.token_expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < exp


def get_current_user(request: Request, authorization: str = Header(None), db: Session = Depends(get_db)):
    # 1. Intentar con cookie de sesión
    if request:
        cookie = request.cookies.get("session")
        if cookie:
            payload = leer_cookie(cookie)
            if payload:
                user = db.query(Usuario).filter(
                    Usuario.id == payload["uid"],
                    Usuario.activo == True
                ).first()
                if user and _token_valido(user):
                    return user
    # 2. Fallback: Bearer token (para API/programático)
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Formato invalido")
        token = authorization[7:]
        token_hash = _hash_token(token)
        user = db.query(Usuario).filter(Usuario.activo == True, Usuario.token == token_hash).first()
        if user:
            if _token_valido(user):
                return user
            raise HTTPException(status_code=401, detail="Token expirado. Inicia sesion nuevamente.")
        user = db.query(Usuario).filter(Usuario.activo == True, Usuario.token == token).first()
        if user:
            user.token = token_hash
            db.commit()
            if _token_valido(user):
                return user
            raise HTTPException(status_code=401, detail="Token expirado. Inicia sesion nuevamente.")
    raise HTTPException(status_code=401, detail="No autenticado")


def require_admin(user: Usuario = Depends(get_current_user)):
    if user.tipo != "admin":
        raise HTTPException(status_code=403, detail="Se requiere permisos de admin")
    return user


def _plan_info(user: Usuario) -> dict:
    if user.tipo == "admin":
        return {"plan": "plus", "activo": True, "dias_restantes": 9999}
    if not user.fecha_pago:
        return {"plan": "free", "activo": True, "dias_restantes": None}
    delta = (datetime.utcnow() - user.fecha_pago).days
    if delta >= 30:
        return {"plan": "free", "activo": True, "dias_restantes": None}
    plan = user.plan or "plus"
    return {"plan": plan, "activo": True, "dias_restantes": 30 - delta}


def _plan_activo(user: Usuario) -> bool:
    if user.tipo == "admin":
        return True
    if not user.fecha_pago:
        return False
    delta = datetime.utcnow() - user.fecha_pago
    return delta.days < 30
