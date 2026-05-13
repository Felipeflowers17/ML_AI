"""ScoringWorker — QThread que recalcula scores de licitaciones activas en pipeline.

Carga las reglas activas desde el repositorio, las mapea a ReglaScoring,
recarga el gestor de reglas, evalúa cada licitación activa y actualiza
sus scores en la base de datos.
"""

from typing import List

from PySide6.QtCore import QThread, Signal

from monitor_licitaciones.config import (
    CODIGO_ESTADO_PUBLICADA,
    ETAPAS_ACTIVAS,
)
from monitor_licitaciones.domain.scoring.gestor_reglas import GestorReglas
from monitor_licitaciones.domain.scoring.motor_scoring import (
    evaluar_detalle,
    evaluar_titulo,
)
from monitor_licitaciones.domain.scoring.tipos import ReglaScoring
from monitor_licitaciones.infrastructure.database.repositorio_licitaciones import (
    RepositorioLicitaciones,
)
from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
    RepositorioReglas,
)
from monitor_licitaciones.workers import mapear_reglas


class ScoringWorker(QThread):
    """Worker que recalcula scores de licitaciones activas en pipeline.

    Signals:
        progreso: Mensaje de estado para el log visual.
        avance: (procesadas, total) para barra de progreso.
        finalizado: Recálculo completado — la UI recarga las 3 pestañas.
        error: Fallo con mensaje descriptivo.
    """

    progreso = Signal(str)
    avance = Signal(int, int)
    finalizado = Signal()
    error = Signal(str)

    def __init__(
        self,
        repo_licitaciones: RepositorioLicitaciones,
        repo_reglas: RepositorioReglas,
        gestor_reglas: GestorReglas,
    ) -> None:
        super().__init__()
        self._repo_licitaciones = repo_licitaciones
        self._repo_reglas = repo_reglas
        self._gestor_reglas = gestor_reglas

    def run(self) -> None:
        """Ejecuta el recálculo de scores en un hilo separado."""
        try:
            # 1. Cargar y mapear reglas
            palabras = self._repo_reglas.obtener_palabras_clave()
            reglas: List[ReglaScoring] = mapear_reglas(palabras)

            # 2. Recargar gestor con las nuevas reglas
            self._gestor_reglas.recargar(reglas)

            # 3. Obtener licitaciones activas en pipeline
            licitaciones = self._repo_licitaciones.obtener_activas_en_pipeline(
                ETAPAS_ACTIVAS, CODIGO_ESTADO_PUBLICADA
            )

            # 4. Cargar puntajes de organismos una vez
            organismos = {
                org.codigo: org.puntaje_fijo
                for org in self._repo_reglas.obtener_organismos()
            }

            total = len(licitaciones)

            # 5. Evaluar cada licitación
            for i, lic in enumerate(licitaciones):
                snapshot = self._gestor_reglas.obtener_snapshot()

                score_resumen, motivos_resumen = evaluar_titulo(
                    lic.nombre, snapshot
                )
                score_detalle, motivos_detalle = evaluar_detalle(
                    lic.descripcion, lic.detalle_productos or "", snapshot
                )

                puntaje_org = organismos.get(lic.codigo_organismo or "", 0)
                score_total = score_resumen + score_detalle + puntaje_org

                justificacion = "; ".join(motivos_resumen + motivos_detalle)

                self._repo_licitaciones.actualizar_score(
                    codigo_externo=lic.codigo_externo,
                    score_resumen=score_resumen,
                    score_detalle=score_detalle,
                    score_total=score_total,
                    justificacion=justificacion,
                )

                if (i + 1) % 25 == 0:
                    self.avance.emit(i + 1, total)

            # 6. Emitir finalizado
            self.finalizado.emit()

        except Exception as e:
            self.error.emit(str(e))
