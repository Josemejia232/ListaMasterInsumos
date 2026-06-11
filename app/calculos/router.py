from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import hmac

from app.database import get_db
from app.models import Insumo, Producto, Usuario, UsoCalculo
from app.calculos.data import MEZCLAS, PRECIOS_FIJOS
from app.calculos.schemas import MezclaResponse, MaterialCalculado, AnclajeRequest, AnclajeResponse, MaterialAnclaje, MezclaMetaResponse
from app.calculos.data_anclajes import calcular_anclaje

router = APIRouter(prefix="/api/calculos", tags=["Cálculos"])

# Fallback cuando no se encuentra en BD ni en fijos
_FALLBACK_PRECIOS: dict[str, float] = {
    "Cemento": 546.0,
    "Arena de rio": 45000.0,
    "Arena de peña": 42000.0,
    "Arena de pozo": 38000.0,
    "Material de rio (gravilla)": 55000.0,
    "Bloque #4 (10x20x40)": 2500.0,
    "Bloque #5 (10x20x40)": 3200.0,
    "Ladrillo tolete (5x10x20)": 800.0,
    "Ladrillo farol (10x20x30)": 1500.0,
    "Ladrillo tablete (4x10x20)": 700.0,
    "Mortero de pega": 180000.0,
    # Ladrillera Santafé — Adoquines
    "Adoquín Cuarto 26 Cobrizo": 2500.0,
    "Adoquín Cuarto 26 Terracota": 2500.0,
    "Adoquín Español Tráfico Pesado": 3500.0,
    "Adoquín Español Cobrizo": 3000.0,
    "Adoquín Español Terracota": 3000.0,
    # Ladrillera Santafé — Estructurales
    "Ladrillo Portante 30 x 12 Capuchino H": 1200.0,
    "Ladrillo Estructural de Perforación Vertical Doble Pared Medio Fachada Rojo": 1500.0,
    "Ladrillo Estructural de Perforación Vertical Doble Pared Pieza Entera": 2500.0,
    "Ladrillo Estructural de Perforación Vertical Medio fachada Rojo RE": 1500.0,
    "Ladrillo Portante 30 Terracota": 1400.0,
    "Ladrillo Portante 30 x 12 Cocoa": 1200.0,
    "Ladrillo Portante 30 x 12 Terracota": 1200.0,
    "Pieza Media de Traba": 1800.0,
    # Ladrillera Santafé — Fachadas
    "Ladrillo Gran Formato Liso Duna": 2000.0,
    "Ladrillo Gran Formato Cobrizo": 2000.0,
    "Ladrillo Gran Formato Cocoa": 2000.0,
    "Ladrillo Gran Formato Duna": 2000.0,
    "Ladrillo Gran Formato Terracota": 2000.0,
    "Ladrillo Gran Formato Tierra": 2000.0,
    "Ladrillo Prensado Liviano 6 Titanio H": 1000.0,
    "Ladrillo Prensado Liviano 6 cm Capuchino H": 1000.0,
    "Ladrillo Prensado Liviano 6 cm Cocoa H": 1000.0,
    "Ladrillo Prensado Liviano 6 cm Coral H": 1000.0,
    "Ladrillo Prensado Liviano 6 cm Terracota": 1000.0,
    "Ladrillo Prensado Macizo Terracota": 1200.0,
    "Ladrillo Tolete Fino Liviano Tierra": 900.0,
    # Ladrillera Santafé — Divisorios
    "Bloque N° 4": 2500.0,
    "Bloque N° 4 Perforación Vertical": 2600.0,
    "Bloque N° 5 Perforación Vertical": 3200.0,
    "Bloque N° 5": 3200.0,
    # Ladrillera Santafé — Placafácil
    "Bloquelón": 5000.0,
    # Complementos mampostería
    "Arena de Base": 45000.0,
    "Arena de Sello": 42000.0,
    "Adhesivo cementicio": 25000.0,
}


def _get_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")
    token = authorization[7:]
    user = db.query(Usuario).filter(Usuario.activo == True, Usuario.token == token).first()
    if user and hmac.compare_digest(token, user.token or ""):
        return user
    raise HTTPException(status_code=401, detail="Token invalido")


def _requiere_plan_calculo(tipo: str, user: Usuario = Depends(_get_user), db: Session = Depends(get_db)):
    if user.tipo == "admin":
        return True
    # Plan vencido o sin plan → Free
    plan = "free"
    if user.fecha_pago and (datetime.utcnow() - user.fecha_pago).days < 30:
        plan = user.plan or "plus"
    if plan == "plus":
        return True
    if plan == "basico":
        raise HTTPException(status_code=403, detail="El plan Basico no incluye calculadora. Actualiza a Plus.")
    # Free: verificar limite de 3 por tipo
    count = db.query(func.count(UsoCalculo.id)).filter(
        UsoCalculo.usuario_id == user.id,
        UsoCalculo.tipo == tipo,
    ).scalar()
    if count >= 3:
        raise HTTPException(status_code=403, detail=f"Limite Free alcanzado: 3 calculos de {tipo}. Actualiza a Plus para acceso ilimitado.")
    db.add(UsoCalculo(usuario_id=user.id, tipo=tipo))
    db.commit()
    return True


def _requiere_plan(tipo: str, user: Usuario = Depends(_get_user), db: Session = Depends(get_db)):
    """Same as _requiere_plan_calculo but without recording usage (for list endpoints)."""
    if user.tipo == "admin":
        return True
    plan = "free"
    if user.fecha_pago and (datetime.utcnow() - user.fecha_pago).days < 30:
        plan = user.plan or "plus"
    if plan == "plus":
        return True
    if plan == "basico":
        raise HTTPException(status_code=403, detail="El plan Basico no incluye calculadora. Actualiza a Plus.")
    # Free - check usage count but don't register
    count = db.query(func.count(UsoCalculo.id)).filter(
        UsoCalculo.usuario_id == user.id,
        UsoCalculo.tipo == tipo,
    ).scalar()
    if count >= 3:
        raise HTTPException(status_code=403, detail=f"Limite Free alcanzado: 3 calculos de {tipo}. Actualiza a Plus para acceso ilimitado.")
    return True


# ─── Endpoints ─────────────────────────────────────────────────

def _buscar_precio_bd(nombre: str, keywords: list[str], db: Session) -> float | None:
    """Busca el precio de un material en Insumo o Producto por palabras clave."""
    if not keywords:
        return None

    from sqlalchemy import or_
    mejor = None
    for modelo, col in [(Insumo, Insumo.descripcion), (Producto, Producto.descripcion)]:
        q = db.query(func.min(modelo.valor)).filter(
            or_(*[col.ilike(f"%{kw}%") for kw in keywords]),
            modelo.valor > 0
        )
        v = q.scalar()
        if v is not None:
            if mejor is None or v < mejor:
                mejor = v
    return mejor


def _calcular_mezcla(mezcla_id: str, db: Session) -> MezclaResponse:
    mezcla = MEZCLAS.get(mezcla_id)
    if not mezcla:
        raise HTTPException(status_code=404, detail=f"Mezcla '{mezcla_id}' no encontrada")

    materiales_calc: list[MaterialCalculado] = []
    total = 0.0

    for mat in mezcla.materiales:
        vr_unitario = PRECIOS_FIJOS.get(mat.nombre)

        if vr_unitario is not None:
            fuente = "fijo"
        else:
            vr_unitario = _buscar_precio_bd(mat.nombre, mat.keywords, db)
            if vr_unitario is not None:
                fuente = "db"
            else:
                vr_unitario = _FALLBACK_PRECIOS.get(mat.nombre, 0.0)
                fuente = "fallback"

        vr_total = round(mat.cantidad * vr_unitario, 2)
        total += vr_total

        materiales_calc.append(MaterialCalculado(
            nombre=mat.nombre,
            unidad=mat.unidad,
            cantidad=mat.cantidad,
            vr_unitario=vr_unitario,
            vr_total=vr_total,
            fuente=fuente,
        ))

    total = round(total, 2)

    return MezclaResponse(
        id=mezcla.id,
        tipo=mezcla.tipo,
        nombre=mezcla.nombre,
        proporcion=mezcla.proporcion,
        resistencia_psi=mezcla.resistencia_psi,
        categoria=mezcla.categoria,
        materiales=materiales_calc,
        total=total,
    )


@router.get("", response_model=list[MezclaMetaResponse])
def listar_mezclas(
    tipo: str | None = None,
    user: Usuario = Depends(_get_user),
    db: Session = Depends(get_db),
):
    if user.tipo == "admin":
        plan = "plus"
    elif user.fecha_pago and (datetime.utcnow() - user.fecha_pago).days < 30:
        plan = user.plan or "plus"
    else:
        plan = "free"
    if plan == "basico":
        raise HTTPException(status_code=403, detail="El plan Basico no incluye calculadora. Actualiza a Plus.")

    resultados = []
    for mezcla_id in MEZCLAS:
        m = MEZCLAS[mezcla_id]
        if tipo and m.tipo != tipo:
            continue
        resultados.append(MezclaMetaResponse(
            id=m.id,
            tipo=m.tipo,
            nombre=m.nombre,
            proporcion=m.proporcion,
            resistencia_psi=m.resistencia_psi,
            categoria=m.categoria,
        ))

    if plan == "free":
        cats = {"concreto": 0, "mortero": 0, "mamposteria": 0}
        limited = []
        for r in resultados:
            t = r.tipo
            key = "mamposteria" if t == "mamposteria" else "concreto"
            if cats.get(t if t == "mamposteria" else key, cats["concreto"]) < 3:
                limited.append(r)
                cats[t if t == "mamposteria" else key] += 1
        return limited[:9]
    return resultados


@router.get("/{mezcla_id}", response_model=MezclaResponse)
def obtener_mezcla(mezcla_id: str, user: Usuario = Depends(_get_user), db: Session = Depends(get_db)):
    check_tipo = "mamposteria" if ("mamp" in mezcla_id.lower() or "santafe" in mezcla_id.lower()) else "mezcla"
    _requiere_plan_calculo(check_tipo, user, db)
    return _calcular_mezcla(mezcla_id, db)


@router.post("/anclajes", response_model=AnclajeResponse)
def calcular_anclajes(req: AnclajeRequest, user: Usuario = Depends(_get_user), db: Session = Depends(get_db)):
    _requiere_plan_calculo("anclajes", user, db)
    if req.diametro_mm < 4 or req.diametro_mm > 32:
        raise HTTPException(status_code=400, detail="Diametro debe estar entre 4 y 32 mm")
    if req.profundidad_mm < 20 or req.profundidad_mm > 500:
        raise HTTPException(status_code=400, detail="Profundidad debe estar entre 20 y 500 mm")
    if req.cantidad < 1:
        raise HTTPException(status_code=400, detail="Cantidad debe ser mayor a 0")
    return calcular_anclaje(req.diametro_mm, req.profundidad_mm, req.cantidad, req.material_base)
