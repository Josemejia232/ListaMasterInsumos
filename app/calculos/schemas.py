from pydantic import BaseModel
from typing import Literal


class MaterialCalculado(BaseModel):
    nombre: str
    unidad: str
    cantidad: float
    vr_unitario: float
    vr_total: float
    fuente: str  # "db" | "fijo"


class MezclaResponse(BaseModel):
    id: str
    tipo: str
    nombre: str
    proporcion: str
    resistencia_psi: int | None = None
    categoria: str | None = None
    materiales: list[MaterialCalculado]
    total: float


class CalculoRequest(BaseModel):
    tipo: str  # "concreto" | "mortero"
    mezcla_id: str


class AnclajeRequest(BaseModel):
    diametro_mm: int
    profundidad_mm: int
    cantidad: int
    material_base: Literal["concreto", "ladrillo_macizo", "piedra"] = "concreto"


class MaterialAnclaje(BaseModel):
    nombre: str
    unidad: str
    cantidad: float
    vr_unitario: float
    vr_total: float


class AnclajeResponse(BaseModel):
    volumen_total_cm3: float
    tubos_calculados: int
    materiales: list[MaterialAnclaje]
    total: float


class MezclaMetaResponse(BaseModel):
    id: str
    tipo: str
    nombre: str
    proporcion: str
    resistencia_psi: int | None = None
    categoria: str | None = None
