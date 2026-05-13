"""FichaTecnicaDialog — Diálogo modal con la ficha técnica de una licitación.

Se abre al hacer doble clic en una fila de la tabla de licitaciones.
Muestra toda la información disponible: nombre, descripción, productos,
scores por fase, justificación, organismo, etapa y fecha de publicación.
"""

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
)

from monitor_licitaciones.infrastructure.database.repositorio_licitaciones import (
    RepositorioLicitaciones,
)


class FichaTecnicaDialog(QDialog):
    """Diálogo modal con la ficha técnica de una licitación.

    Args:
        codigo_externo: Código de la licitación a mostrar.
        repo_licitaciones: Repositorio para obtener los datos.
        parent: Widget padre (opcional).
    """

    def __init__(
        self,
        codigo_externo: str,
        repo_licitaciones: RepositorioLicitaciones,
        parent=None,
    ):
        super().__init__(parent)
        self._codigo_externo = codigo_externo
        self._repo = repo_licitaciones

        self.setWindowTitle(f"Ficha Técnica — {codigo_externo}")
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)

        self._setup_ui()
        self._cargar_datos()

    def _setup_ui(self) -> None:
        """Construye la UI del diálogo con scroll."""
        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QVBoxLayout()

        # ── Información general ───────────────────────────────────────
        grupo_gral = QGroupBox("Información General")
        form_gral = QFormLayout(grupo_gral)

        self._lbl_nombre = QLabel()
        self._lbl_nombre.setWordWrap(True)
        form_gral.addRow("Nombre:", self._lbl_nombre)

        self._lbl_codigo = QLabel()
        form_gral.addRow("Código:", self._lbl_codigo)

        self._lbl_etapa = QLabel()
        form_gral.addRow("Etapa:", self._lbl_etapa)

        self._lbl_organismo = QLabel()
        form_gral.addRow("Organismo:", self._lbl_organismo)

        self._lbl_fecha_publicacion = QLabel()
        form_gral.addRow("Fecha Publicación:", self._lbl_fecha_publicacion)

        content.addWidget(grupo_gral)

        # ── Descripción ───────────────────────────────────────────────
        grupo_desc = QGroupBox("Descripción")
        desc_layout = QVBoxLayout(grupo_desc)
        self._txt_descripcion = QTextEdit()
        self._txt_descripcion.setReadOnly(True)
        self._txt_descripcion.setMaximumHeight(120)
        desc_layout.addWidget(self._txt_descripcion)
        content.addWidget(grupo_desc)

        # ── Productos / Detalle ───────────────────────────────────────
        grupo_prod = QGroupBox("Productos")
        prod_layout = QVBoxLayout(grupo_prod)
        self._txt_productos = QTextEdit()
        self._txt_productos.setReadOnly(True)
        self._txt_productos.setMaximumHeight(100)
        prod_layout.addWidget(self._txt_productos)
        content.addWidget(grupo_prod)

        # ── Scoring ───────────────────────────────────────────────────
        grupo_score = QGroupBox("Scoring")
        form_score = QFormLayout(grupo_score)

        self._lbl_score_resumen = QLabel()
        form_score.addRow("Score Resumen:", self._lbl_score_resumen)

        self._lbl_score_detalle = QLabel()
        form_score.addRow("Score Detalle:", self._lbl_score_detalle)

        self._lbl_score_total = QLabel()
        form_score.addRow("Score Total:", self._lbl_score_total)

        content.addWidget(grupo_score)

        # ── Justificación ─────────────────────────────────────────────
        grupo_just = QGroupBox("Justificación del Score")
        just_layout = QVBoxLayout(grupo_just)
        self._txt_justificacion = QTextEdit()
        self._txt_justificacion.setReadOnly(True)
        self._txt_justificacion.setMaximumHeight(100)
        just_layout.addWidget(self._txt_justificacion)
        content.addWidget(grupo_just)

        # Scroll content
        scroll_widget = QLabel()
        scroll_widget.setLayout(content)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

    def _cargar_datos(self) -> None:
        """Carga los datos de la licitación desde el repositorio."""
        lic = self._repo.obtener_por_codigo(self._codigo_externo)
        if lic is None:
            self._lbl_nombre.setText(
                f"[Licitación {self._codigo_externo} no encontrada]"
            )
            return

        self._lbl_nombre.setText(lic.nombre or "")
        self._lbl_codigo.setText(lic.codigo_externo)
        self._lbl_etapa.setText(lic.etapa or "")

        organismo = (
            lic.codigo_organismo if lic.codigo_organismo else "No disponible"
        )
        self._lbl_organismo.setText(organismo)

        if lic.fecha_publicacion:
            self._lbl_fecha_publicacion.setText(
                lic.fecha_publicacion.strftime("%Y-%m-%d %H:%M")
            )
        else:
            self._lbl_fecha_publicacion.setText("No disponible")

        self._txt_descripcion.setPlainText(lic.descripcion or "No disponible")
        self._txt_productos.setPlainText(
            lic.detalle_productos or "No disponible"
        )

        self._lbl_score_resumen.setText(str(lic.score_resumen))
        self._lbl_score_detalle.setText(str(lic.score_detalle))
        self._lbl_score_total.setText(str(lic.score_total))

        self._txt_justificacion.setPlainText(
            lic.justificacion_score or "Sin justificación"
        )
