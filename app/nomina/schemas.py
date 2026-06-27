from pydantic import BaseModel
from datetime import date
from typing import Optional


class UsoProyectoIn(BaseModel):
    descripcion: str


class UsoProyectoOut(UsoProyectoIn):
    id_uso: int
    model_config = {"from_attributes": True}


class ProyectoIn(BaseModel):
    nombre: str
    direccion: Optional[str] = None
    responsable: Optional[str] = None
    id_uso: int


class ProyectoOut(ProyectoIn):
    id_proyecto: int
    uso_descripcion: Optional[str] = None
    model_config = {"from_attributes": True}


class EpsIn(BaseModel):
    nombre_eps: str


class EpsOut(EpsIn):
    id_eps: int
    model_config = {"from_attributes": True}


class AfpIn(BaseModel):
    nombre_afp: str


class AfpOut(AfpIn):
    id_afp: int
    model_config = {"from_attributes": True}


class CargoIn(BaseModel):
    descripcion: str


class CargoOut(CargoIn):
    id_cargo: int
    model_config = {"from_attributes": True}


class PersonaIn(BaseModel):
    cedula: int
    fecha_expedicion: Optional[date] = None
    nombre: str
    celular: Optional[str] = None
    id_eps: Optional[int] = None
    id_afp: Optional[int] = None


class PersonaOut(PersonaIn):
    eps_nombre: Optional[str] = None
    afp_nombre: Optional[str] = None
    model_config = {"from_attributes": True}


class VinculacionIn(BaseModel):
    cedula: int
    id_proyecto: int
    id_cargo: int
    fecha_ingreso: date
    fecha_retiro: Optional[date] = None
    estado: str = "Activo"
    salario_quincenal: float = 0.0


class VinculacionOut(BaseModel):
    id_vinculacion: int
    cedula: int
    persona_nombre: Optional[str] = None
    id_proyecto: int
    proyecto_nombre: Optional[str] = None
    id_cargo: int
    cargo_descripcion: Optional[str] = None
    fecha_ingreso: date
    fecha_retiro: Optional[date] = None
    estado: str
    salario_quincenal: float
    model_config = {"from_attributes": True}


class QuincenaIn(BaseModel):
    id_vinculacion: int
    numero_quincena: int
    fecha_pago: date
    valor_bruto: float = 0.0
    desc_abono: float = 0.0
    desc_seguro: float = 0.0


class QuincenaOut(BaseModel):
    id_quincena: int
    id_vinculacion: int
    vinculacion_info: Optional[str] = None
    numero_quincena: int
    fecha_pago: date
    valor_bruto: float
    desc_abono: float
    desc_seguro: float
    valor_neto: float
    model_config = {"from_attributes": True}


class PrestamoIn(BaseModel):
    id_vinculacion: int
    fecha_prestamo: date
    valor: float = 0.0


class PrestamoOut(BaseModel):
    id_prestamo: int
    id_vinculacion: int
    vinculacion_info: Optional[str] = None
    fecha_prestamo: date
    valor: float
    saldo: float
    model_config = {"from_attributes": True}


class AbonoIn(BaseModel):
    id_prestamo: int
    fecha_abono: date
    valor_abono: float = 0.0
    quincena_origen: Optional[int] = None


class AbonoOut(BaseModel):
    id_abono: int
    id_prestamo: int
    fecha_abono: date
    valor_abono: float
    quincena_origen: Optional[int] = None
    model_config = {"from_attributes": True}
