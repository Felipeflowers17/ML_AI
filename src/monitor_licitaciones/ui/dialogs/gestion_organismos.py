"""GestionOrganismosDialog — Diálogo CRUD para administrar organismos.

Permite listar, crear, editar y desactivar organismos públicos registrados
en la base de datos. Cada organismo tiene un código, nombre y puntaje fijo
que se usa en el scoring automático.
"""

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
    RepositorioReglas,
)


class GestionOrganismosDialog(QDialog):
    """Diálogo CRUD para la gestión de organismos.

    Args:
        repo_reglas: Repositorio de reglas para persistir datos.
        parent: Widget padre (opcional).
    """

    def __init__(
        self,
        repo_reglas: RepositorioReglas,
        parent=None,
    ):
        super().__init__(parent)
        self._repo = repo_reglas

        self.setWindowTitle("Gestión de Organismos")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        self._setup_ui()
        self._cargar_datos()

    def _setup_ui(self) -> None:
        """Construye la UI del diálogo."""
        layout = QVBoxLayout(self)

        # ── Tabla de organismos ────────────────────────────────────────
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(3)
        self._tabla.setHorizontalHeaderLabels([
            "Código",
            "Nombre",
            "Puntaje Fijo",
        ])
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.horizontalHeader().setStretchLastSection(True)
        self._tabla.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self._tabla.verticalHeader().setVisible(False)
        layout.addWidget(self._tabla)

        # ── Botones ────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()

        self._btn_agregar = QPushButton("Agregar")
        self._btn_agregar.clicked.connect(self._agregar)

        self._btn_editar = QPushButton("Editar")
        self._btn_editar.clicked.connect(self._editar)

        self._btn_desactivar = QPushButton("Desactivar")
        self._btn_desactivar.clicked.connect(self._desactivar)

        btn_layout.addWidget(self._btn_agregar)
        btn_layout.addWidget(self._btn_editar)
        btn_layout.addWidget(self._btn_desactivar)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def _cargar_datos(self) -> None:
        """Carga la lista de organismos desde el repositorio."""
        organismos = self._repo.obtener_organismos()
        self._tabla.setRowCount(len(organismos))

        for fila, org in enumerate(organismos):
            self._tabla.setItem(
                fila, 0, QTableWidgetItem(org.codigo)
            )
            self._tabla.setItem(
                fila, 1, QTableWidgetItem(org.nombre)
            )
            self._tabla.setItem(
                fila, 2,
                QTableWidgetItem(str(org.puntaje_fijo)),
            )

    def _obtener_organismo_seleccionado(self) -> str | None:
        """Retorna el código del organismo seleccionado o ``None``."""
        filas = self._tabla.selectionModel().selectedRows()
        if not filas:
            QMessageBox.information(
                self, "Selección requerida",
                "Seleccione un organismo de la tabla."
            )
            return None
        item = self._tabla.item(filas[0].row(), 0)
        return item.text() if item else None

    def _agregar(self) -> None:
        """Abre sub-diálogo para crear un nuevo organismo."""
        dialog = _OrganismoEditDialog(self._repo, parent=self)
        if dialog.exec_():
            self._cargar_datos()

    def _editar(self) -> None:
        """Abre sub-diálogo para modificar un organismo existente."""
        codigo = self._obtener_organismo_seleccionado()
        if codigo is None:
            return

        dialog = _OrganismoEditDialog(
            self._repo, codigo=codigo, parent=self
        )
        if dialog.exec_():
            self._cargar_datos()

    def _desactivar(self) -> None:
        """Desactiva un organismo (puntaje_fijo = 0)."""
        codigo = self._obtener_organismo_seleccionado()
        if codigo is None:
            return

        respuesta = QMessageBox.question(
            self,
            "Confirmar desactivación",
            f"¿Está seguro de desactivar el organismo '{codigo}'?\n"
            f"Su puntaje fijo se establecerá a 0.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return

        self._repo.actualizar_puntaje_organismo(codigo, 0)
        self._cargar_datos()


class _OrganismoEditDialog(QDialog):
    """Sub-diálogo para crear o editar un organismo.

    Args:
        repo_reglas: Repositorio para persistir.
        codigo: Código del organismo a editar (``None`` para crear nuevo).
        parent: Widget padre.
    """

    def __init__(
        self,
        repo_reglas: RepositorioReglas,
        codigo: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._repo = repo_reglas
        self._codigo_original = codigo

        titulo = "Editar Organismo" if codigo else "Nuevo Organismo"
        self.setWindowTitle(titulo)
        self.setMinimumWidth(350)

        self._setup_ui()

        if codigo:
            self._cargar_datos_existente(codigo)

    def _setup_ui(self) -> None:
        """Construye el formulario de edición."""
        layout = QFormLayout(self)

        self._txt_codigo = QLineEdit()
        self._txt_codigo.setPlaceholderText("Ej: PER6973CFD")
        if self._codigo_original:
            self._txt_codigo.setReadOnly(True)
        layout.addRow("Código:", self._txt_codigo)

        self._txt_nombre = QLineEdit()
        self._txt_nombre.setPlaceholderText("Ej: Municipalidad de Santiago")
        layout.addRow("Nombre:", self._txt_nombre)

        self._spin_puntaje = QSpinBox()
        self._spin_puntaje.setRange(0, 1000)
        self._spin_puntaje.setValue(0)
        layout.addRow("Puntaje Fijo:", self._spin_puntaje)

        # Botones
        btn_layout = QHBoxLayout()
        self._btn_guardar = QPushButton("Guardar")
        self._btn_guardar.clicked.connect(self._guardar)
        self._btn_cancelar = QPushButton("Cancelar")
        self._btn_cancelar.clicked.connect(self.reject)

        btn_layout.addWidget(self._btn_guardar)
        btn_layout.addWidget(self._btn_cancelar)
        layout.addRow(btn_layout)

    def _cargar_datos_existente(self, codigo: str) -> None:
        """Carga los datos de un organismo existente en el formulario."""
        from monitor_licitaciones.infrastructure.database.models import (
            Organismo,
        )

        org = self._repo._session.query(Organismo).filter(
            Organismo.codigo == codigo
        ).first()
        if org:
            self._txt_codigo.setText(org.codigo)
            self._txt_nombre.setText(org.nombre)
            self._spin_puntaje.setValue(org.puntaje_fijo)

    def _guardar(self) -> None:
        """Valida y persiste el organismo."""
        codigo = self._txt_codigo.text().strip()
        nombre = self._txt_nombre.text().strip()
        puntaje = self._spin_puntaje.value()

        if not codigo:
            QMessageBox.warning(
                self, "Validación", "El código del organismo es obligatorio."
            )
            return
        if not nombre:
            QMessageBox.warning(
                self, "Validación", "El nombre del organismo es obligatorio."
            )
            return

        self._repo.guardar_organismo({
            "codigo": codigo,
            "nombre": nombre,
            "puntaje_fijo": puntaje,
        })
        self.accept()
