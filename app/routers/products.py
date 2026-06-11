"""Router de productos."""
import json
from collections import OrderedDict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.database import get_db
from app.models import Producto
from app.services.auth_service import get_current_user, require_admin
from app.schemas import ProductoResponse, UpdateAjustadaRequest
from app.dependencies import _get_cache, _set_cache, _invalidate_cache
from app.services.auth_service import _plan_activo

router = APIRouter()

@router.get("", response_model=list[ProductoResponse])
def listar_productos(
    tienda: str | None = None,
    skip: int = 0,
    limit: int = 500,
    _user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _plan_activo(_user):
        total = db.query(func.count(Producto.id)).scalar() or 0
        prods = db.query(Producto).filter(
            Producto.n01.isnot(None), Producto.n01 != ""
        ).order_by(Producto.n01, Producto.n02, Producto.n03, Producto.descripcion).all()
        cats = OrderedDict()
        for p in prods:
            cats.setdefault(p.n01, []).append(p)
        result = []
        for items in cats.values():
            result.extend(items[:10])
        data = json.dumps(jsonable_encoder(result))
        response = JSONResponse(content=json.loads(data))
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Free-Tier"] = "1"
        response.headers["X-Free-Cats"] = str(len(cats))
        return response

    cached = _get_cache("productos", db) if not tienda else None
    if cached:
        return JSONResponse(content=json.loads(cached), headers={"X-Cache":"HIT"})

    query = db.query(Producto)
    if tienda:
        query = query.filter(Producto.tienda.ilike(f"%{tienda}%"))
    result = query.order_by(Producto.created_at.desc()).offset(skip).limit(limit).all()
    data = json.dumps(jsonable_encoder(result))
    if not tienda:
        _set_cache("productos", data, db)
    return JSONResponse(content=json.loads(data), headers={"X-Cache":"MISS"})

@router.get("/{producto_id}", response_model=ProductoResponse)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return prod

@router.put("/{producto_id}/ajustada", response_model=ProductoResponse)
def actualizar_ajustada(producto_id: int, req: UpdateAjustadaRequest, _admin = Depends(require_admin), db: Session = Depends(get_db)):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if req.descripcion_ajustada is not None:
        prod.descripcion_ajustada = req.descripcion_ajustada
    if req.categoria is not None:
        prod.categoria = req.categoria
    if req.n01 is not None:
        prod.n01 = req.n01
    if req.n02 is not None:
        prod.n02 = req.n02
    if req.n03 is not None:
        prod.n03 = req.n03
    if req.proveedor is not None:
        prod.proveedor = req.proveedor
    db.commit()
    db.refresh(prod)
    return prod
