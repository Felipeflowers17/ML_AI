"""ExtraccionWorker — QThread que extrae licitaciones desde la API de Mercado Público.

Procesa un rango de fechas día por día, evalúa el título de cada licitación
contra las reglas de scoring, descarga detalle solo si hay coincidencia
positiva, y persiste los resultados en la base de datos.
"""

from datetime import datetime, timedelta
from typing import Any, List

from PySide6.QtCore import QThread, Signal

from monitor_licitaciones.domain.scoring.gestor_reglas import GestorReglas
from monitor_licitaciones.domain.scoring.motor_scoring import (
    evaluar_detalle,
    evaluar_titulo,
)
from monitor_licitaciones.domain.scoring.tipos import ReglaScoring
from monitor_licitaciones.infrastructure.api.cliente_mp import ClienteAPI
from monitor_licitaciones.infrastructure.database.repositorio_licitaciones import (
    RepositorioLicitaciones,
)
from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
    RepositorioReglas,
)


def _parsear_fecha_api(valor: Any) -> datetime | None:
    """Convierte un string de fecha de la API a ``datetime`` o ``None``.

    La API de Mercado Público retorna fechas en formato ISO 8601.
    Si el valor es ``None`` o inválido, retorna ``None`` sin lanzar
    excepción.
    """
    if not valor or not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor)
    except (ValueError, TypeError):
        return None


class ExtraccionWorker(QThread):
    """Worker que extrae licitaciones día por día desde la API.

    Signals:
        progreso: Mensaje de estado para el log visual.
        avance: (procesadas, total_del_dia) para barra de progreso.
        finalizado: Extracción completada con éxito.
        error: Fallo con mensaje descriptivo.
    """

    progreso = Signal(str)
    avance = Signal(int, int)
    finalizado = Signal()
    error = Signal(str)

    def __init__(
        self,
        fecha_inicio: str,
        fecha_fin: str,
        cliente_mp: ClienteAPI,
        repo_licitaciones: RepositorioLicitaciones,
        repo_reglas: RepositorioReglas,
        gestor_reglas: GestorReglas,
    ) -> None:
        super().__init__()
        self._fecha_inicio = fecha_inicio
        self._fecha_fin = fecha_fin
        self._cliente_mp = cliente_mp
        self._repo_licitaciones = repo_licitaciones
        self._repo_reglas = repo_reglas
        self._gestor_reglas = gestor_reglas
        self._ejecutando = True

    def run(self) -> None:
        """Ejecuta la extracción día por día en un hilo separado."""
        # 1. Cargar snapshot de reglas al inicio
        snapshot: List[ReglaScoring] = self._gestor_reglas.obtener_snapshot()

        # 2. Cargar caché de organismos una vez
        organismos = {
            org.codigo: org.puntaje_fijo
            for org in self._repo_reglas.obtener_organismos()
        }

        # 3. Parsear fechas
        fecha_actual = datetime.strptime(self._fecha_inicio, "%Y-%m-%d").date()
        fecha_fin = datetime.strptime(self._fecha_fin, "%Y-%m-%d").date()

        while fecha_actual <= fecha_fin:
            if not self._ejecutando:
                return

            fecha_str = fecha_actual.strftime("%d%m%Y")
            self.progreso.emit(f"Procesando día {fecha_str}...")

            try:
                licitaciones = self._cliente_mp.obtener_licitaciones_dia(fecha_str)
            except Exception as e:
                self.error.emit(str(e))
                fecha_actual += timedelta(days=1)
                continue

            total_dia = len(licitaciones)
            procesadas = 0

            for lic in licitaciones:
                codigo = lic.get("CodigoExterno", "")
                nombre = lic.get("Nombre", "")

                # Evaluar título
                score_resumen, motivos_resumen = evaluar_titulo(nombre, snapshot)

                if score_resumen > 0:
                    # Descargar detalle solo si hay coincidencia positiva
                    detalle = self._cliente_mp.obtener_detalle(codigo)
                    if detalle:
                        descripcion = detalle.get("Descripcion") or ""
                        items = detalle.get("Items") or {}
                        productos_str = (
                            " ".join(str(v) for v in items.values())
                            if isinstance(items, dict)
                            else str(items) if items else ""
                        )

                        score_detalle, motivos_detalle = evaluar_detalle(
                            descripcion, productos_str, snapshot
                        )

                        codigo_org = (
                            detalle.get("Comprador", {}).get("CodigoOrganismo", "")
                            if isinstance(detalle.get("Comprador"), dict)
                            else ""
                        )
                        puntaje_org = organismos.get(codigo_org, 0)
                        score_total = score_resumen + score_detalle + puntaje_org

                        fecha_publicacion = _parsear_fecha_api(
                            detalle.get("FechaPublicacion")
                        )

                        datos = {
                            "codigo_externo": codigo,
                            "nombre": nombre,
                            "descripcion": descripcion,
                            "detalle_productos": productos_str,
                            "fecha_publicacion": fecha_publicacion,
                            "score_resumen": score_resumen,
                            "score_detalle": score_detalle,
                            "score_total": score_total,
                            "justificacion_score": "; ".join(
                                motivos_resumen + motivos_detalle
                            ),
                            "etapa": "candidata",
                            "tiene_detalle": True,
                        }
                    else:
                        # Detalle no encontrado, persistir solo con score de título
                        datos = {
                            "codigo_externo": codigo,
                            "nombre": nombre,
                            "score_resumen": score_resumen,
                            "score_total": score_resumen,
                            "justificacion_score": "; ".join(motivos_resumen),
                            "etapa": "candidata",
                            "tiene_detalle": False,
                            "fecha_publicacion": None,
                        }
                else:
                    # Sin coincidencia en título — ignorar
                    datos = {
                        "codigo_externo": codigo,
                        "nombre": nombre,
                        "score_resumen": 0,
                        "score_total": 0,
                        "etapa": "ignorada",
                        "tiene_detalle": False,
                        "fecha_publicacion": None,
                    }

                self._repo_licitaciones.upsert(datos)
                procesadas += 1

                if procesadas % 10 == 0:
                    self.avance.emit(procesadas, total_dia)

            fecha_actual += timedelta(days=1)

        self.finalizado.emit()

    def detener(self) -> None:
        """Solicita la detención del worker de forma cooperativa."""
        self._ejecutando = False
