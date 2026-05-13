"""Lógica de transiciones válidas entre etapas del pipeline.

Define las reglas de navegación del pipeline de licitaciones:
- candidata ↔ seguimiento ↔ ofertada (movimiento libre entre activas)
- ignorada → candidata (solo se puede ascender desde ignorada)
"""

from typing import List

TRANSICIONES_VALIDAS: dict[str, List[str]] = {
    "candidata": ["seguimiento", "ofertada"],
    "seguimiento": ["candidata", "ofertada"],
    "ofertada": ["candidata", "seguimiento"],
    "ignorada": ["candidata"],
}


class GestorPipeline:
    """Valida y consulta transiciones entre etapas del pipeline."""

    @staticmethod
    def es_transicion_valida(origen: str, destino: str) -> bool:
        """Retorna True si la transición origen → destino está permitida."""
        return destino in TRANSICIONES_VALIDAS.get(origen, [])

    @staticmethod
    def destinos_disponibles(etapa_actual: str) -> List[str]:
        """Retorna lista de etapas a las que se puede mover desde etapa_actual."""
        return TRANSICIONES_VALIDAS.get(etapa_actual, [])
