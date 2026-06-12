"""Esquemas Pydantic compartidos."""
from datetime import datetime
from pydantic import BaseModel, field_validator

class ScrapeRequest(BaseModel):
    sheet_url: str
    @field_validator("sheet_url")
    @classmethod
    def validate_sheet_url(cls, v):
        if not v or not v.startswith("https://"):
            raise ValueError("URL debe ser HTTPS valida")
        if "docs.google.com" not in v:
            raise ValueError("URL debe ser de Google Sheets")
        return v

class ScrapeResponse(BaseModel):
    total: int
    nuevos: int
    actualizados: int
    sin_cambio: int
    fallidos: int
    mensaje: str

class SyncResponse(BaseModel):
    total: int
    actualizados: int
    sin_cambio: int
    no_encontrados: int
    sin_categoria: int
    urls_no_encontradas: list[str] = []
    mensaje: str

class ProductoResponse(BaseModel):
    id: int
    codigo: str
    descripcion: str
    descripcion_ajustada: str | None = None
    unidad: str
    valor: float
    valor_anterior: float | None = None
    origen: str | None = None
    categoria: str | None = None
    n01: str | None = None
    n02: str | None = None
    n03: str | None = None
    proveedor: str | None = None
    material: str | None = None
    tienda: str
    url_origen: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}

class InsumoRequest(BaseModel):
    descripcion: str
    un: str = "Unidad"
    valor: float = 0.0
    @field_validator("valor")
    @classmethod
    def validate_valor(cls, v):
        if v < 0:
            raise ValueError("Valor no puede ser negativo")
        return v

class InsumoResponse(InsumoRequest):
    id: int
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

class ProductoPublicResponse(BaseModel):
    id: int
    descripcion: str
    unidad: str
    valor: float
    categoria: str | None = None
    n01: str | None = None
    n02: str | None = None
    n03: str | None = None
    proveedor: str | None = None
    model_config = {"from_attributes": True}

class LoginRequest(BaseModel):
    email: str
    token: str
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email invalido")
        return v.strip().lower()

class LoginResponse(BaseModel):
    id: int
    email: str
    token: str = ""
    tipo: str
    plan: str | None = None
    fecha_pago: datetime | None = None
    plan_activo: bool = False

class UpdateAjustadaRequest(BaseModel):
    descripcion_ajustada: str | None = None
    categoria: str | None = None
    n01: str | None = None
    n02: str | None = None
    n03: str | None = None
    proveedor: str | None = None
    material: str | None = None

class MaterialInscalRequest(BaseModel):
    material: str

class MaterialInscalResponse(BaseModel):
    id: int
    codigo: str
    descripcion: str
    tienda: str
    material: str | None = None
    categoria: str | None = None
    model_config = {"from_attributes": True}

class UsuarioRequest(BaseModel):
    email: str
    token: str = ""
    activo: bool = True
    tipo: str = "usuario"
    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        if v not in ("admin", "usuario"):
            raise ValueError("Tipo debe ser 'admin' o 'usuario'")
        return v
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email invalido")
        return v.strip().lower()

class UsuarioResponse(BaseModel):
    id: int
    email: str
    token: str
    activo: bool
    tipo: str
    fecha_pago: datetime | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}

    @field_validator("token", mode="before")
    @classmethod
    def mask_token(cls, v):
        if v and len(str(v)) > 8:
            return "****" + str(v)[-4:]
        return v

class CrearLinkRequest(BaseModel):
    usuario_id: int
    amount: float
    description: str = "Suscripcion ListaMasterInsumos"
    expiration_minutes: int = 60
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v < 1000:
            raise ValueError("Monto minimo: $1,000 COP")
        return v

class CrearLinkResponse(BaseModel):
    id: int
    payment_link: str
    url: str
    reference: str
    amount: float
    status: str

class PagoResponse(BaseModel):
    id: int
    usuario_id: int
    payment_link: str
    url: str
    reference: str
    amount: float
    status: str
    transaction_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}

class ComprarPlanResponse(BaseModel):
    id: int
    url: str
    amount: float
    status: str

class ComprarPlanRequest(BaseModel):
    plan: str
    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v):
        if v not in ("basico", "plus"):
            raise ValueError("Plan debe ser 'basico' o 'plus'")
        return v

class UpgradePlanResponse(BaseModel):
    id: int
    url: str
    amount: float
    monto_original: float = 15000.0
    credito_basico: float = 0.0
    status: str

class PlanInfo(BaseModel):
    plan: str
    activo: bool
    dias_restantes: int | None = None
    puede_upgradear: bool = False
    upgrade: dict | None = None
