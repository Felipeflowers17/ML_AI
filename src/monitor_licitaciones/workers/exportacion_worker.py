"""ExportacionWorker — QThread para exportación en Excel/CSV con paginación.

Procesa licitaciones en chunks de EXPORT_CHUNK_SIZE usando paginación del
repositorio. Soporta formato CSV (append mode) y Excel (acumula DataFrames).
Limpia zonas horarias en columnas datetime antes de escribir.
"""

import math
import os
from datetime import datetime
from typing import List

import pandas as pd
from PySide6.QtCore import QThread, Signal

from monitor_licitaciones.config import EXPORT_CHUNK_SIZE
from monitor_licitaciones.infrastructure.database.models import Licitacion
from monitor_licitaciones.infrastructure.database.repositorio_licitaciones import (
    RepositorioLicitaciones,
)

# Columnas a exportar (orden y nombres)
COLUMNAS_EXPORTACION = [
    "score_total",
    "codigo_externo",
    "nombre",
    "descripcion",
    "etapa",
    "fecha_publicacion",
    "fecha_cierre",
    "codigo_organismo",
    "justificacion_score",
]


class ExportacionWorker(QThread):
    """Worker que exporta licitaciones a Excel o CSV.

    Signals:
        avance: (chunks procesados, chunks totales) para barra de progreso.
        finalizado: Exportación completada — emite la ruta del archivo.
        error: Fallo con mensaje descriptivo.
    """

    avance = Signal(int, int)
    finalizado = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        repo_licitaciones: RepositorioLicitaciones,
        etapa: str,
        formato: str,
        directorio: str,
    ) -> None:
        super().__init__()
        self._repo_licitaciones = repo_licitaciones
        self._etapa = etapa
        self._formato = formato.lower()  # "csv" o "xlsx"
        self._directorio = directorio

    def run(self) -> None:
        """Ejecuta la exportación en un hilo separado."""
        try:
            # Contar total de registros
            total = self._repo_licitaciones.contar_por_etapa().get(self._etapa, 0)
            if total == 0:
                # No hay datos para exportar
                self.finalizado.emit("")
                return

            chunks_totales = math.ceil(total / EXPORT_CHUNK_SIZE)

            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"Reporte_{self._etapa}_{timestamp}.{self._formato}"
            filepath = os.path.join(self._directorio, filename)

            if self._formato == "csv":
                self._exportar_csv(filepath, chunks_totales)
            else:
                self._exportar_excel(filepath, chunks_totales)

            self.finalizado.emit(filepath)

        except Exception as e:
            self.error.emit(str(e))

    def _exportar_csv(self, filepath: str, chunks_totales: int) -> None:
        """Exporta a CSV en modo append, cabecera solo en el primer chunk."""
        for pagina in range(chunks_totales):
            licitaciones = self._repo_licitaciones.obtener_por_etapa(
                self._etapa, pagina=pagina, por_pagina=EXPORT_CHUNK_SIZE
            )

            df = self._licitaciones_a_dataframe(licitaciones)

            # CSV: cabecera solo en el primer chunk
            header = pagina == 0
            df.to_csv(
                filepath,
                mode="a",
                header=header,
                index=False,
                encoding="utf-8-sig",
            )

            self.avance.emit(pagina + 1, chunks_totales)

    def _exportar_excel(self, filepath: str, chunks_totales: int) -> None:
        """Exporta a Excel acumulando DataFrames y concatenando al final."""
        fragmentos: List[pd.DataFrame] = []

        for pagina in range(chunks_totales):
            licitaciones = self._repo_licitaciones.obtener_por_etapa(
                self._etapa, pagina=pagina, por_pagina=EXPORT_CHUNK_SIZE
            )

            df = self._licitaciones_a_dataframe(licitaciones)
            fragmentos.append(df)

            self.avance.emit(pagina + 1, chunks_totales)

        if fragmentos:
            df_final = pd.concat(fragmentos, ignore_index=True)
            df_final.to_excel(filepath, index=False, engine="openpyxl")

    def _licitaciones_a_dataframe(
        self, licitaciones: List[Licitacion]
    ) -> pd.DataFrame:
        """Convierte una lista de licitaciones a DataFrame.

        Selecciona solo las columnas definidas en COLUMNAS_EXPORTACION
        y limpia zonas horarias en columnas datetime.
        """
        registros = []
        for lic in licitaciones:
            registro = {}
            for col in COLUMNAS_EXPORTACION:
                valor = getattr(lic, col, None)
                registro[col] = valor
            registros.append(registro)

        df = pd.DataFrame(registros)

        # Limpiar zonas horarias en columnas datetime
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    df[col] = df[col].dt.tz_localize(None)
                except (TypeError, AttributeError):
                    pass

        return df
