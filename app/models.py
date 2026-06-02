from sqlalchemy import Column, Integer, String, Float, DateTime, func, UniqueConstraint
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
    created_at = Column(DateTime, server_default=func.now())
