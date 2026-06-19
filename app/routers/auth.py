"""Router de autenticación y usuarios."""
import os
import time
import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Usuario, Pago, RateLimit
from app.services.auth_service import get_current_user, require_admin, _plan_info, _plan_activo
from app.schemas import (
    LoginRequest, LoginResponse, PlanInfo, ComprarPlanRequest, ComprarPlanResponse,
    UpgradePlanResponse, UsuarioRequest, UsuarioResponse,
)
from app.dependencies import rate_limit_login, rate_limit_scrape
from app import bold as bold_client

logger = logging.getLogger("app")
router = APIRouter()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _check_ip_blocked(ip: str, db: Session):
    now = datetime.utcnow()
    window = now - timedelta(minutes=15)
    total = db.query(func.count(RateLimit.id)).filter(
        RateLimit.key == f"login_fail:{ip}",
        RateLimit.window_start >= window,
    ).scalar() or 0
    if total >= 5:
        raise HTTPException(status_code=429, detail="Demasiados intentos fallidos. Intenta en 15 minutos.")


def _register_fail_ip(ip: str, db: Session):
    entry = RateLimit(key=f"login_fail:{ip}", window_start=datetime.utcnow(), request_count=1)
    db.add(entry)
    db.commit()


def _clear_ip_block(ip: str, db: Session):
    db.query(RateLimit).filter(RateLimit.key == f"login_fail:{ip}").delete()
    db.commit()


TOKEN_DAYS = int(os.getenv("TOKEN_EXPIRE_DAYS", "30"))


@router.post("/register", response_model=LoginResponse)
def register(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit_login(request)
    existente = db.query(Usuario).filter(Usuario.email == req.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="Email ya registrado. Contacta al administrador.")
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
    user = Usuario(
        email=req.email, token=_hash_token(token),
        activo=True, tipo="usuario",
        token_expires_at=expires,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    info = _plan_info(user)
    return LoginResponse(id=user.id, email=user.email, token=token, tipo=user.tipo, plan=info["plan"], fecha_pago=user.fecha_pago, plan_activo=_plan_activo(user))


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    rate_limit_login(request)
    ip = request.client.host if request.client else "unknown"
    _check_ip_blocked(ip, db)
    user = db.query(Usuario).filter(
        Usuario.email == req.email,
        Usuario.activo == True
    ).first()
    if not user:
        _register_fail_ip(ip, db)
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    token_hash = _hash_token(req.token)
    if user.token != token_hash and user.token != req.token:
        _register_fail_ip(ip, db)
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    if user.token != token_hash:
        user.token = token_hash
    user.token_expires_at = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
    db.commit()
    _clear_ip_block(ip, db)
    info = _plan_info(user)
    return LoginResponse(id=user.id, email=user.email, tipo=user.tipo, plan=info["plan"], fecha_pago=user.fecha_pago, plan_activo=_plan_activo(user))


@router.get("/me", response_model=LoginResponse)
def auth_me(user: Usuario = Depends(get_current_user)):
    info = _plan_info(user)
    return LoginResponse(id=user.id, email=user.email, tipo=user.tipo, plan=info["plan"], fecha_pago=user.fecha_pago, plan_activo=_plan_activo(user))


@router.get("/planes", response_model=PlanInfo)
def ver_planes(user: Usuario = Depends(get_current_user)):
    info = _plan_info(user)
    result = {"plan": info["plan"], "activo": info["activo"], "dias_restantes": info["dias_restantes"]}
    if info["plan"] == "free":
        result["puede_upgradear"] = True
        result["upgrade"] = {"basico": 10000, "plus": 15000}
    elif info["plan"] == "basico":
        result["puede_upgradear"] = True
        dias_rest = info["dias_restantes"] or 0
        credito = round((10000 * dias_rest) / 30, 0)
        a_pagar = max(5000, round(15000 - credito, 0))
        result["upgrade"] = {"a_pagar": a_pagar, "credito": credito, "plus_full": 15000, "formula": f"$15.000 - ($10.000 × {dias_rest}/30) = ${a_pagar:,.0f}"}
    else:
        result["puede_upgradear"] = False
    return result


@router.post("/comprar-plan", response_model=ComprarPlanResponse)
async def comprar_plan(
    req: ComprarPlanRequest,
    request: Request,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit_scrape(request)
    info = _plan_info(user)
    if info["plan"] != "free":
        raise HTTPException(status_code=400, detail="Ya tienes un plan activo. Usa /upgrade-plan para mejorar.")
    amounts = {"basico": 10000, "plus": 15000}
    amount = amounts.get(req.plan, 10000)
    desc = {"basico": "Plan Basico - Insumos ilimitados", "plus": "Plan Plus - Acceso completo"}
    reference = f"{req.plan}_usr_{user.id}_{int(time.time())}"
    try:
        payload = await bold_client.create_payment_link(
            amount_total=amount,
            description=desc.get(req.plan, "Plan ListaMasterInsumos"),
            reference=reference,
            payer_email=user.email,
            expiration_minutes=120,
        )
    except Exception as e:
        logger.error(f"[comprar-plan] Error Bold: {e}")
        raise HTTPException(status_code=502, detail=f"Error en pasarela de pago: {str(e)}")
    pago = Pago(
        usuario_id=user.id,
        payment_link=payload["payment_link"],
        url=payload["url"],
        reference=reference,
        amount=amount,
        status="ACTIVE",
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return ComprarPlanResponse(id=pago.id, url=pago.url, amount=pago.amount, status=pago.status)


@router.post("/upgrade-plan", response_model=UpgradePlanResponse)
async def upgrade_plan(
    request: Request,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rate_limit_scrape(request)
    info = _plan_info(user)
    if info["plan"] != "basico":
        raise HTTPException(status_code=400, detail="Solo puedes hacer upgrade desde el plan Basico.")
    dias_rest = info["dias_restantes"] or 0
    if dias_rest <= 0:
        raise HTTPException(status_code=400, detail="Tu plan Basico ya vencio. Compra Plus directamente.")
    credito = round((10000 * dias_rest) / 30, 0)
    amount = max(5000, round(15000 - credito, 0))
    reference = f"upgrade_usr_{user.id}_{int(time.time())}"
    try:
        payload = await bold_client.create_payment_link(
            amount_total=amount,
            description="Upgrade a Plan Plus - Acceso completo",
            reference=reference,
            payer_email=user.email,
            expiration_minutes=120,
        )
    except Exception as e:
        logger.error(f"[upgrade-plan] Error Bold: {e}")
        raise HTTPException(status_code=502, detail=f"Error en pasarela de pago: {str(e)}")
    pago = Pago(
        usuario_id=user.id,
        payment_link=payload["payment_link"],
        url=payload["url"],
        reference=reference,
        amount=amount,
        status="ACTIVE",
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return UpgradePlanResponse(
        id=pago.id, url=pago.url, amount=amount,
        monto_original=15000.0, credito_basico=credito,
        status=pago.status,
    )
