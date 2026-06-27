from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, func
from app.database import Base


class UsoProyecto(Base):
    __tablename__ = "uso_proyecto"
    id_uso = Column(Integer, primary_key=True, autoincrement=True)
    descripcion = Column(String(100), nullable=False, unique=True)


class Proyecto(Base):
    __tablename__ = "proyecto"
    id_proyecto = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False)
    direccion = Column(String(300), nullable=True)
    responsable = Column(String(200), nullable=True)
    id_uso = Column(Integer, ForeignKey("uso_proyecto.id_uso"), nullable=False)


class Eps(Base):
    __tablename__ = "eps"
    id_eps = Column(Integer, primary_key=True, autoincrement=True)
    nombre_eps = Column(String(200), nullable=False, unique=True)


class Afp(Base):
    __tablename__ = "afp"
    id_afp = Column(Integer, primary_key=True, autoincrement=True)
    nombre_afp = Column(String(200), nullable=False, unique=True)


class Cargo(Base):
    __tablename__ = "cargo"
    id_cargo = Column(Integer, primary_key=True, autoincrement=True)
    descripcion = Column(String(100), nullable=False, unique=True)


class Persona(Base):
    __tablename__ = "persona"
    cedula = Column(Integer, primary_key=True)
    fecha_expedicion = Column(Date, nullable=True)
    nombre = Column(String(200), nullable=False)
    celular = Column(String(20), nullable=True)
    id_eps = Column(Integer, ForeignKey("eps.id_eps"), nullable=True)
    id_afp = Column(Integer, ForeignKey("afp.id_afp"), nullable=True)


class Vinculacion(Base):
    __tablename__ = "vinculacion"
    id_vinculacion = Column(Integer, primary_key=True, autoincrement=True)
    cedula = Column(Integer, ForeignKey("persona.cedula"), nullable=False)
    id_proyecto = Column(Integer, ForeignKey("proyecto.id_proyecto"), nullable=False)
    id_cargo = Column(Integer, ForeignKey("cargo.id_cargo"), nullable=False)
    fecha_ingreso = Column(Date, nullable=False)
    fecha_retiro = Column(Date, nullable=True)
    estado = Column(String(20), nullable=False, default="Activo")
    salario_quincenal = Column(Float, nullable=False, default=0.0)


class Quincena(Base):
    __tablename__ = "quincena"
    id_quincena = Column(Integer, primary_key=True, autoincrement=True)
    id_vinculacion = Column(Integer, ForeignKey("vinculacion.id_vinculacion"), nullable=False)
    numero_quincena = Column(Integer, nullable=False)
    fecha_pago = Column(Date, nullable=False)
    valor_bruto = Column(Float, nullable=False, default=0.0)
    desc_abono = Column(Float, nullable=False, default=0.0)
    desc_seguro = Column(Float, nullable=False, default=0.0)
    valor_neto = Column(Float, nullable=False, default=0.0)

    @staticmethod
    def calcular_neto(bruto: float, desc_abono: float, desc_seguro: float) -> float:
        return round(bruto - desc_abono - desc_seguro, 2)


class Prestamo(Base):
    __tablename__ = "prestamo"
    id_prestamo = Column(Integer, primary_key=True, autoincrement=True)
    id_vinculacion = Column(Integer, ForeignKey("vinculacion.id_vinculacion"), nullable=False)
    fecha_prestamo = Column(Date, nullable=False)
    valor = Column(Float, nullable=False, default=0.0)
    saldo = Column(Float, nullable=False, default=0.0)


class Abono(Base):
    __tablename__ = "abono"
    id_abono = Column(Integer, primary_key=True, autoincrement=True)
    id_prestamo = Column(Integer, ForeignKey("prestamo.id_prestamo"), nullable=False)
    fecha_abono = Column(Date, nullable=False)
    valor_abono = Column(Float, nullable=False, default=0.0)
    quincena_origen = Column(Integer, ForeignKey("quincena.id_quincena"), nullable=True)
