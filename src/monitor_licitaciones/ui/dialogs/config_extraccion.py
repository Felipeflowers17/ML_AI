"""Diálogo de configuración y ejecución de extracción de licitaciones.

Permite seleccionar un rango de fechas, iniciar la extracción con barra de
progreso y log visual, y cancelar una extracción en curso.
"""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class ConfigExtraccionDialog(QDialog):
    """Diálogo para configurar y ejecutar la extracción de licitaciones.

    El usuario selecciona un rango de fechas, inicia la extracción en un
    hilo separado (ExtraccionWorker) y puede monitorear el progreso mediante
    la barra de progreso y el área de log.
    """

    def __init__(self, extraccion_worker, parent=None):
        super().__init__(parent)
        self._worker = extraccion_worker
        self._en_ejecucion = False

        self.setWindowTitle("Extracción de Licitaciones")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._setup_ui()

    def _setup_ui(self):
        """Construye los componentes visuales del diálogo."""
        layout = QVBoxLayout(self)

        # ── Selector de fechas ───────────────────────────────────────────
        fechas_layout = QHBoxLayout()
        fechas_layout.addWidget(QLabel("Fecha inicio:"))
        self._date_inicio = QDateEdit()
        self._date_inicio.setCalendarPopup(True)
        self._date_inicio.setDate(QDate.currentDate().addDays(-7))
        self._date_inicio.dateChanged.connect(self._validar_fechas)
        fechas_layout.addWidget(self._date_inicio)

        fechas_layout.addWidget(QLabel("Fecha fin:"))
        self._date_fin = QDateEdit()
        self._date_fin.setCalendarPopup(True)
        self._date_fin.setDate(QDate.currentDate())
        self._date_fin.dateChanged.connect(self._validar_fechas)
        fechas_layout.addWidget(self._date_fin)

        self._lbl_error_fechas = QLabel("")
        self._lbl_error_fechas.setStyleSheet("color: red;")
        self._lbl_error_fechas.setVisible(False)

        layout.addLayout(fechas_layout)
        layout.addWidget(self._lbl_error_fechas)

        # ── Botones de control ───────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self._btn_iniciar = QPushButton("Iniciar Extracción")
        self._btn_iniciar.clicked.connect(self._iniciar_extraccion)

        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.clicked.connect(self._cancelar_extraccion)
        self._btn_cancelar.setVisible(False)

        btn_layout.addWidget(self._btn_iniciar)
        btn_layout.addWidget(self._btn_cancelar)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # ── Barra de progreso ───────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ── Área de log ──────────────────────────────────────────────────
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log)

    def _validar_fechas(self):
        """Valida que fecha inicio <= fecha fin."""
        if self._date_inicio.date() > self._date_fin.date():
            self._lbl_error_fechas.setText(
                "La fecha de inicio no puede ser posterior a la fecha fin."
            )
            self._lbl_error_fechas.setVisible(True)
            self._btn_iniciar.setEnabled(False)
        else:
            self._lbl_error_fechas.setVisible(False)
            self._btn_iniciar.setEnabled(True)

    def _iniciar_extraccion(self):
        """Configura el worker y lanza la extracción."""
        fecha_inicio = self._date_inicio.date().toString("yyyy-MM-dd")
        fecha_fin = self._date_fin.date().toString("yyyy-MM-dd")

        if fecha_inicio > fecha_fin:
            QMessageBox.warning(
                self, "Fechas inválidas", self._lbl_error_fechas.text()
            )
            return

        self._en_ejecucion = True
        self._btn_iniciar.setVisible(False)
        self._btn_cancelar.setVisible(True)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._log.clear()

        # Configurar fechas en el worker
        self._worker._fecha_inicio = fecha_inicio
        self._worker._fecha_fin = fecha_fin

        # Conectar señales
        self._worker.progreso.connect(self._on_progreso)
        self._worker.avance.connect(self._on_avance)
        self._worker.finalizado.connect(self._on_finalizado)
        self._worker.error.connect(self._on_error)

        # Iniciar worker
        self._worker.start()

    def _cancelar_extraccion(self):
        """Detiene la extracción en curso."""
        self._worker.detener()
        self._log.append("Extracción cancelada por el usuario.")
        self._finalizar()

    def _on_progreso(self, mensaje: str):
        """Recibe mensajes de progreso del worker."""
        self._log.append(mensaje)

    def _on_avance(self, procesadas: int, total: int):
        """Actualiza la barra de progreso."""
        if total > 0:
            self._progress.setMaximum(total)
            self._progress.setValue(procesadas)
        self._log.append(f"  Procesadas: {procesadas}/{total}")

    def _on_finalizado(self):
        """Maneja la finalización exitosa de la extracción."""
        self._log.append("Extracción completada.")
        self._finalizar()

    def _on_error(self, mensaje: str):
        """Maneja un error durante la extracción."""
        self._log.append(f"ERROR: {mensaje}")
        self._finalizar()

    def _finalizar(self):
        """Restaura la UI al estado inicial post-ejecución."""
        self._en_ejecucion = False
        self._btn_iniciar.setVisible(True)
        self._btn_cancelar.setVisible(False)
        self._progress.setVisible(False)

        # Desconectar señales para evitar múltiples conexiones
        try:
            self._worker.progreso.disconnect(self._on_progreso)
            self._worker.avance.disconnect(self._on_avance)
            self._worker.finalizado.disconnect(self._on_finalizado)
            self._worker.error.disconnect(self._on_error)
        except (TypeError, RuntimeError):
            pass
