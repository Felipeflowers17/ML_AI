"""Gestor thread-safe del estado compartido de reglas de scoring.

Administra una lista de ReglaScoring con acceso sincronizado mediante
threading.Lock. El lock NUNCA se mantiene durante la evaluación léxica:
el snapshot se obtiene antes de llamar al motor y se pasa como parámetro.
"""

import threading
from typing import List

from monitor_licitaciones.domain.scoring.tipos import ReglaScoring


class GestorReglas:
    """Gestor thread-safe de reglas de scoring.

    El patrón de uso es:
        1. Workers cargan reglas desde BD y llaman a recargar()
        2. Antes de evaluar, llaman a obtener_snapshot()
        3. Pasan el snapshot al motor de scoring (función pura, sin locks)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reglas: List[ReglaScoring] = []

    def recargar(self, reglas: List[ReglaScoring]) -> None:
        """Reemplaza todas las reglas con una nueva lista (copia defensiva)."""
        with self._lock:
            self._reglas = list(reglas)

    def obtener_snapshot(self) -> List[ReglaScoring]:
        """Retorna una copia del estado actual (thread-safe)."""
        with self._lock:
            return list(self._reglas)
