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


class BoquillaRequest(BaseModel):
    formato: str
    ancho_mm: int
    area_m2: float


class MaterialBoquilla(BaseModel):
    nombre: str
    unidad: str
    cantidad: float
    vr_unitario: float
    vr_total: float


class BoquillaResponse(BaseModel):
    formato: str
    ancho_mm: int
    area_m2: float
    factor_consumo: float
    kg_totales: float
    materiales: list[MaterialBoquilla]
    total: float


class YesoRequest(BaseModel):
    h: float
    l: float
    e: float = 0.6
    con_lana: bool = False
    desp: float = 0.05
    factor_torn: int = 30
    kg_m2_masilla: float = 0.5
    n_manos_masilla: int = 2
    rendimiento_m2_dia: float = 12
    n_operarios: int = 2
    jornal: float = 120000
    precios: dict[str, float] | None = None


class MaterialYeso(BaseModel):
    nombre: str
    unidad: str
    cantidad: float
    vr_unitario: float
    vr_total: float


class YesoResponse(BaseModel):
    h: float
    l: float
    area_m2: float
    e: float
    con_lana: bool
    materiales: list[MaterialYeso]
    total: float
