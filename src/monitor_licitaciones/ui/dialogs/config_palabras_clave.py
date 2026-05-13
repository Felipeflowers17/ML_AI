"""Diálogo de gestión de palabras clave para el scoring.

Permite agregar, editar y eliminar (soft delete) palabras clave con sus
pesos por campo (título, descripción, productos). Al guardar cambios,
emite ``reglas_cambiadas`` para que la main window lance el ScoringWorker.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class _EditarPalabraDialog(QDialog):
    """Subdiálogo modal para agregar o editar una palabra clave."""

    def __init__(self, parent=None, datos=None):
        super().__init__(parent)
        self.setWindowTitle("Palabra Clave")
        self.setMinimumWidth(400)

        self._datos = datos or {}

        layout = QFormLayout(self)

        self._txt_termino = QLineEdit(self._datos.get("termino", ""))
        layout.addRow("Término:", self._txt_termino)

        self._txt_categoria = QLineEdit(self._datos.get("categoria", ""))
        layout.addRow("Categoría:", self._txt_categoria)

        self._spn_peso_titulo = QSpinBox()
        self._spn_peso_titulo.setRange(0, 100)
        self._spn_peso_titulo.setValue(self._datos.get("peso_titulo", 0))
        layout.addRow("Peso Título:", self._spn_peso_titulo)

        self._spn_peso_descripcion = QSpinBox()
        self._spn_peso_descripcion.setRange(0, 100)
        self._spn_peso_descripcion.setValue(self._datos.get("peso_descripcion", 0))
        layout.addRow("Peso Descripción:", self._spn_peso_descripcion)

        self._spn_peso_productos = QSpinBox()
        self._spn_peso_productos.setRange(0, 100)
        self._spn_peso_productos.setValue(self._datos.get("peso_productos", 0))
        layout.addRow("Peso Productos:", self._spn_peso_productos)

        self._btn_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._btn_box.accepted.connect(self.accept)
        self._btn_box.rejected.connect(self.reject)
        layout.addRow(self._btn_box)

    def obtener_datos(self) -> dict:
        """Retorna los datos ingresados como dict."""
        datos = {
            "termino": self._txt_termino.text().strip(),
            "categoria": self._txt_categoria.text().strip(),
            "peso_titulo": self._spn_peso_titulo.value(),
            "peso_descripcion": self._spn_peso_descripcion.value(),
            "peso_productos": self._spn_peso_productos.value(),
        }
        if "id" in self._datos:
            datos["id"] = self._datos["id"]
        return datos


class ConfigPalabrasClaveDialog(QDialog):
    """Diálogo de gestión de palabras clave del scoring.

    Signals:
        reglas_cambiadas: Se emite cuando el usuario guarda cambios,
            indicando a la main window que debe relanzar el ScoringWorker.
    """

    reglas_cambiadas = Signal()

    COLUMNAS = [
        "Término",
        "Categoría",
        "Peso Título",
        "Peso Descripción",
        "Peso Productos",
        "Estado",
    ]

    def __init__(self, repo_reglas, parent=None):
        super().__init__(parent)
        self._repo = repo_reglas
        self._datos_originales = []
        self._datos_actuales = []

        self.setWindowTitle("Configurar Palabras Clave")
        self.setMinimumSize(700, 450)

        self._setup_ui()
        self._cargar_datos()

    def _setup_ui(self):
        """Construye los componentes visuales del diálogo."""
        layout = QVBoxLayout(self)

        # Tabla de palabras clave
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(len(self.COLUMNAS))
        self._tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.horizontalHeader().setStretchLastSection(True)
        self._tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self._tabla.verticalHeader().setVisible(False)

        # Botones de acción
        btn_layout = QHBoxLayout()
        self._btn_agregar = QPushButton("Agregar")
        self._btn_agregar.clicked.connect(self._agregar_palabra)
        self._btn_editar = QPushButton("Editar")
        self._btn_editar.clicked.connect(self._editar_palabra)
        self._btn_eliminar = QPushButton("Eliminar")
        self._btn_eliminar.clicked.connect(self._eliminar_palabra)

        btn_layout.addWidget(self._btn_agregar)
        btn_layout.addWidget(self._btn_editar)
        btn_layout.addWidget(self._btn_eliminar)
        btn_layout.addStretch()

        # Botón de cierre
        self._btn_cerrar = QPushButton("Cerrar")
        self._btn_cerrar.clicked.connect(self._cerrar_y_guardar)

        layout.addWidget(self._tabla)
        layout.addLayout(btn_layout)
        layout.addWidget(self._btn_cerrar)

    def _cargar_datos(self):
        """Carga las palabras clave desde el repositorio."""
        palabras = self._repo.obtener_palabras_clave()
        self._datos_originales = list(palabras)
        self._datos_actuales = list(palabras)
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        """Refresca la tabla con los datos actuales."""
        self._tabla.setRowCount(len(self._datos_actuales))
        for fila, pk in enumerate(self._datos_actuales):
            self._tabla.setItem(fila, 0, QTableWidgetItem(pk.termino))
            self._tabla.setItem(
                fila, 1, QTableWidgetItem(pk.categoria or "")
            )
            self._tabla.setItem(
                fila, 2, QTableWidgetItem(str(pk.peso_titulo))
            )
            self._tabla.setItem(
                fila, 3, QTableWidgetItem(str(pk.peso_descripcion))
            )
            self._tabla.setItem(
                fila, 4, QTableWidgetItem(str(pk.peso_productos))
            )
            estado = "Activa" if pk.activa else "Inactiva"
            self._tabla.setItem(fila, 5, QTableWidgetItem(estado))

    def _agregar_palabra(self):
        """Abre subdiálogo para agregar una nueva palabra clave."""
        dialog = _EditarPalabraDialog(self)
        if dialog.exec() == QDialog.Accepted:
            datos = dialog.obtener_datos()
            # Persistir en BD
            self._repo.guardar_palabra_clave(datos)
            # Recargar datos
            self._cargar_datos()
            self.reglas_cambiadas.emit()

    def _editar_palabra(self):
        """Abre subdiálogo para editar la palabra seleccionada."""
        fila = self._tabla.currentRow()
        if fila < 0:
            QMessageBox.information(
                self, "Editar", "Seleccione una palabra clave para editar."
            )
            return

        pk = self._datos_actuales[fila]
        datos = {
            "id": pk.id,
            "termino": pk.termino,
            "categoria": pk.categoria or "",
            "peso_titulo": pk.peso_titulo,
            "peso_descripcion": pk.peso_descripcion,
            "peso_productos": pk.peso_productos,
        }

        dialog = _EditarPalabraDialog(self, datos=datos)
        if dialog.exec() == QDialog.Accepted:
            nuevos = dialog.obtener_datos()
            self._repo.guardar_palabra_clave(nuevos)
            self._cargar_datos()
            self.reglas_cambiadas.emit()

    def _eliminar_palabra(self):
        """Soft delete de la palabra seleccionada con confirmación."""
        fila = self._tabla.currentRow()
        if fila < 0:
            QMessageBox.information(
                self,
                "Eliminar",
                "Seleccione una palabra clave para eliminar.",
            )
            return

        pk = self._datos_actuales[fila]
        respuesta = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f'¿Está seguro de eliminar "{pk.termino}"?\n'
            "La palabra clave se desactivará, no se borrará permanentemente.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if respuesta == QMessageBox.Yes:
            self._repo.eliminar_palabra_clave(pk.id)
            self._cargar_datos()
            self.reglas_cambiadas.emit()

    def _cerrar_y_guardar(self):
        """Cierra el diálogo. Los cambios ya se persistieron en cada acción."""
        self.accept()
