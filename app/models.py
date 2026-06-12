from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func, UniqueConstraint, Text
from app.database import Base


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (
        UniqueConstraint("codigo", "tienda", name="uq_producto_codigo_tienda"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(100), nullable=False, index=True)
    descripcion = Column(String(500), nullable=False)
    unidad = Column(String(50), nullable=False)
    valor = Column(Float, nullable=False)
    valor_anterior = Column(Float, nullable=True)
    origen = Column(String(20), nullable=True)  # sheet | manual
    categoria = Column(String(200), nullable=True)
    n01 = Column(String(200), nullable=True)
    n02 = Column(String(200), nullable=True)
    n03 = Column(String(200), nullable=True)
    proveedor = Column(String(200), nullable=True)
    descripcion_ajustada = Column(String(500), nullable=True)
    material = Column(String(200), nullable=True)
    tienda = Column(String(200), nullable=False)
    url_origen = Column(String(1000), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Insumo(Base):
    __tablename__ = "insumos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    descripcion = Column(String(500), nullable=False)
    un = Column(String(50), nullable=False, default="Unidad")
    valor = Column(Float, nullable=False, default=0.0)
    categoria = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    token = Column(String(200), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    tipo = Column(String(20), default="usuario", nullable=False)  # admin | usuario
    plan = Column(String(10), nullable=True)  # NULL=free, 'basico', 'plus'
    fecha_pago = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    payment_link = Column(String(30), unique=True, nullable=False)
    url = Column(String(200), nullable=False)
    reference = Column(String(60), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)
    transaction_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UsoCalculo(Base):
    __tablename__ = "uso_calculos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # 'mezcla', 'mamposteria', 'anclajes'
    created_at = Column(DateTime, server_default=func.now())


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), nullable=False, index=True)
    window_start = Column(DateTime, nullable=False, index=True)
    request_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class CacheEntry(Base):
    __tablename__ = "cache_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())


class UserMaterialOverride(Base):
    __tablename__ = "user_material_overrides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    unidad = Column(String(50), nullable=False, default="")
    cantidad = Column(Float, nullable=False, default=0.0)
    vr_unitario = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
