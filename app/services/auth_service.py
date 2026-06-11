"""Servicios de autenticación y autorización."""
import hmac
import os
from datetime import datetime
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Usuario


def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato invalido")
    token = authorization[7:]
    user = db.query(Usuario).filter(Usuario.activo == True, Usuario.token == token).first()
    if user and hmac.compare_digest(token, user.token or ""):
        return user
    raise HTTPException(status_code=401, detail="Token invalido o usuario inactivo")


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
