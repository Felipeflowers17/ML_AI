"""TablaLicitaciones — Widget reutilizable de lista paginada de licitaciones.

Muestra una tabla con columnas Puntaje Total, Código, Nombre, Fecha Cierre
y Estado. Soporta paginación (Anterior/Siguiente), menú contextual con
destinos del pipeline, doble clic para ficha técnica y señal de cambio de
etapa.

La UI no accede directamente a la BD. Los datos se cargan a través del
repositorio inyectado o mediante ``cargar_licitaciones()``.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from monitor_licitaciones.config import TAMANIO_PAGINA


class TablaLicitaciones(QWidget):
    """Tabla paginada de licitaciones con menú contextual y señales.

    Signals:
        etapa_cambiada: Se emite cuando el usuario cambia la etapa de una
            licitación desde el menú contextual.
            Argumentos: (codigo_externo: str, nueva_etapa: str)
    """

    etapa_cambiada = Signal(str, str)

    def __init__(self, gestor_pipeline, parent=None):
        super().__init__(parent)
        self._gestor_pipeline = gestor_pipeline
        self._datos = []
        self._pagina_actual = 0

        self._setup_ui()

    # ── Setup de UI ──────────────────────────────────────────────────────

    def _setup_ui(self):
        """Construye los componentes visuales del widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._crear_tabla()
        self._crear_texto_ayuda()
        self._crear_botonera_paginacion()

        layout.addWidget(self._tabla)
        layout.addWidget(self._texto_ayuda)
        layout.addLayout(self._pag_layout)

    def _crear_tabla(self):
        """Configura el QTableWidget con las columnas del listado."""
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(5)
        self._tabla.setHorizontalHeaderLabels([
            "Puntaje Total",
            "Código",
            "Nombre",
            "Fecha Cierre",
            "Estado",
        ])
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.horizontalHeader().setStretchLastSection(True)
        self._tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tabla.customContextMenuRequested.connect(self._on_context_menu)
        self._tabla.cellDoubleClicked.connect(self._on_doble_clic)

    def _crear_texto_ayuda(self):
        """Crea el label de ayuda visible debajo de la tabla."""
        self._texto_ayuda = QLabel(
            "Clic derecho sobre una fila para mover la licitación entre etapas."
        )
        self._texto_ayuda.setStyleSheet("color: gray; font-style: italic; padding: 2px 0;")

    def _crear_botonera_paginacion(self):
        """Crea los botones Anterior / Página N / Siguiente."""
        self._pag_layout = QHBoxLayout()

        self._btn_anterior = QPushButton("Anterior")
        self._btn_anterior.clicked.connect(self._pagina_anterior)

        self._lbl_pagina = QLabel("Página 1")
        self._lbl_pagina.setAlignment(Qt.AlignCenter)

        self._btn_siguiente = QPushButton("Siguiente")
        self._btn_siguiente.clicked.connect(self._pagina_siguiente)

        self._pag_layout.addWidget(self._btn_anterior)
        self._pag_layout.addWidget(self._lbl_pagina)
        self._pag_layout.addWidget(self._btn_siguiente)

    # ── Carga de datos ───────────────────────────────────────────────────

    def cargar_licitaciones(self, licitaciones):
        """Carga una lista de licitaciones en la tabla.

        Resetea la paginación a la página 0.
        Cada elemento debe ser un objeto con atributos:
        codigo_externo, nombre, score_total, fecha_cierre, etapa.
        """
        self._datos = list(licitaciones)
        self._pagina_actual = 0
        self._renderizar_pagina()

    def _renderizar_pagina(self):
        """Renderiza las filas de la página actual en la tabla."""
        inicio = self._pagina_actual * TAMANIO_PAGINA
        fin = inicio + TAMANIO_PAGINA
        pagina_datos = self._datos[inicio:fin]

        self._tabla.setRowCount(len(pagina_datos))

        for fila, lic in enumerate(pagina_datos):
            self._poblar_fila(fila, lic)

        self._actualizar_botones_paginacion()

    def _poblar_fila(self, fila: int, lic):
        """Llena una fila con los datos de una licitación."""
        item_score = QTableWidgetItem(str(lic.score_total))
        item_score.setData(Qt.UserRole, lic.etapa)
        self._tabla.setItem(fila, 0, item_score)

        self._tabla.setItem(fila, 1, QTableWidgetItem(str(lic.codigo_externo)))
        self._tabla.setItem(fila, 2, QTableWidgetItem(str(lic.nombre)))

        fecha_str = (
            lic.fecha_cierre.strftime("%Y-%m-%d")
            if lic.fecha_cierre
            else ""
        )
        self._tabla.setItem(fila, 3, QTableWidgetItem(fecha_str))
        self._tabla.setItem(fila, 4, QTableWidgetItem(lic.etapa))

    # ── Paginación ───────────────────────────────────────────────────────

    def _actualizar_botones_paginacion(self):
        """Actualiza estado habilitado de los botones y texto de página."""
        self._btn_anterior.setEnabled(self._pagina_actual > 0)

        # Siguiente: deshabilitado si la última página no está llena
        hay_siguiente = self._tabla.rowCount() >= TAMANIO_PAGINA
        self._btn_siguiente.setEnabled(hay_siguiente)

        self._lbl_pagina.setText(f"Página {self._pagina_actual + 1}")

    def _pagina_anterior(self):
        """Retrocede una página."""
        if self._pagina_actual > 0:
            self._pagina_actual -= 1
            self._renderizar_pagina()

    def _pagina_siguiente(self):
        """Avanza una página."""
        self._pagina_actual += 1
        self._renderizar_pagina()

    # ── Menú contextual ──────────────────────────────────────────────────

    def _crear_menu_contextual(self, fila):
        """Crea un QMenu con los destinos disponibles para la fila indicada.

        Args:
            fila: Índice de la fila en la tabla actual.

        Returns:
            QMenu con las acciones de destino válidas.
        """
        if fila < 0 or fila >= self._tabla.rowCount():
            return QMenu()

        item = self._tabla.item(fila, 0)
        if item is None:
            return QMenu()

        etapa = item.data(Qt.UserRole)
        if not etapa:
            return QMenu()

        menu = QMenu(self)
        destinos = self._gestor_pipeline.destinos_disponibles(etapa)

        for destino in destinos:
            accion = menu.addAction(destino)
            accion.setData(destino)

        return menu

    def _on_context_menu(self, pos):
        """Maneja la solicitud de menú contextual (clic derecho)."""
        item = self._tabla.itemAt(pos)
        if item is None:
            return

        fila = item.row()
        menu = self._crear_menu_contextual(fila)

        if not menu.actions():
            return

        accion = menu.exec_(self._tabla.viewport().mapToGlobal(pos))
        if accion:
            destino = accion.data()
            idx_dato = self._pagina_actual * TAMANIO_PAGINA + fila
            if idx_dato < len(self._datos):
                self.etapa_cambiada.emit(
                    self._datos[idx_dato].codigo_externo, destino
                )

    # ── Doble clic ───────────────────────────────────────────────────────

    def _on_doble_clic(self, fila, columna):
        """Maneja el doble clic en una fila.

        Placeholder: abre el diálogo de ficha técnica con detalle de la
        licitación (descripción, productos, justificación del score).
        """
        if fila < 0 or fila >= len(self._datos):
            return

        # TODO: Implementar diálogo de ficha técnica (tarea futura)
        # lic = self._datos[fila]
        # dialog = FichaTecnicaDialog(lic, self)
        # dialog.exec_()
