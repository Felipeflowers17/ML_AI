"""FiltroBusqueda — QLineEdit con debounce de 300ms para búsqueda en tiempo real.

Cada cambio de texto reinicia un timer de 300ms. Si no hay nuevos cambios
en ese intervalo, se emite ``texto_cambiado`` con el texto actual.
Si el texto queda vacío, se emite ``texto_cambiado("")`` para que la vista
cargue sin filtro.
"""

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLineEdit


class FiltroBusqueda(QLineEdit):
    """Campo de texto con debounce para búsqueda en listados.

    Signals:
        texto_cambiado: Se emite tras 300ms sin escribir. Contiene el texto
            actual del campo. Texto vacío emite ``""``.
    """

    texto_cambiado = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Filtrar por nombre o descripción...")

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emitir_texto)

        self.textChanged.connect(self._reiniciar_debounce)

    def _reiniciar_debounce(self):
        """Reinicia el timer de debounce cada vez que el texto cambia."""
        self._debounce_timer.stop()
        self._debounce_timer.start(300)

    def _emitir_texto(self):
        """Emite la señal con el texto actual del campo."""
        self.texto_cambiado.emit(self.text())
