"""Workers layer — QThread implementations for background tasks.

Los workers orquestan el trabajo entre capas. No implementan lógica de
negocio propia — delegan en el motor de scoring y en los repositorios.

La función ``mapear_reglas`` es el único punto de conversión entre la capa
de infraestructura (``PalabraClave``, modelo SQLAlchemy) y la capa de
dominio (``ReglaScoring``, TypedDict puro).
"""

from typing import List

from monitor_licitaciones.domain.scoring.tipos import ReglaScoring
from monitor_licitaciones.infrastructure.database.models import PalabraClave


def mapear_reglas(palabras: List[PalabraClave]) -> List[ReglaScoring]:
    """Convierte ``list[PalabraClave]`` a ``list[ReglaScoring]``.

    Solo incluye palabras clave activas. Esta función es el único punto
    de mapping entre la capa de infraestructura y la de dominio.
    """
    return [
        ReglaScoring(
            termino=p.termino,
            peso_titulo=p.peso_titulo,
            peso_descripcion=p.peso_descripcion,
            peso_productos=p.peso_productos,
        )
        for p in palabras
        if p.activa
    ]
