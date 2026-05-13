"""PilotoWorker — QThread de ejecución automática programada.

El piloto automático sobrevive reinicios de la app y se ejecuta de forma
confiable a una hora configurada, con reintentos ante fallos, sin bloquear
la UI. Lee la configuración de BD en cada ciclo de 60 segundos, por lo
que la UI no necesita reiniciar el worker al cambiar la configuración.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from PySide6.QtCore import QThread, Signal

from monitor_licitaciones.config import (
    PILOTO_ACTIVO,
    PILOTO_HORA,
    PILOTO_HORA_DEFAULT,
    PILOTO_ULTIMA_EJECUCION,
    PILOTO_ULTIMO_ERROR,
)
from monitor_licitaciones.domain.scoring.gestor_reglas import GestorReglas
from monitor_licitaciones.infrastructure.api.cliente_mp import ClienteAPI
from monitor_licitaciones.infrastructure.database.repositorio_configuracion import (
    RepositorioConfiguracion,
)
from monitor_licitaciones.infrastructure.database.repositorio_licitaciones import (
    RepositorioLicitaciones,
)
from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
    RepositorioReglas,
)


class PilotoWorker(QThread):
    """Worker de ejecución automática programada.

    Ciclo de vida:
    1. Al iniciar: lee configuración desde BD.
    2. Entra en loop: duerme 60 segundos, despierta, evalúa condición.
    3. Si es la hora Y no ejecutó hoy: lanza extracción.
    4. Si éxito: persiste fecha en BD, emite extraccion_completada.
    5. Si falla: reintenta x3 con backoff 5/10/20 minutos.
    6. Si agota reintentos: persiste error en BD, emite error_ocurrido.

    Signals:
        estado_cambiado: Texto descriptivo para label de estado.
        extraccion_iniciada: Extracción automática comenzó.
        extraccion_completada: Extracción automática finalizó con éxito.
        error_ocurrido: Ocurrió un error tras agotar reintentos.
    """

    estado_cambiado = Signal(str)
    extraccion_iniciada = Signal()
    extraccion_completada = Signal()
    error_ocurrido = Signal(str)

    def __init__(
        self,
        repo_config: RepositorioConfiguracion,
        cliente_mp: ClienteAPI | None = None,
        repo_licitaciones: RepositorioLicitaciones | None = None,
        repo_reglas: RepositorioReglas | None = None,
        gestor_reglas: GestorReglas | None = None,
    ) -> None:
        super().__init__()
        self._repo_config = repo_config
        self._cliente_mp = cliente_mp
        self._repo_licitaciones = repo_licitaciones
        self._repo_reglas = repo_reglas
        self._gestor_reglas = gestor_reglas
        self._ejecutando = True

    def run(self) -> None:
        """Loop principal del piloto automático."""
        self.estado_cambiado.emit("Piloto iniciado")

        while self._ejecutando:
            self._iterar_ciclo()
            self._sleep_interrumpible(60)

    def _iterar_ciclo(self) -> None:
        """Ejecuta un ciclo de evaluación sin dormir (testeable)."""
        config = self._repo_config.obtener_todas()
        activo = config.get(PILOTO_ACTIVO) == "true"
        hora = config.get(PILOTO_HORA) or PILOTO_HORA_DEFAULT
        ultima = config.get(PILOTO_ULTIMA_EJECUCION)
        ahora = datetime.now()

        if activo and self._es_hora(ahora, hora):
            if str(ahora.date()) != ultima:
                self._ejecutar_con_reintentos(ahora)

    def _es_hora(self, ahora: datetime, hora_str: str) -> bool:
        """Verifica si la hora actual coincide con la hora configurada.

        Compara en formato HH:MM. Retorna True si la diferencia es
        menor a 60 segundos para no perderse la ventana de ejecución.
        """
        try:
            hora_config = datetime.strptime(hora_str, "%H:%M").time()
            hora_actual = ahora.time()
            # Comparar solo horas y minutos
            diff_minutos = (
                (hora_actual.hour - hora_config.hour) * 60
                + (hora_actual.minute - hora_config.minute)
            )
            return 0 <= diff_minutos < 1
        except (ValueError, TypeError):
            return False

    def _ejecutar_con_reintentos(
        self,
        ahora: datetime,
        extraccion_fn: Optional[Callable[[], None]] = None,
    ) -> None:
        """Ejecuta la extracción con backoff de 5, 10 y 20 minutos.

        Args:
            ahora: Momento de la ejecución para persistir la fecha.
            extraccion_fn: Función de extracción a ejecutar
                (sobreescribible para tests).
        """
        # Backoff en segundos: 5min, 10min, 20min
        backoffs = [300, 600, 1200]
        ultimo_error = ""

        for intento, backoff in enumerate(backoffs):
            if not self._ejecutando:
                return

            self.estado_cambiado.emit(
                f"Ejecutando extracción (intento {intento + 1}/3)..."
            )
            self.extraccion_iniciada.emit()

            try:
                if extraccion_fn:
                    extraccion_fn()
                else:
                    self._ejecutar_extraccion_real()
                # Éxito
                self._repo_config.guardar(
                    PILOTO_ULTIMA_EJECUCION, str(ahora.date())
                )
                self.estado_cambiado.emit("Extracción completada")
                self.extraccion_completada.emit()
                return

            except Exception as e:
                ultimo_error = str(e)
                if intento < len(backoffs) - 1 and self._ejecutando:
                    self.estado_cambiado.emit(
                        f"Error (intento {intento + 1}/3), reintentando "
                        f"en {backoff // 60} minutos..."
                    )
                    self._sleep_interrumpible(backoff)

        # Agotó reintentos
        self._repo_config.guardar(PILOTO_ULTIMO_ERROR, ultimo_error)
        self.estado_cambiado.emit(f"Error: {ultimo_error}")
        self.error_ocurrido.emit(ultimo_error)

    def _ejecutar_extraccion_real(self) -> None:
        """Ejecuta la extracción real para el día anterior.

        Crea un ``ExtraccionWorker`` con las dependencias inyectadas y
        ejecuta ``run()`` de forma síncrona dentro del hilo del piloto.
        Si faltan dependencias, lanza ``RuntimeError`` que es capturado
        por el mecanismo de reintentos en ``_ejecutar_con_reintentos``.
        """
        # Validar dependencias
        if not all([
            self._cliente_mp,
            self._repo_licitaciones,
            self._repo_reglas,
            self._gestor_reglas,
        ]):
            raise RuntimeError(
                "PilotoWorker no tiene todas las dependencias para "
                "ejecutar extracción real. Inyecte cliente_mp, "
                "repo_licitaciones, repo_reglas y gestor_reglas."
            )

        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        worker = ExtraccionWorker(
            fecha_inicio=ayer,
            fecha_fin=ayer,
            cliente_mp=self._cliente_mp,
            repo_licitaciones=self._repo_licitaciones,
            repo_reglas=self._repo_reglas,
            gestor_reglas=self._gestor_reglas,
        )
        # Ejecución síncrona dentro del hilo del piloto
        worker.run()

    def _sleep_interrumpible(self, segundos: int) -> None:
        """Duerme en intervalos de 1 segundo para permitir detener().

        Verifica self._ejecutando en cada iteración para responder
        rápidamente a detener().
        """
        for _ in range(segundos):
            if not self._ejecutando:
                break
            time.sleep(1)

    def detener(self) -> None:
        """Solicita la detención del worker de forma cooperativa."""
        self._ejecutando = False
