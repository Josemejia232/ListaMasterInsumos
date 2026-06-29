from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models import Usuario
from app.services.auth_service import get_current_user, _plan_info
from app.models_nomina import (
    UsoProyecto, Proyecto, Eps, Afp, Cargo,
    Persona, Vinculacion, Quincena, Prestamo, Abono,
)
from app.nomina.schemas import (
    UsoProyectoIn, UsoProyectoOut,
    ProyectoIn, ProyectoOut,
    EpsIn, EpsOut,
    AfpIn, AfpOut,
    CargoIn, CargoOut,
    PersonaIn, PersonaOut,
    VinculacionIn, VinculacionOut,
    QuincenaIn, QuincenaOut,
    PrestamoIn, PrestamoOut,
    AbonoIn, AbonoOut,
)


def _requiere_nomina(user: Usuario = Depends(get_current_user)):
    if user.tipo == "admin":
        return user
    info = _plan_info(user)
    if info["plan"] == "pro" and info["activo"]:
        return user
    raise HTTPException(
        status_code=403,
        detail="El modulo Nomina requiere plan Pro ($20.000/mes). Actualiza tu plan."
    )


router = APIRouter(prefix="/api/nomina", tags=["Nomina"], dependencies=[Depends(_requiere_nomina)])


# ─── USO PROYECTO ────────────────────────────────
@router.get("/usos-proyecto", response_model=list[UsoProyectoOut])
def listar_usos(db: Session = Depends(get_db)):
    return db.query(UsoProyecto).order_by(UsoProyecto.descripcion).all()


@router.post("/usos-proyecto", response_model=UsoProyectoOut)
def crear_uso(req: UsoProyectoIn, db: Session = Depends(get_db)):
    exists = db.query(UsoProyecto).filter(UsoProyecto.descripcion == req.descripcion).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe ese uso")
    item = UsoProyecto(descripcion=req.descripcion)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/usos-proyecto/{id}", response_model=UsoProyectoOut)
def actualizar_uso(id: int, req: UsoProyectoIn, db: Session = Depends(get_db)):
    item = db.query(UsoProyecto).filter(UsoProyecto.id_uso == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    item.descripcion = req.descripcion
    db.commit()
    db.refresh(item)
    return item


@router.delete("/usos-proyecto/{id}")
def eliminar_uso(id: int, db: Session = Depends(get_db)):
    item = db.query(UsoProyecto).filter(UsoProyecto.id_uso == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── EPS ────────────────────────────────────────
@router.get("/eps", response_model=list[EpsOut])
def listar_eps(db: Session = Depends(get_db)):
    return db.query(Eps).order_by(Eps.nombre_eps).all()


@router.post("/eps", response_model=EpsOut)
def crear_eps(req: EpsIn, db: Session = Depends(get_db)):
    exists = db.query(Eps).filter(Eps.nombre_eps == req.nombre_eps).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe esa EPS")
    item = Eps(nombre_eps=req.nombre_eps)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/eps/{id}", response_model=EpsOut)
def actualizar_eps(id: int, req: EpsIn, db: Session = Depends(get_db)):
    item = db.query(Eps).filter(Eps.id_eps == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    item.nombre_eps = req.nombre_eps
    db.commit()
    db.refresh(item)
    return item


@router.delete("/eps/{id}")
def eliminar_eps(id: int, db: Session = Depends(get_db)):
    item = db.query(Eps).filter(Eps.id_eps == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── AFP ────────────────────────────────────────
@router.get("/afp", response_model=list[AfpOut])
def listar_afp(db: Session = Depends(get_db)):
    return db.query(Afp).order_by(Afp.nombre_afp).all()


@router.post("/afp", response_model=AfpOut)
def crear_afp(req: AfpIn, db: Session = Depends(get_db)):
    exists = db.query(Afp).filter(Afp.nombre_afp == req.nombre_afp).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe esa AFP")
    item = Afp(nombre_afp=req.nombre_afp)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/afp/{id}", response_model=AfpOut)
def actualizar_afp(id: int, req: AfpIn, db: Session = Depends(get_db)):
    item = db.query(Afp).filter(Afp.id_afp == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    item.nombre_afp = req.nombre_afp
    db.commit()
    db.refresh(item)
    return item


@router.delete("/afp/{id}")
def eliminar_afp(id: int, db: Session = Depends(get_db)):
    item = db.query(Afp).filter(Afp.id_afp == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── CARGO ──────────────────────────────────────
@router.get("/cargos", response_model=list[CargoOut])
def listar_cargos(db: Session = Depends(get_db)):
    return db.query(Cargo).order_by(Cargo.descripcion).all()


@router.post("/cargos", response_model=CargoOut)
def crear_cargo(req: CargoIn, db: Session = Depends(get_db)):
    exists = db.query(Cargo).filter(Cargo.descripcion == req.descripcion).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe ese cargo")
    item = Cargo(descripcion=req.descripcion)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/cargos/{id}", response_model=CargoOut)
def actualizar_cargo(id: int, req: CargoIn, db: Session = Depends(get_db)):
    item = db.query(Cargo).filter(Cargo.id_cargo == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    item.descripcion = req.descripcion
    db.commit()
    db.refresh(item)
    return item


@router.delete("/cargos/{id}")
def eliminar_cargo(id: int, db: Session = Depends(get_db)):
    item = db.query(Cargo).filter(Cargo.id_cargo == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── PROYECTO ───────────────────────────────────
@router.get("/proyectos", response_model=list[ProyectoOut])
def listar_proyectos(db: Session = Depends(get_db)):
    items = db.query(
        Proyecto, UsoProyecto.descripcion.label("uso_descripcion")
    ).outerjoin(UsoProyecto, Proyecto.id_uso == UsoProyecto.id_uso).order_by(Proyecto.nombre).all()
    result = []
    for p, uso_desc in items:
        d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
        d["uso_descripcion"] = uso_desc
        result.append(d)
    return result


@router.get("/proyectos/{id}", response_model=ProyectoOut)
def obtener_proyecto(id: int, db: Session = Depends(get_db)):
    item = db.query(Proyecto).filter(Proyecto.id_proyecto == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    item.uso_descripcion = db.query(UsoProyecto.descripcion).filter(UsoProyecto.id_uso == item.id_uso).scalar()
    return item

@router.post("/proyectos", response_model=ProyectoOut)
def crear_proyecto(req: ProyectoIn, db: Session = Depends(get_db)):
    item = Proyecto(**req.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    item.uso_descripcion = db.query(UsoProyecto.descripcion).filter(UsoProyecto.id_uso == item.id_uso).scalar()
    return item


@router.put("/proyectos/{id}", response_model=ProyectoOut)
def actualizar_proyecto(id: int, req: ProyectoIn, db: Session = Depends(get_db)):
    item = db.query(Proyecto).filter(Proyecto.id_proyecto == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    for k, v in req.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    item.uso_descripcion = db.query(UsoProyecto.descripcion).filter(UsoProyecto.id_uso == item.id_uso).scalar()
    return item


@router.delete("/proyectos/{id}")
def eliminar_proyecto(id: int, db: Session = Depends(get_db)):
    item = db.query(Proyecto).filter(Proyecto.id_proyecto == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── PERSONA ────────────────────────────────────
@router.get("/personas", response_model=list[PersonaOut])
def listar_personas(db: Session = Depends(get_db)):
    items = db.query(
        Persona, Eps.nombre_eps.label("eps_nombre"), Afp.nombre_afp.label("afp_nombre")
    ).outerjoin(Eps, Persona.id_eps == Eps.id_eps
    ).outerjoin(Afp, Persona.id_afp == Afp.id_afp).order_by(Persona.nombre).all()
    result = []
    for p, eps_nombre, afp_nombre in items:
        d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
        d["eps_nombre"] = eps_nombre
        d["afp_nombre"] = afp_nombre
        result.append(d)
    return result


@router.get("/personas/{cedula}", response_model=PersonaOut)
def obtener_persona(cedula: int, db: Session = Depends(get_db)):
    item = db.query(Persona).filter(Persona.cedula == cedula).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    item.eps_nombre = db.query(Eps.nombre_eps).filter(Eps.id_eps == item.id_eps).scalar() if item.id_eps else None
    item.afp_nombre = db.query(Afp.nombre_afp).filter(Afp.id_afp == item.id_afp).scalar() if item.id_afp else None
    return item


@router.post("/personas", response_model=PersonaOut)
def crear_persona(req: PersonaIn, db: Session = Depends(get_db)):
    exists = db.query(Persona).filter(Persona.cedula == req.cedula).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe una persona con esa cedula")
    item = Persona(**req.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    item.eps_nombre = db.query(Eps.nombre_eps).filter(Eps.id_eps == item.id_eps).scalar() if item.id_eps else None
    item.afp_nombre = db.query(Afp.nombre_afp).filter(Afp.id_afp == item.id_afp).scalar() if item.id_afp else None
    return item


@router.put("/personas/{cedula}", response_model=PersonaOut)
def actualizar_persona(cedula: int, req: PersonaIn, db: Session = Depends(get_db)):
    item = db.query(Persona).filter(Persona.cedula == cedula).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    for k, v in req.model_dump(exclude={"cedula"}).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    item.eps_nombre = db.query(Eps.nombre_eps).filter(Eps.id_eps == item.id_eps).scalar() if item.id_eps else None
    item.afp_nombre = db.query(Afp.nombre_afp).filter(Afp.id_afp == item.id_afp).scalar() if item.id_afp else None
    return item


@router.delete("/personas/{cedula}")
def eliminar_persona(cedula: int, db: Session = Depends(get_db)):
    item = db.query(Persona).filter(Persona.cedula == cedula).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── VINCULACION ────────────────────────────────
@router.get("/vinculaciones", response_model=list[VinculacionOut])
def listar_vinculaciones(db: Session = Depends(get_db)):
    items = db.query(
        Vinculacion, Persona.nombre.label("persona_nombre"),
        Proyecto.nombre.label("proyecto_nombre"),
        Cargo.descripcion.label("cargo_descripcion")
    ).outerjoin(Persona, Vinculacion.cedula == Persona.cedula
    ).outerjoin(Proyecto, Vinculacion.id_proyecto == Proyecto.id_proyecto
    ).outerjoin(Cargo, Vinculacion.id_cargo == Cargo.id_cargo
    ).order_by(Vinculacion.id_vinculacion.desc()).all()
    result = []
    for v, pn, prn, cd in items:
        d = {c.name: getattr(v, c.name) for c in v.__table__.columns}
        d["persona_nombre"] = pn
        d["proyecto_nombre"] = prn
        d["cargo_descripcion"] = cd
        result.append(d)
    return result


@router.get("/vinculaciones/{id}", response_model=VinculacionOut)
def obtener_vinculacion(id: int, db: Session = Depends(get_db)):
    item = db.query(Vinculacion).filter(Vinculacion.id_vinculacion == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    persona = db.query(Persona.nombre).filter(Persona.cedula == item.cedula).scalar()
    proyecto = db.query(Proyecto.nombre).filter(Proyecto.id_proyecto == item.id_proyecto).scalar()
    cargo = db.query(Cargo.descripcion).filter(Cargo.id_cargo == item.id_cargo).scalar()
    item.persona_nombre = persona
    item.proyecto_nombre = proyecto
    item.cargo_descripcion = cargo
    return item


@router.post("/vinculaciones", response_model=VinculacionOut)
def crear_vinculacion(req: VinculacionIn, db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.cedula == req.cedula).first()
    if not persona:
        raise HTTPException(status_code=400, detail="Persona no existe")
    proyecto = db.query(Proyecto).filter(Proyecto.id_proyecto == req.id_proyecto).first()
    if not proyecto:
        raise HTTPException(status_code=400, detail="Proyecto no existe")
    cargo = db.query(Cargo).filter(Cargo.id_cargo == req.id_cargo).first()
    if not cargo:
        raise HTTPException(status_code=400, detail="Cargo no existe")
    item = Vinculacion(**req.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    item.persona_nombre = persona.nombre
    item.proyecto_nombre = proyecto.nombre
    item.cargo_descripcion = cargo.descripcion
    return item


@router.put("/vinculaciones/{id}", response_model=VinculacionOut)
def actualizar_vinculacion(id: int, req: VinculacionIn, db: Session = Depends(get_db)):
    item = db.query(Vinculacion).filter(Vinculacion.id_vinculacion == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    for k, v in req.model_dump().items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    persona = db.query(Persona.nombre).filter(Persona.cedula == item.cedula).scalar()
    proyecto = db.query(Proyecto.nombre).filter(Proyecto.id_proyecto == item.id_proyecto).scalar()
    cargo = db.query(Cargo.descripcion).filter(Cargo.id_cargo == item.id_cargo).scalar()
    item.persona_nombre = persona
    item.proyecto_nombre = proyecto
    item.cargo_descripcion = cargo
    return item


@router.delete("/vinculaciones/{id}")
def eliminar_vinculacion(id: int, db: Session = Depends(get_db)):
    item = db.query(Vinculacion).filter(Vinculacion.id_vinculacion == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── QUINCENA ───────────────────────────────────
@router.get("/quincenas", response_model=list[QuincenaOut])
def listar_quincenas(db: Session = Depends(get_db)):
    items = db.query(Quincena, Persona.nombre).join(
        Vinculacion, Quincena.id_vinculacion == Vinculacion.id_vinculacion
    ).join(Persona, Vinculacion.cedula == Persona.cedula).order_by(Quincena.fecha_pago.desc()).all()
    result = []
    for q, nombre in items:
        d = {c.name: getattr(q, c.name) for c in q.__table__.columns}
        d["vinculacion_info"] = nombre
        result.append(d)
    return result


@router.get("/quincenas/{id}", response_model=QuincenaOut)
def obtener_quincena(id: int, db: Session = Depends(get_db)):
    item = db.query(Quincena).filter(Quincena.id_quincena == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    item.vinculacion_info = db.query(Persona.nombre).join(
        Vinculacion, Persona.cedula == Vinculacion.cedula
    ).filter(Vinculacion.id_vinculacion == item.id_vinculacion).scalar()
    return item


@router.post("/quincenas", response_model=QuincenaOut)
def crear_quincena(req: QuincenaIn, db: Session = Depends(get_db)):
    vinculacion = db.query(Vinculacion).filter(Vinculacion.id_vinculacion == req.id_vinculacion).first()
    if not vinculacion:
        raise HTTPException(status_code=400, detail="Vinculacion no existe")
    item = Quincena(
        id_vinculacion=req.id_vinculacion,
        numero_quincena=req.numero_quincena,
        fecha_pago=req.fecha_pago,
        valor_bruto=req.valor_bruto,
        desc_abono=req.desc_abono,
        desc_seguro=req.desc_seguro,
        valor_neto=Quincena.calcular_neto(req.valor_bruto, req.desc_abono, req.desc_seguro),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    persona = db.query(Persona.nombre).join(Vinculacion, Persona.cedula == Vinculacion.cedula).filter(
        Vinculacion.id_vinculacion == item.id_vinculacion
    ).scalar()
    item.vinculacion_info = persona
    return item


@router.put("/quincenas/{id}", response_model=QuincenaOut)
def actualizar_quincena(id: int, req: QuincenaIn, db: Session = Depends(get_db)):
    item = db.query(Quincena).filter(Quincena.id_quincena == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    for k, v in req.model_dump().items():
        setattr(item, k, v)
    item.valor_neto = Quincena.calcular_neto(item.valor_bruto, item.desc_abono, item.desc_seguro)
    db.commit()
    db.refresh(item)
    persona = db.query(Persona.nombre).join(Vinculacion, Persona.cedula == Vinculacion.cedula).filter(
        Vinculacion.id_vinculacion == item.id_vinculacion
    ).scalar()
    item.vinculacion_info = persona
    return item


@router.delete("/quincenas/{id}")
def eliminar_quincena(id: int, db: Session = Depends(get_db)):
    item = db.query(Quincena).filter(Quincena.id_quincena == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── PRESTAMO ───────────────────────────────────
@router.get("/prestamos", response_model=list[PrestamoOut])
def listar_prestamos(db: Session = Depends(get_db)):
    items = db.query(Prestamo, Persona.nombre).join(
        Vinculacion, Prestamo.id_vinculacion == Vinculacion.id_vinculacion
    ).join(Persona, Vinculacion.cedula == Persona.cedula).order_by(Prestamo.fecha_prestamo.desc()).all()
    result = []
    for p, nombre in items:
        d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
        d["vinculacion_info"] = nombre
        result.append(d)
    return result


@router.get("/prestamos/{id}", response_model=PrestamoOut)
def obtener_prestamo(id: int, db: Session = Depends(get_db)):
    item = db.query(Prestamo).filter(Prestamo.id_prestamo == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    item.vinculacion_info = db.query(Persona.nombre).join(
        Vinculacion, Persona.cedula == Vinculacion.cedula
    ).filter(Vinculacion.id_vinculacion == item.id_vinculacion).scalar()
    return item


@router.post("/prestamos", response_model=PrestamoOut)
def crear_prestamo(req: PrestamoIn, db: Session = Depends(get_db)):
    vinculacion = db.query(Vinculacion).filter(Vinculacion.id_vinculacion == req.id_vinculacion).first()
    if not vinculacion:
        raise HTTPException(status_code=400, detail="Vinculacion no existe")
    item = Prestamo(
        id_vinculacion=req.id_vinculacion,
        fecha_prestamo=req.fecha_prestamo,
        valor=req.valor,
        saldo=req.valor,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    persona = db.query(Persona.nombre).join(Vinculacion, Persona.cedula == Vinculacion.cedula).filter(
        Vinculacion.id_vinculacion == item.id_vinculacion
    ).scalar()
    item.vinculacion_info = persona
    return item


@router.put("/prestamos/{id}", response_model=PrestamoOut)
def actualizar_prestamo(id: int, req: PrestamoIn, db: Session = Depends(get_db)):
    item = db.query(Prestamo).filter(Prestamo.id_prestamo == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    old_valor = item.valor
    for k, v in req.model_dump().items():
        setattr(item, k, v)
    diff = round(item.valor - old_valor, 2)
    item.saldo = round(item.saldo + diff, 2)
    db.commit()
    db.refresh(item)
    persona = db.query(Persona.nombre).join(Vinculacion, Persona.cedula == Vinculacion.cedula).filter(
        Vinculacion.id_vinculacion == item.id_vinculacion
    ).scalar()
    item.vinculacion_info = persona
    return item


@router.delete("/prestamos/{id}")
def eliminar_prestamo(id: int, db: Session = Depends(get_db)):
    item = db.query(Prestamo).filter(Prestamo.id_prestamo == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ─── ABONO ──────────────────────────────────────
@router.get("/abonos", response_model=list[AbonoOut])
def listar_abonos(prestamo_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Abono)
    if prestamo_id:
        q = q.filter(Abono.id_prestamo == prestamo_id)
    return q.order_by(Abono.fecha_abono.desc()).all()


@router.get("/abonos/{id}", response_model=AbonoOut)
def obtener_abono(id: int, db: Session = Depends(get_db)):
    item = db.query(Abono).filter(Abono.id_abono == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    return item


@router.post("/abonos", response_model=AbonoOut)
def crear_abono(req: AbonoIn, db: Session = Depends(get_db)):
    prestamo = db.query(Prestamo).filter(Prestamo.id_prestamo == req.id_prestamo).first()
    if not prestamo:
        raise HTTPException(status_code=400, detail="Prestamo no existe")
    if req.valor_abono <= 0:
        raise HTTPException(status_code=400, detail="Valor de abono debe ser > 0")
    if req.valor_abono > prestamo.saldo:
        raise HTTPException(status_code=400, detail="Abono excede el saldo del prestamo")
    item = Abono(**req.model_dump())
    prestamo.saldo = round(prestamo.saldo - req.valor_abono, 2)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/abonos/{id}", response_model=AbonoOut)
def actualizar_abono(id: int, req: AbonoIn, db: Session = Depends(get_db)):
    item = db.query(Abono).filter(Abono.id_abono == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    old_prestamo_id = item.id_prestamo
    old_valor = item.valor_abono
    prestamo = db.query(Prestamo).filter(Prestamo.id_prestamo == old_prestamo_id).first()
    if prestamo:
        prestamo.saldo = round(prestamo.saldo + old_valor, 2)
    for k, v in req.model_dump().items():
        setattr(item, k, v)
    if req.valor_abono <= 0:
        raise HTTPException(status_code=400, detail="Valor de abono debe ser > 0")
    nuevo_prestamo = db.query(Prestamo).filter(Prestamo.id_prestamo == item.id_prestamo).first()
    if not nuevo_prestamo:
        raise HTTPException(status_code=400, detail="Prestamo no existe")
    if item.valor_abono > nuevo_prestamo.saldo:
        raise HTTPException(status_code=400, detail="Abono excede el saldo del prestamo")
    nuevo_prestamo.saldo = round(nuevo_prestamo.saldo - item.valor_abono, 2)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/abonos/{id}")
def eliminar_abono(id: int, db: Session = Depends(get_db)):
    item = db.query(Abono).filter(Abono.id_abono == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    prestamo = db.query(Prestamo).filter(Prestamo.id_prestamo == item.id_prestamo).first()
    if prestamo:
        prestamo.saldo = round(prestamo.saldo + item.valor_abono, 2)
    db.delete(item)
    db.commit()
    return {"ok": True}
