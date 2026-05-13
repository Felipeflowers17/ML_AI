"""Modelos Pydantic para validación de respuestas de la API de Mercado Público.

Todos los campos opcionales tienen ``default=None`` o ``default_factory``
porque la API gubernamental puede omitir campos sin previo aviso.
Nunca lanzar ``ValidationError`` por campos faltantes, solo por tipos
incompatibles en campos presentes.
"""

from typing import Optional

from pydantic import BaseModel, Field


class OrganismoAPI(BaseModel):
    """Organismo comprador en respuestas de la API."""

    CodigoOrganismo: str
    NombreOrganismo: str


class ItemAPI(BaseModel):
    """Ítem dentro del detalle de una licitación."""

    NombreProducto: str = ""
    Cantidad: float = 0
    UnidadMedida: str = ""
    Descripcion: str = ""


class LicitacionResumenAPI(BaseModel):
    """Modelo para cada elemento del listado diario."""

    CodigoExterno: str
    Nombre: str
    FechaCierre: Optional[str] = None
    CodigoEstado: Optional[int] = None
    Comprador: Optional[OrganismoAPI] = None


class LicitacionDetalleAPI(BaseModel):
    """Modelo para la respuesta de detalle individual."""

    CodigoExterno: str
    Nombre: str
    Descripcion: Optional[str] = None
    FechaCierre: Optional[str] = None
    FechaInicio: Optional[str] = None
    FechaPublicacion: Optional[str] = None
    CodigoEstado: Optional[int] = None
    Comprador: Optional[OrganismoAPI] = None
    Items: Optional[dict] = None  # estructura variable según la licitación


class RespuestaListadoAPI(BaseModel):
    """Envelope de la respuesta del listado diario."""

    Cantidad: int = 0
    Listado: list[LicitacionResumenAPI] = Field(default_factory=list)
