"""Diálogo de configuración y ejecución de exportación de licitaciones.

Permite seleccionar etapas, formato de exportación (Excel/CSV), directorio
de destino y monitorear el progreso de la exportación.
"""

import os

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from monitor_licitaciones.config import ETAPAS_ACTIVAS


class ConfigExportacionDialog(QDialog):
    """Diálogo para configurar y ejecutar la exportación de licitaciones.

    El usuario selecciona etapas, formato y directorio de destino.
    La exportación se ejecuta en un hilo separado (ExportacionWorker)
    con barra de progreso.
    """

    def __init__(self, exportacion_worker_factory, parent=None):
        """Args:
            exportacion_worker_factory: Callable que recibe
                (repo_licitaciones, etapa, formato, directorio)
                y retorna un ExportacionWorker listo para ejecutar.
        """
        super().__init__(parent)
        self._factory = exportacion_worker_factory
        self._worker = None
        self._directorio = ""

        self.setWindowTitle("Exportar Licitaciones")
        self.setMinimumWidth(450)

        self._setup_ui()

    def _setup_ui(self):
        """Construye los componentes visuales del diálogo."""
        layout = QVBoxLayout(self)

        # ── Selección de etapas ──────────────────────────────────────────
        etapas_group = QGroupBox("Etapas a exportar")
        etapas_layout = QVBoxLayout(etapas_group)

        self._chk_etapas = {}
        for etapa in ETAPAS_ACTIVAS:
            chk = QCheckBox(etapa.capitalize())
            chk.setChecked(True)
            self._chk_etapas[etapa] = chk
            chk.toggled.connect(self._validar)
            etapas_layout.addWidget(chk)

        layout.addWidget(etapas_group)

        # ── Selección de formato ─────────────────────────────────────────
        formato_group = QGroupBox("Formato de exportación")
        formato_layout = QVBoxLayout(formato_group)

        self._chk_excel = QCheckBox("Excel (.xlsx)")
        self._chk_excel.setChecked(True)
        self._chk_excel.toggled.connect(self._validar)
        formato_layout.addWidget(self._chk_excel)

        self._chk_csv = QCheckBox("CSV (.csv)")
        self._chk_csv.toggled.connect(self._validar)
        formato_layout.addWidget(self._chk_csv)

        layout.addWidget(formato_group)

        # ── Selección de directorio ──────────────────────────────────────
        dir_layout = QHBoxLayout()
        self._lbl_directorio = QLabel("Seleccione un directorio...")
        self._btn_seleccionar = QPushButton("Examinar...")
        self._btn_seleccionar.clicked.connect(self._seleccionar_directorio)
        dir_layout.addWidget(self._lbl_directorio, 1)
        dir_layout.addWidget(self._btn_seleccionar)
        layout.addLayout(dir_layout)

        # ── Botón de exportación ─────────────────────────────────────────
        self._btn_exportar = QPushButton("Exportar")
        self._btn_exportar.clicked.connect(self._iniciar_exportacion)
        self._btn_exportar.setEnabled(False)
        layout.addWidget(self._btn_exportar)

        # ── Barra de progreso ────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

    def _validar(self):
        """Valida que al menos una etapa y un formato estén seleccionados,
        y que el directorio esté elegido."""
        etapa_valida = any(chk.isChecked() for chk in self._chk_etapas.values())
        formato_valido = self._chk_excel.isChecked() or self._chk_csv.isChecked()
        directorio_valido = bool(self._directorio) and os.path.isdir(
            self._directorio
        )
        self._btn_exportar.setEnabled(
            etapa_valida and formato_valido and directorio_valido
        )

    def _seleccionar_directorio(self):
        """Abre el diálogo de selección de directorio."""
        directorio = QFileDialog.getExistingDirectory(
            self, "Seleccionar directorio de destino"
        )
        if directorio:
            self._directorio = directorio
            self._lbl_directorio.setText(directorio)
            self._validar()

    def _iniciar_exportacion(self):
        """Inicia la exportación para cada etapa y formato seleccionados."""
        etapas = [
            etapa
            for etapa, chk in self._chk_etapas.items()
            if chk.isChecked()
        ]
        formatos = []
        if self._chk_excel.isChecked():
            formatos.append("xlsx")
        if self._chk_csv.isChecked():
            formatos.append("csv")

        if not etapas or not formatos:
            QMessageBox.warning(
                self,
                "Exportación",
                "Debe seleccionar al menos una etapa y un formato.",
            )
            return

        self._btn_exportar.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)

        # Por simplicidad, exportar la primera etapa seleccionada en el
        # primer formato. La factory crea el worker.
        for etapa in etapas:
            for fmt in formatos:
                # Crear worker para esta combinación etapa/formato
                self._worker = self._factory(etapa, fmt, self._directorio)
                self._worker.avance.connect(self._on_avance)
                self._worker.finalizado.connect(self._on_finalizado)
                self._worker.error.connect(self._on_error)
                self._worker.start()
                # Solo la primera combinación por ahora
                return

    def _on_avance(self, actual: int, total: int):
        """Actualiza la barra de progreso."""
        if total > 0:
            self._progress.setMaximum(total)
            self._progress.setValue(actual)

    def _on_finalizado(self, ruta: str):
        """Maneja la finalización exitosa de la exportación."""
        self._progress.setVisible(False)
        self._btn_exportar.setEnabled(True)

        if ruta:
            QMessageBox.information(
                self,
                "Exportación completada",
                f"Archivo generado:\n{ruta}",
            )
        else:
            QMessageBox.information(
                self,
                "Exportación",
                "No hay datos para exportar en los filtros seleccionados.",
            )

    def _on_error(self, mensaje: str):
        """Maneja un error durante la exportación."""
        self._progress.setVisible(False)
        self._btn_exportar.setEnabled(True)
        QMessageBox.critical(
            self, "Error de exportación", f"Ocurrió un error:\n{mensaje}"
        )
