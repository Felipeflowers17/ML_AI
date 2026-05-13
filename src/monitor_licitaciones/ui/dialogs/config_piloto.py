"""Diálogo de configuración del piloto automático.

Permite activar/desactivar la ejecución programada, configurar la hora
de ejecución y visualizar el estado y última ejecución del piloto.
La configuración se persiste en BD mediante RepositorioConfiguracion.
"""

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)

from monitor_licitaciones.config import (
    PILOTO_ACTIVO,
    PILOTO_HORA,
    PILOTO_HORA_DEFAULT,
    PILOTO_ULTIMA_EJECUCION,
)


class ConfigPilotoDialog(QDialog):
    """Diálogo de configuración del piloto automático.

    Permite al usuario:
    - Activar/desactivar el piloto (persiste en BD)
    - Configurar la hora de ejecución (persiste en BD)
    - Ver el estado actual del piloto
    - Ver la última ejecución registrada
    """

    def __init__(self, repo_config, parent=None):
        super().__init__(parent)
        self._repo_config = repo_config

        self.setWindowTitle("Piloto Automático")
        self.setMinimumWidth(450)

        self._setup_ui()
        self._cargar_configuracion()

    def _setup_ui(self):
        """Construye los componentes visuales del diálogo."""
        layout = QVBoxLayout(self)

        # ── Selector de hora ─────────────────────────────────────────────
        form_layout = QFormLayout()
        self._time_edit = QTimeEdit()
        self._time_edit.setDisplayFormat("HH:mm")
        self._time_edit.setTime(QTime.fromString(PILOTO_HORA_DEFAULT, "HH:mm"))
        self._time_edit.timeChanged.connect(self._on_hora_cambiada)
        form_layout.addRow("Hora de ejecución:", self._time_edit)
        layout.addLayout(form_layout)

        # ── Texto informativo ChileCompra ────────────────────────────────
        self._lbl_recomendacion = QLabel(
            "ChileCompra recomienda ejecutar entre las 22:00 y las "
            "07:00 horas para mayor estabilidad de la API."
        )
        self._lbl_recomendacion.setStyleSheet(
            "color: #666; font-style: italic; padding: 8px 0;"
        )
        self._lbl_recomendacion.setWordWrap(True)
        layout.addWidget(self._lbl_recomendacion)

        # ── Botón toggle Activar/Desactivar ─────────────────────────────
        self._btn_toggle = QPushButton()
        self._btn_toggle.clicked.connect(self._on_toggle)
        layout.addWidget(self._btn_toggle)

        # ── Estado actual ───────────────────────────────────────────────
        estado_layout = QFormLayout()
        self._lbl_estado = QLabel("—")
        estado_layout.addRow("Estado:", self._lbl_estado)

        self._lbl_ultima_ejecucion = QLabel("—")
        estado_layout.addRow("Última ejecución:", self._lbl_ultima_ejecucion)
        layout.addLayout(estado_layout)

        # ── Botón cerrar ────────────────────────────────────────────────
        self._btn_cerrar = QPushButton("Cerrar")
        self._btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(self._btn_cerrar)

    def _cargar_configuracion(self):
        """Carga la configuración actual desde la BD."""
        activo = self._repo_config.obtener(PILOTO_ACTIVO) == "true"
        hora = self._repo_config.obtener(PILOTO_HORA) or PILOTO_HORA_DEFAULT
        ultima = self._repo_config.obtener(PILOTO_ULTIMA_EJECUCION)

        # Actualizar UI
        self._actualizar_boton(activo)
        self._time_edit.setTime(QTime.fromString(hora, "HH:mm"))
        self._lbl_ultima_ejecucion.setText(ultima or "Nunca")

    def _actualizar_boton(self, activo: bool):
        """Actualiza el texto y estilo del botón toggle."""
        if activo:
            self._btn_toggle.setText("Desactivar Piloto")
            self._btn_toggle.setStyleSheet(
                "background-color: #d32f2f; color: white; font-weight: bold;"
            )
            self._lbl_estado.setText("Activo")
            self._lbl_estado.setStyleSheet("color: green; font-weight: bold;")
        else:
            self._btn_toggle.setText("Activar Piloto")
            self._btn_toggle.setStyleSheet(
                "background-color: #388e3c; color: white; font-weight: bold;"
            )
            self._lbl_estado.setText("Inactivo")
            self._lbl_estado.setStyleSheet("color: gray;")

    def _on_toggle(self):
        """Maneja el clic en el botón de activar/desactivar."""
        activo = self._repo_config.obtener(PILOTO_ACTIVO) == "true"
        nuevo_valor = "false" if activo else "true"
        self._repo_config.guardar(PILOTO_ACTIVO, nuevo_valor)
        self._actualizar_boton(nuevo_valor == "true")

    def _on_hora_cambiada(self, hora: QTime):
        """Persiste la nueva hora en BD cuando el usuario la cambia."""
        self._repo_config.guardar(PILOTO_HORA, hora.toString("HH:mm"))
