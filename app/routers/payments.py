"""Router de pagos y webhooks."""
import os
import time
import logging
import hashlib
import base64
import hmac as hmac_lib
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Usuario, Pago
from app.services.auth_service import require_admin
from app.schemas import CrearLinkRequest, CrearLinkResponse, PagoResponse
from app.dependencies import rate_limit_scrape
from app import bold as bold_client

logger = logging.getLogger("app")
router = APIRouter()

BOLD_WEBHOOK_IPS = os.getenv("BOLD_WEBHOOK_IPS", "").split(",")
BOLD_WEBHOOK_IPS = [ip.strip() for ip in BOLD_WEBHOOK_IPS if ip.strip()]

@router.post("/crear-link", response_model=CrearLinkResponse)
async def crear_link_pago(
    req: CrearLinkRequest,
    request: Request,
    _admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rate_limit_scrape(request)
    usuario = db.query(Usuario).filter(Usuario.id == req.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    reference = f"usr_{req.usuario_id}_{int(time.time())}"
    try:
        payload = await bold_client.create_payment_link(
            amount_total=req.amount,
            description=req.description,
            reference=reference,
            payer_email=usuario.email,
            expiration_minutes=req.expiration_minutes,
        )
    except Exception as e:
        logger.error(f"[crear-link] Error Bold: {e}")
        raise HTTPException(status_code=502, detail=f"Error en pasarela de pago: {str(e)}")

    pago = Pago(
        usuario_id=req.usuario_id,
        payment_link=payload["payment_link"],
        url=payload["url"],
        reference=reference,
        amount=req.amount,
        status="ACTIVE",
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)
    return CrearLinkResponse(
        id=pago.id,
        payment_link=pago.payment_link,
        url=pago.url,
        reference=pago.reference,
        amount=pago.amount,
        status=pago.status,
    )

@router.get("", response_model=list[PagoResponse])
def listar_pagos(
    usuario_id: int | None = None,
    _admin = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Pago).order_by(Pago.created_at.desc())
    if usuario_id:
        query = query.filter(Pago.usuario_id == usuario_id)
    return query.limit(200).all()

@router.get("/{pago_id}", response_model=PagoResponse)
def obtener_pago(pago_id: int, _admin = Depends(require_admin), db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago

@router.put("/sync/{pago_id}", response_model=PagoResponse)
async def sync_pago(pago_id: int, _admin = Depends(require_admin), db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    try:
        data = await bold_client.get_payment_link_status(pago.payment_link)
        new_status = data.get("status", pago.status)
        pago.status = new_status
        pago.transaction_id = data.get("transaction_id") or pago.transaction_id
        if new_status == "PAID" and pago.usuario_id:
            usuario = db.query(Usuario).filter(Usuario.id == pago.usuario_id).first()
            if usuario:
                usuario.fecha_pago = func.now()
                ref = pago.reference or ""
                if ref.startswith("basico_"):
                    usuario.plan = "basico"
                elif ref.startswith("upgrade_") or ref.startswith("plus_"):
                    usuario.plan = "plus"
        db.commit()
        db.refresh(pago)
        return pago
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sincronizando: {str(e)}")

@router.delete("/{pago_id}")
def eliminar_pago(pago_id: int, _admin = Depends(require_admin), db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    db.delete(pago)
    db.commit()
    return {"status": "ok"}


