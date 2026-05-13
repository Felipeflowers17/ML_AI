"""Modelos SQLAlchemy ORM para el Monitor de Licitaciones.

Todos los modelos heredan de ``Base`` y son descubiertos automáticamente
por Alembic para generar migraciones.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Licitacion(Base):
    """Representa una licitación obtenida de Mercado Público."""

    __tablename__ = "licitaciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_externo = Column(String(50), unique=True, index=True, nullable=False)
    nombre = Column(String(500), nullable=False)
    descripcion = Column(Text, nullable=True)
    detalle_productos = Column(Text, nullable=True)
    fecha_publicacion = Column(DateTime, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_adjudicacion = Column(DateTime, nullable=True)
    codigo_organismo = Column(
        String, ForeignKey("organismos.codigo"), nullable=True
    )
    codigo_estado = Column(
        Integer, ForeignKey("estados_licitacion.codigo"), nullable=True
    )
    score_resumen = Column(Integer, default=0, nullable=False)
    score_detalle = Column(Integer, default=0, nullable=False)
    score_total = Column(Integer, default=0, index=True, nullable=False)
    etapa = Column(String, default="ignorada", nullable=False)
    justificacion_score = Column(Text, nullable=True)
    tiene_detalle = Column(Boolean, default=False, nullable=False)
    fecha_extraccion = Column(DateTime, default=func.now(), nullable=False)
    fecha_actualizacion = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class PalabraClave(Base):
    """Palabra clave para el scoring con pesos por campo."""

    __tablename__ = "palabras_clave"

    id = Column(Integer, primary_key=True, autoincrement=True)
    termino = Column(String(100), index=True, nullable=False)
    categoria = Column(String(100), nullable=True)
    peso_titulo = Column(Integer, default=0, nullable=False)
    peso_descripcion = Column(Integer, default=0, nullable=False)
    peso_productos = Column(Integer, default=0, nullable=False)
    activa = Column(Boolean, default=True, nullable=False)


class Organismo(Base):
    """Organismo público (comprador) registrado en Mercado Público."""

    __tablename__ = "organismos"

    codigo = Column(String, primary_key=True, index=True)
    nombre = Column(String(200), index=True, nullable=False)
    puntaje_fijo = Column(Integer, default=0, nullable=False)


class EstadoLicitacion(Base):
    """Catálogo de estados posibles de una licitación."""

    __tablename__ = "estados_licitacion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(Integer, unique=True, nullable=False)
    descripcion = Column(String(100), nullable=False)


class Configuracion(Base):
    """Configuración clave-valor de la aplicación (piloto automático, etc.)."""

    __tablename__ = "configuracion"

    clave = Column(String(50), primary_key=True, nullable=False)
    valor = Column(Text, nullable=True)
    fecha_actualizacion = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=True
    )
