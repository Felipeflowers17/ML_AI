"""Tests para los widgets de UI con pytest-qt.

TODOS los tests se escriben ANTES del código de producción (Strict TDD).
Cada test describe el comportamiento esperado del widget antes de que exista.
"""

from unittest.mock import MagicMock

from monitor_licitaciones.config import TAMANIO_PAGINA
from monitor_licitaciones.domain.pipeline.gestor_pipeline import GestorPipeline
from PySide6.QtTest import QTest

# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def _crear_licitacion_mock(
    codigo_externo: str,
    nombre: str,
    etapa: str,
    score_total: int = 0,
    fecha_cierre=None,
    descripcion: str = "",
    detalle_productos: str = "",
    justificacion_score: str = "",
):
    """Crea un mock con los atributos de una Licitacion para tests de UI."""
    mock = MagicMock()
    mock.codigo_externo = codigo_externo
    mock.nombre = nombre
    mock.etapa = etapa
    mock.score_total = score_total
    mock.fecha_cierre = fecha_cierre
    mock.descripcion = descripcion
    mock.detalle_productos = detalle_productos
    mock.justificacion_score = justificacion_score
    return mock


# ────────────────────────────────────────────────────────────────────────────
# FiltroBusqueda
# ────────────────────────────────────────────────────────────────────────────


class TestFiltroBusqueda:
    """Tests del widget FiltroBusqueda — debounce de 300ms."""

    def test_filtro_debounce_emite_una_sola_vez(self, qtbot):
        """Simular 5 cambios rápidos: texto_cambiado se emite 1 vez tras 300ms."""
        from monitor_licitaciones.ui.widgets.filtro_busqueda import (
            FiltroBusqueda,
        )

        filtro = FiltroBusqueda()
        qtbot.addWidget(filtro)
        filtro.show()

        with qtbot.waitSignal(filtro.texto_cambiado, timeout=600) as blocker:
            filtro.setText("a")
            QTest.qWait(20)
            filtro.setText("ab")
            QTest.qWait(20)
            filtro.setText("abc")
            QTest.qWait(20)
            filtro.setText("abcd")
            QTest.qWait(20)
            filtro.setText("abcde")

        assert blocker.signal_triggered, "La señal debe emitirse después del debounce"
        assert blocker.args[0] == "abcde", "Debe emitir el texto final"

    def test_filtro_texto_vacio_emite_string_vacio(self, qtbot):
        """Limpiar el campo emite texto_cambiado('')."""
        from monitor_licitaciones.ui.widgets.filtro_busqueda import (
            FiltroBusqueda,
        )

        filtro = FiltroBusqueda()
        qtbot.addWidget(filtro)
        filtro.show()

        # Poner texto y esperar que el debounce se dispare
        filtro.setText("algo")
        qtbot.wait(350)

        # Ahora limpiar — debe emitir "" tras el debounce
        with qtbot.waitSignal(filtro.texto_cambiado, timeout=500) as blocker:
            filtro.setText("")

        assert blocker.signal_triggered
        assert blocker.args[0] == ""


# ────────────────────────────────────────────────────────────────────────────
# TablaLicitaciones
# ────────────────────────────────────────────────────────────────────────────


class TestTablaLicitaciones:
    """Tests del widget TablaLicitaciones — paginación y menú contextual."""

    def test_tabla_menu_contextual_candidata(self, qtbot):
        """Clic derecho en fila candidata: menú tiene seguimiento y ofertada,
        pero NO candidata."""
        from monitor_licitaciones.ui.widgets.tabla_licitaciones import (
            TablaLicitaciones,
        )

        gestor = GestorPipeline()
        tabla = TablaLicitaciones(gestor_pipeline=gestor)
        qtbot.addWidget(tabla)
        tabla.show()

        licitaciones = [
            _crear_licitacion_mock(
                codigo_externo="L001",
                nombre="Licitación de prueba",
                etapa="candidata",
                score_total=100,
            )
        ]
        tabla.cargar_licitaciones(licitaciones)

        menu = tabla._crear_menu_contextual(0)
        acciones = [a.text() for a in menu.actions()]

        assert "seguimiento" in acciones
        assert "ofertada" in acciones
        assert "candidata" not in acciones

    def test_tabla_paginacion_siguiente_deshabilitado(self, qtbot):
        """Cargar menos filas que TAMANIO_PAGINA: botón Siguiente deshabilitado."""
        from monitor_licitaciones.ui.widgets.tabla_licitaciones import (
            TablaLicitaciones,
        )

        gestor = GestorPipeline()
        tabla = TablaLicitaciones(gestor_pipeline=gestor)
        qtbot.addWidget(tabla)
        tabla.show()

        # Menos filas que el tamaño de página
        licitaciones = [
            _crear_licitacion_mock(
                codigo_externo=f"L{i:03d}",
                nombre=f"Licitación {i}",
                etapa="candidata",
            )
            for i in range(TAMANIO_PAGINA - 10)
        ]
        tabla.cargar_licitaciones(licitaciones)

        assert (
            tabla._btn_siguiente.isEnabled() is False
        ), "Siguiente debe estar deshabilitado si rowCount < TAMANIO_PAGINA"

    def test_tabla_texto_ayuda_visible(self, qtbot):
        """El texto de ayuda es visible sin hacer clic."""
        from monitor_licitaciones.ui.widgets.tabla_licitaciones import (
            TablaLicitaciones,
        )

        gestor = GestorPipeline()
        tabla = TablaLicitaciones(gestor_pipeline=gestor)
        qtbot.addWidget(tabla)
        tabla.show()

        # El texto de ayuda debe estar visible en la interfaz
        assert tabla._texto_ayuda is not None
        assert tabla._texto_ayuda.isVisible()
        assert "Clic derecho" in tabla._texto_ayuda.text()


# ────────────────────────────────────────────────────────────────────────────
# IndicadoresPipeline
# ────────────────────────────────────────────────────────────────────────────


class TestIndicadoresPipeline:
    """Tests del widget IndicadoresPipeline — contadores por etapa."""

    def test_indicadores_muestra_cero_por_defecto(self, qtbot):
        """Sin datos, los labels muestran cero, no texto vacío."""
        from monitor_licitaciones.ui.widgets.indicadores_pipeline import (
            IndicadoresPipeline,
        )

        indicadores = IndicadoresPipeline(repo_licitaciones=None)
        qtbot.addWidget(indicadores)
        indicadores.show()

        assert indicadores._lbl_candidatas.text() == "Candidatas (0)"
        assert indicadores._lbl_seguimiento.text() == "Seguimiento (0)"
        assert indicadores._lbl_ofertadas.text() == "Ofertadas (0)"

    def test_indicadores_actualizar_con_datos(self, qtbot):
        """Mock de contar_por_etapa() actualiza los tres labels."""
        from monitor_licitaciones.ui.widgets.indicadores_pipeline import (
            IndicadoresPipeline,
        )

        repo_mock = MagicMock()
        repo_mock.contar_por_etapa.return_value = {
            "candidata": 5,
            "seguimiento": 2,
            "ofertada": 1,
        }

        indicadores = IndicadoresPipeline(repo_licitaciones=repo_mock)
        qtbot.addWidget(indicadores)
        indicadores.show()

        indicadores.actualizar()

        assert indicadores._lbl_candidatas.text() == "Candidatas (5)"
        assert indicadores._lbl_seguimiento.text() == "Seguimiento (2)"
        assert indicadores._lbl_ofertadas.text() == "Ofertadas (1)"
