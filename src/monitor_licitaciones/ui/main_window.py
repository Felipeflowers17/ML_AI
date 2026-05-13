"""MainWindow — Ventana principal del Monitor de Licitaciones.

Organiza la UI en pestañas principales (Candidatas, Seguimiento, Ofertadas,
Herramientas) con sub-pestañas en Herramientas. Orquesta la comunicación
entre widgets, workers y repositorios.

La UI no accede directamente a la BD. Toda operación de datos pasa por
workers (operaciones largas) o por repositorios (operaciones síncronas).
"""

from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from monitor_licitaciones.config import ETAPAS_ACTIVAS
from monitor_licitaciones.ui.dialogs.config_exportacion import (
    ConfigExportacionDialog,
)
from monitor_licitaciones.ui.dialogs.config_extraccion import (
    ConfigExtraccionDialog,
)
from monitor_licitaciones.ui.dialogs.config_palabras_clave import (
    ConfigPalabrasClaveDialog,
)
from monitor_licitaciones.ui.dialogs.config_piloto import ConfigPilotoDialog
from monitor_licitaciones.ui.dialogs.gestion_organismos import (
    GestionOrganismosDialog,
)
from monitor_licitaciones.ui.widgets.filtro_busqueda import FiltroBusqueda
from monitor_licitaciones.ui.widgets.indicadores_pipeline import (
    IndicadoresPipeline,
)
from monitor_licitaciones.ui.widgets.tabla_licitaciones import (
    TablaLicitaciones,
)


class MainWindow(QMainWindow):
    """Ventana principal del Monitor de Licitaciones.

    Recibe todas las dependencias por inyección para facilitar tests y
    mantener la independencia de la capa de infraestructura.

    Args:
        repo_licitaciones: Repositorio de licitaciones.
        repo_reglas: Repositorio de reglas (palabras clave y organismos).
        repo_config: Repositorio de configuración.
        gestor_reglas: Gestor thread-safe de reglas de scoring.
        gestor_pipeline: GestorPipeline con lógica de transiciones.
        extraccion_worker: ExtraccionWorker instanciado (se reusa).
        scoring_worker: ScoringWorker instanciado (se reusa).
        exportacion_worker_factory: Callable que crea ExportacionWorker.
        piloto_worker: PilotoWorker instanciado.
    """

    def __init__(
        self,
        repo_licitaciones,
        repo_reglas,
        repo_config,
        gestor_reglas,
        gestor_pipeline,
        extraccion_worker,
        scoring_worker,
        exportacion_worker_factory,
        piloto_worker,
        parent=None,
    ):
        super().__init__(parent)
        self._repo_licitaciones = repo_licitaciones
        self._repo_reglas = repo_reglas
        self._repo_config = repo_config
        self._gestor_reglas = gestor_reglas
        self._gestor_pipeline = gestor_pipeline
        self._extraccion_worker = extraccion_worker
        self._scoring_worker = scoring_worker
        self._exportacion_worker_factory = exportacion_worker_factory
        self._piloto_worker = piloto_worker

        # Estado de lazy loading por pestaña
        self._tabs_cargadas = {
            "candidata": False,
            "seguimiento": False,
            "ofertada": False,
        }
        self._necesita_actualizacion = {
            "candidata": False,
            "seguimiento": False,
            "ofertada": False,
        }

        self.setWindowTitle("Monitor de Licitaciones — Mercado Público Chile")
        self.setMinimumSize(900, 600)

        self._setup_ui()
        self._conectar_senales()

        # Iniciar PilotoWorker
        self._piloto_worker.start()

    # ── Setup de UI ──────────────────────────────────────────────────────

    def _setup_ui(self):
        """Construye toda la UI de la ventana principal."""
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout = QVBoxLayout(widget_central)

        # ── Indicadores del pipeline ─────────────────────────────────────
        self._indicadores = IndicadoresPipeline(self._repo_licitaciones)
        layout.addWidget(self._indicadores)

        # ── Pestañas principales ─────────────────────────────────────────
        self._tabs_principales = QTabWidget()
        self._tabs_principales.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tabs_principales)

        # Crear pestañas de etapas
        self._tabs_etapa = {}
        self._tablas_etapa = {}
        self._filtros_etapa = {}

        for etapa in ETAPAS_ACTIVAS:
            tab, tabla, filtro = self._crear_pestania_etapa(etapa)
            self._tabs_etapa[etapa] = tab
            self._tablas_etapa[etapa] = tabla
            self._filtros_etapa[etapa] = filtro
            self._tabs_principales.addTab(tab, etapa.capitalize())

        # Crear pestaña de Herramientas
        self._tabs_herramientas = self._crear_pestania_herramientas()
        self._tabs_principales.addTab(
            self._tabs_herramientas, "Herramientas del Sistema"
        )

    def _crear_pestania_etapa(self, etapa: str):
        """Crea una pestaña con tabla paginada y filtro para una etapa.

        Returns:
            Tuple[QWidget, TablaLicitaciones, FiltroBusqueda]
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Filtro de búsqueda
        filtro = FiltroBusqueda()

        # Tabla de licitaciones
        tabla = TablaLicitaciones(
            gestor_pipeline=self._gestor_pipeline,
            repo_licitaciones=self._repo_licitaciones,
        )

        # Conectar filtro a tabla
        filtro.texto_cambiado.connect(
            lambda texto, e=etapa: self._on_filtro_cambiado(e, texto)
        )

        # Conectar cambio de etapa en tabla
        tabla.etapa_cambiada.connect(self._on_etapa_cambiada)

        layout.addWidget(filtro)
        layout.addWidget(tabla)

        return tab, tabla, filtro

    def _crear_pestania_herramientas(self):
        """Crea la pestaña de Herramientas con sub-pestañas."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        sub_tabs = QTabWidget()

        # Extracción
        self._dialog_extraccion = ConfigExtraccionDialog(
            self._extraccion_worker
        )
        # Re-empaquetar el diálogo como widget
        wrapper_extraccion = QWidget()
        wrapper_layout = QVBoxLayout(wrapper_extraccion)
        wrapper_layout.addWidget(self._dialog_extraccion)
        sub_tabs.addTab(wrapper_extraccion, "Extracción")

        # Exportación
        wrapper_exportacion = self._crear_wrapper_exportacion()
        sub_tabs.addTab(wrapper_exportacion, "Exportación")

        # Palabras Clave
        self._dialog_palabras_clave = ConfigPalabrasClaveDialog(
            self._repo_reglas
        )
        wrapper_pk = QWidget()
        wrapper_pk_layout = QVBoxLayout(wrapper_pk)
        wrapper_pk_layout.addWidget(self._dialog_palabras_clave)
        sub_tabs.addTab(wrapper_pk, "Palabras Clave")

        # Organismos
        self._dialog_organismos = GestionOrganismosDialog(
            self._repo_reglas,
        )
        wrapper_org = QWidget()
        org_layout = QVBoxLayout(wrapper_org)
        org_layout.addWidget(self._dialog_organismos)
        sub_tabs.addTab(wrapper_org, "Organismos")

        # Piloto Automático
        self._dialog_piloto = ConfigPilotoDialog(self._repo_config)
        wrapper_piloto = QWidget()
        wrapper_piloto_layout = QVBoxLayout(wrapper_piloto)
        wrapper_piloto_layout.addWidget(self._dialog_piloto)
        sub_tabs.addTab(wrapper_piloto, "Piloto Automático")

        layout.addWidget(sub_tabs)
        return tab

    def _crear_wrapper_exportacion(self):
        """Crea el widget wrapper para el diálogo de exportación."""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)

        dialog = ConfigExportacionDialog(self._exportacion_worker_factory)
        wrapper_layout.addWidget(dialog)

        return wrapper

    # ── Conexión de señales ──────────────────────────────────────────────

    def _conectar_senales(self):
        """Conecta todas las señales entre workers, widgets e indicadores."""
        # ScoringWorker finalizado → recargar pestañas e indicadores
        self._scoring_worker.finalizado.connect(self._on_scoring_completado)

        # ExtraccionWorker finalizado → actualizar indicadores
        self._extraccion_worker.finalizado.connect(
            self._indicadores.actualizar
        )

        # Palabras clave cambiadas → lanzar ScoringWorker
        self._dialog_palabras_clave.reglas_cambiadas.connect(
            self._lanzar_scoring
        )

        # PilotoWorker estado cambiado → actualizar label en diálogo piloto
        self._piloto_worker.estado_cambiado.connect(
            self._dialog_piloto._lbl_estado.setText
        )

    # ── Eventos ──────────────────────────────────────────────────────────

    def _on_tab_changed(self, indice: int):
        """Maneja cambio de pestaña principal (lazy loading)."""
        texto_pestania = self._tabs_principales.tabText(indice)

        for etapa in ETAPAS_ACTIVAS:
            if texto_pestania == etapa.capitalize():
                self._cargar_pestania_si_necesario(etapa)
                break

    def _on_filtro_cambiado(self, etapa: str, texto: str):
        """Maneja cambio en el filtro de búsqueda."""
        tabla = self._tablas_etapa[etapa]
        if texto:
            datos = self._repo_licitaciones.buscar_por_texto(
                texto, etapa, pagina=0, por_pagina=50
            )
        else:
            datos = self._repo_licitaciones.obtener_por_etapa(
                etapa, pagina=0, por_pagina=50
            )
        tabla.cargar_licitaciones(datos)

    def _on_etapa_cambiada(self, codigo_externo: str, nueva_etapa: str):
        """Maneja cambio de etapa desde el menú contextual de la tabla."""
        self._repo_licitaciones.actualizar_etapa(
            codigo_externo, nueva_etapa
        )
        self._indicadores.actualizar()
        # Marcar pestañas para recarga
        for e in ETAPAS_ACTIVAS:
            self._necesita_actualizacion[e] = True

    def _on_scoring_completado(self):
        """Recarga las 3 pestañas y los indicadores tras el scoring."""
        self._indicadores.actualizar()
        for etapa in ETAPAS_ACTIVAS:
            self._necesita_actualizacion[etapa] = True
            if self._tabs_cargadas[etapa]:
                self._cargar_pestania_si_necesario(etapa)

    # ── Lazy loading ─────────────────────────────────────────────────────

    def _cargar_pestania_si_necesario(self, etapa: str):
        """Carga datos en una pestaña si es necesario (lazy loading).

        Carga la primera vez que se visita la pestaña o cuando
        ``necesita_actualizacion`` es True.
        """
        if self._tabs_cargadas[etapa] and not self._necesita_actualizacion.get(
            etapa, False
        ):
            return

        tabla = self._tablas_etapa[etapa]
        datos = self._repo_licitaciones.obtener_por_etapa(
            etapa, pagina=0, por_pagina=50
        )
        tabla.cargar_licitaciones(datos)
        self._tabs_cargadas[etapa] = True
        self._necesita_actualizacion[etapa] = False

    # ── Acciones ─────────────────────────────────────────────────────────

    def _lanzar_scoring(self):
        """Lanza el ScoringWorker desde la UI (no en main thread)."""
        if self._scoring_worker.isRunning():
            return
        self._scoring_worker.start()

    # ── Ciclo de vida ────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Maneja el cierre de la ventana: detiene el PilotoWorker."""
        self._piloto_worker.detener()
        if not self._piloto_worker.wait(3000):
            self._piloto_worker.terminate()
        event.accept()
