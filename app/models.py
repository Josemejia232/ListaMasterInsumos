from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func, UniqueConstraint
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
