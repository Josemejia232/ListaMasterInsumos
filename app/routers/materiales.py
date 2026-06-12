"""Router CRUD para la columna material de productos Inscal."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Producto
from app.services.auth_service import get_current_user, require_admin
from app.schemas import MaterialInscalRequest, MaterialInscalResponse

router = APIRouter(prefix="/api/materiales", tags=["materiales"])

_MATERIAL_A_CATEGORIA: dict[str, str] = {
    "cemento": "CEMENTOS",
    "cementos": "CEMENTOS",
    "acero": "ACERO",
    "varilla": "ACERO",
    "hierro": "ACERO",
    "arena": "ARENAS",
    "gravilla": "AGREGADOS",
    "grava": "AGREGADOS",
    "agregado": "AGREGADOS",
    "bloque": "BLOQUES",
    "ladrillo": "BLOQUES",
    "ladrillera": "BLOQUES",
    "madera": "MADERAS",
    "teja": "TEJAS",
    "pintura": "PINTURAS",
    "tuberia": "TUBERIA",
    "tubo": "TUBERIA",
    "cable": "ELECTRICOS",
    "electrico": "ELECTRICOS",
    "sanitario": "SANITARIOS",
    "llave": "GRIFERIA",
    "pegante": "ADHESIVOS",
    "adhesivo": "ADHESIVOS",
    "impermeabilizante": "IMPERMEABILIZANTES",
    "pulidora": "HERRAMIENTAS",
    "disco": "HERRAMIENTAS",
    "pala": "HERRAMIENTAS",
}


def _clasificar_categoria(material: str | None) -> str | None:
    if not material:
        return None
    m = material.lower().strip()
    for key, cat in _MATERIAL_A_CATEGORIA.items():
        if key in m:
            return cat
    return material.upper()


@router.get("/inscal", response_model=list[MaterialInscalResponse])
def listar_materiales_inscal(
    material: str | None = None,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user),
):
    query = db.query(Producto).filter(Producto.tienda.ilike("inscal"))
    if material:
        query = query.filter(Producto.material.ilike(f"%{material}%"))
    return query.order_by(Producto.material, Producto.descripcion).all()


@router.get("/inscal/{producto_id}", response_model=MaterialInscalResponse)
def obtener_material_inscal(
    producto_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_current_user),
):
    prod = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.tienda.ilike("inscal"),
    ).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto Inscal no encontrado")
    return prod


@router.put("/inscal/{producto_id}", response_model=MaterialInscalResponse)
def actualizar_material_inscal(
    producto_id: int,
    req: MaterialInscalRequest,
    db: Session = Depends(get_db),
    _admin = Depends(require_admin),
):
    prod = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.tienda.ilike("inscal"),
    ).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto Inscal no encontrado")
    prod.material = req.material
    cat = _clasificar_categoria(req.material)
    if cat:
        prod.categoria = cat
    db.commit()
    db.refresh(prod)
    return prod


@router.post("/inscal/clasificar")
def clasificar_inscal(db: Session = Depends(get_db), _admin = Depends(require_admin)):
    prods = db.query(Producto).filter(Producto.tienda.ilike("inscal")).all()
    count = 0
    for p in prods:
        cat = _clasificar_categoria(p.material)
        if cat and p.categoria != cat:
            p.categoria = cat
            count += 1
    db.commit()
    return {"clasificados": count, "total": len(prods)}


@router.delete("/inscal/{producto_id}", response_model=MaterialInscalResponse)
def eliminar_material_inscal(
    producto_id: int,
    db: Session = Depends(get_db),
    _admin = Depends(require_admin),
):
    prod = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.tienda.ilike("inscal"),
    ).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto Inscal no encontrado")
    prod.material = None
    db.commit()
    db.refresh(prod)
    return prod
