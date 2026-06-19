"""Router de administración de usuarios."""
import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Usuario
from app.services.auth_service import require_admin
from app.schemas import UsuarioResponse, UsuarioRequest


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


router = APIRouter()

@router.get("", response_model=list[UsuarioResponse])
def listar_usuarios(_admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(Usuario).order_by(Usuario.email).all()

@router.post("", response_model=UsuarioResponse)
def crear_usuario(req: UsuarioRequest, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == req.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    if not req.token:
        req.token = secrets.token_hex(32)
    item = Usuario(email=req.email, token=_hash_token(req.token), activo=req.activo, tipo=req.tipo)
    db.add(item)
    db.commit()
    db.refresh(item)
    return UsuarioResponse(id=item.id, email=item.email, token=item.token, activo=item.activo, tipo=item.tipo, fecha_pago=item.fecha_pago, created_at=item.created_at)

@router.put("/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(usuario_id: int, req: UsuarioRequest, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if req.email:
        item.email = req.email
    if req.token:
        item.token = _hash_token(req.token)
    item.activo = req.activo
    item.tipo = req.tipo
    db.commit()
    db.refresh(item)
    return UsuarioResponse(id=item.id, email=item.email, token=item.token, activo=item.activo, tipo=item.tipo, fecha_pago=item.fecha_pago, created_at=item.created_at)

@router.delete("/{usuario_id}")
def eliminar_usuario(usuario_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}

@router.post("/{usuario_id}/pago", response_model=UsuarioResponse)
def renovar_pago(usuario_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    item.fecha_pago = func.now()
    db.commit()
    db.refresh(item)
    return UsuarioResponse(id=item.id, email=item.email, token=item.token, activo=item.activo, tipo=item.tipo, fecha_pago=item.fecha_pago, created_at=item.created_at)

@router.post("/{usuario_id}/reset-token")
def resetear_token(usuario_id: int, _admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    raw = secrets.token_hex(32)
    item.token = _hash_token(raw)
    db.commit()
    return {"ok": True, "message": "Token reseteado. El usuario debe iniciar sesion nuevamente."}
