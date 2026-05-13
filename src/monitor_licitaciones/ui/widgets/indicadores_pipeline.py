"""IndicadoresPipeline — Contadores visibles de licitaciones por etapa.

Muestra tres etiquetas con la cantidad de licitaciones en cada etapa activa
del pipeline: Candidatas, Seguimiento y Ofertadas. Se actualiza mediante
llamadas a ``actualizar()`` que consulta el repositorio.
"""

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class IndicadoresPipeline(QWidget):
    """Widget con tres labels de conteo por etapa del pipeline.

    Los labels muestran cero por defecto, nunca texto vacío.
    Se actualiza vía ``actualizar()`` que llama a
    ``repo_licitaciones.contar_por_etapa()``.
    """

    def __init__(self, repo_licitaciones, parent=None):
        super().__init__(parent)
        self._repo = repo_licitaciones

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._lbl_candidatas = QLabel("Candidatas (0)")
        self._lbl_seguimiento = QLabel("Seguimiento (0)")
        self._lbl_ofertadas = QLabel("Ofertadas (0)")

        for lbl in [
            self._lbl_candidatas,
            self._lbl_seguimiento,
            self._lbl_ofertadas,
        ]:
            lbl.setStyleSheet("font-weight: bold; padding: 4px 8px;")
            layout.addWidget(lbl)

    def actualizar(self):
        """Actualiza los contadores desde el repositorio.

        Si el repositorio es ``None`` (modo test sin BD), no hace nada.
        """
        if self._repo is None:
            return

        conteos = self._repo.contar_por_etapa()

        self._lbl_candidatas.setText(
            f"Candidatas ({conteos.get('candidata', 0)})"
        )
        self._lbl_seguimiento.setText(
            f"Seguimiento ({conteos.get('seguimiento', 0)})"
        )
        self._lbl_ofertadas.setText(
            f"Ofertadas ({conteos.get('ofertada', 0)})"
        )
