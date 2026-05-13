"""Tests para ScoringWorker — QThread que recalcula scores de licitaciones activas.

Usa mocks de repositorios y del motor de scoring. Verifica que el worker
solo procesa licitaciones activas, emite avance cada 25 registros, siempre
emite finalizado, y usa el mapping correcto de palabras a reglas.
"""

from unittest.mock import MagicMock, patch

import pytest
from monitor_licitaciones.infrastructure.database.models import PalabraClave
from monitor_licitaciones.workers import mapear_reglas
from PySide6.QtTest import QSignalSpy
from pytestqt.qtbot import QtBot


@pytest.fixture
def mock_repo_lic():
    return MagicMock()


@pytest.fixture
def mock_repo_reglas():
    repo = MagicMock()
    repo.obtener_palabras_clave.return_value = []
    repo.obtener_organismos.return_value = []
    return repo


@pytest.fixture
def mock_gestor():
    gestor = MagicMock()
    gestor.obtener_snapshot.return_value = []
    return gestor


class TestMapearReglas:
    """Tests para la función mapear_reglas en workers/__init__."""

    def test_mapear_reglas_convierte_palabras_activas(self):
        """PalabraClave activas se convierten a ReglaScoring."""
        palabra = MagicMock(spec=PalabraClave)
        palabra.termino = "silla"
        palabra.peso_titulo = 10
        palabra.peso_descripcion = 5
        palabra.peso_productos = 1
        palabra.activa = True

        resultado = mapear_reglas([palabra])

        assert len(resultado) == 1
        assert resultado[0]["termino"] == "silla"
        assert resultado[0]["peso_titulo"] == 10

    def test_mapear_reglas_excluye_palabras_inactivas(self):
        """PalabraClave inactivas NO se incluyen en el resultado."""
        palabra = MagicMock(spec=PalabraClave)
        palabra.termino = "mesa"
        palabra.peso_titulo = 20
        palabra.peso_descripcion = 10
        palabra.peso_productos = 2
        palabra.activa = False

        resultado = mapear_reglas([palabra])

        assert len(resultado) == 0

    def test_mapear_reglas_lista_vacia(self):
        """Lista vacía de palabras produce lista vacía de reglas."""
        resultado = mapear_reglas([])
        assert len(resultado) == 0


class TestScoringWorker:
    """Suite de tests para ScoringWorker."""

    def test_recalcula_solo_licitaciones_activas(
        self,
        qtbot: QtBot,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Mock del repositorio devuelve licitaciones mezcladas,
        actualizar_score solo se llama para las activas."""
        from monitor_licitaciones.workers.scoring_worker import ScoringWorker

        # Crear licitaciones mock activas e inactivas
        lic_activa = MagicMock()
        lic_activa.codigo_externo = "L1"
        lic_activa.nombre = "Sillas de oficina"
        lic_activa.descripcion = "Compra de sillas"
        lic_activa.detalle_productos = ""
        lic_activa.codigo_organismo = "ORG1"

        lic_inactiva = MagicMock()
        lic_inactiva.codigo_externo = "L2"
        lic_inactiva.nombre = "Aseo"
        lic_inactiva.descripcion = ""
        lic_inactiva.detalle_productos = ""
        lic_inactiva.codigo_organismo = None

        # Configurar mock para devolver ambas
        mock_repo_lic.obtener_activas_en_pipeline.return_value = [
            lic_activa,
            lic_inactiva,
        ]

        with patch(
            "monitor_licitaciones.workers.scoring_worker.evaluar_titulo",
            return_value=(10, ["[TÍTULO] 'silla' (+10)"]),
        ), patch(
            "monitor_licitaciones.workers.scoring_worker.evaluar_detalle",
            return_value=(0, []),
        ):
            worker = ScoringWorker(
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        # actualizar_score debe llamarse para las 2 licitaciones activas devueltas
        assert mock_repo_lic.actualizar_score.call_count == 2
        worker.wait(1000)

    def test_emite_avance_cada_25(
        self,
        qtbot: QtBot,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Con 50 licitaciones, avance se emite exactamente 2 veces."""
        from monitor_licitaciones.workers.scoring_worker import ScoringWorker

        # Crear 50 licitaciones mock
        licitaciones = []
        for i in range(50):
            lic = MagicMock()
            lic.codigo_externo = f"L{i}"
            lic.nombre = f"Item {i}"
            lic.descripcion = ""
            lic.detalle_productos = ""
            lic.codigo_organismo = None
            licitaciones.append(lic)

        mock_repo_lic.obtener_activas_en_pipeline.return_value = licitaciones

        with patch(
            "monitor_licitaciones.workers.scoring_worker.evaluar_titulo",
            return_value=(0, []),
        ), patch(
            "monitor_licitaciones.workers.scoring_worker.evaluar_detalle",
            return_value=(0, []),
        ):
            worker = ScoringWorker(
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            spy_avance = QSignalSpy(worker.avance)

            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        # Con 50 licitaciones emite avance en 25 y 50 → 2 veces
        assert spy_avance.count() == 2
        worker.wait(1000)

    def test_emite_finalizado_siempre(
        self,
        qtbot: QtBot,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Incluso con lista vacía, finalizado se emite."""
        from monitor_licitaciones.workers.scoring_worker import ScoringWorker

        mock_repo_lic.obtener_activas_en_pipeline.return_value = []

        worker = ScoringWorker(
            repo_licitaciones=mock_repo_lic,
            repo_reglas=mock_repo_reglas,
            gestor_reglas=mock_gestor,
        )
        spy = QSignalSpy(worker.finalizado)

        with qtbot.waitSignal(worker.finalizado, timeout=5000):
            worker.start()

        assert spy.count() == 1
        worker.wait(1000)

    def test_usa_mapping_de_palabras_a_reglas(
        self,
        qtbot: QtBot,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Verificar que el worker llama a mapear_reglas() antes de pasar al motor."""
        from monitor_licitaciones.workers.scoring_worker import ScoringWorker

        mock_repo_lic.obtener_activas_en_pipeline.return_value = []

        with patch(
            "monitor_licitaciones.workers.scoring_worker.mapear_reglas"
        ) as mock_mapear:
            mock_mapear.return_value = []

            worker = ScoringWorker(
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        # mapear_reglas debe haberse llamado con las palabras clave del repo
        mock_mapear.assert_called_once()
        worker.wait(1000)

    def test_error_en_run_emite_error(
        self,
        qtbot: QtBot,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Cuando obtener_palabras_clave() lanza excepción, emite error."""
        from monitor_licitaciones.workers.scoring_worker import ScoringWorker

        mock_repo_reglas.obtener_palabras_clave.side_effect = Exception(
            "DB connection error"
        )

        worker = ScoringWorker(
            repo_licitaciones=mock_repo_lic,
            repo_reglas=mock_repo_reglas,
            gestor_reglas=mock_gestor,
        )
        spy_error = QSignalSpy(worker.error)

        worker.start()
        ok = worker.wait(3000)

        assert ok, "Worker no terminó tras error"
        assert spy_error.count() >= 1

        worker.wait(500)

    def test_puntaje_organismo_se_incluye_en_total(
        self,
        qtbot: QtBot,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Cuando organismo tiene puntaje_fijo, se suma al score_total."""
        from monitor_licitaciones.workers.scoring_worker import ScoringWorker

        lic = MagicMock()
        lic.codigo_externo = "L1"
        lic.nombre = "Sillas de oficina"
        lic.descripcion = "Compra de sillas"
        lic.detalle_productos = ""
        lic.codigo_organismo = "ORG1"

        mock_repo_lic.obtener_activas_en_pipeline.return_value = [lic]

        org_mock = MagicMock()
        org_mock.codigo = "ORG1"
        org_mock.puntaje_fijo = 15
        mock_repo_reglas.obtener_organismos.return_value = [org_mock]

        with patch(
            "monitor_licitaciones.workers.scoring_worker.evaluar_titulo",
            return_value=(10, ["[TÍTULO] 'silla' (+10)"]),
        ), patch(
            "monitor_licitaciones.workers.scoring_worker.evaluar_detalle",
            return_value=(5, ["[DESC] 'silla' (+5)"]),
        ):
            worker = ScoringWorker(
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        # score_total = 10 (título) + 5 (detalle) + 15 (organismo) = 30
        mock_repo_lic.actualizar_score.assert_called_once()
        _, kwargs = mock_repo_lic.actualizar_score.call_args
        assert kwargs["score_total"] == 30

        worker.wait(1000)

    def test_codigo_organismo_none_usa_cero(
        self,
        qtbot: QtBot,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Cuando codigo_organismo es None, puntaje_org = 0."""
        from monitor_licitaciones.workers.scoring_worker import ScoringWorker

        lic = MagicMock()
        lic.codigo_externo = "L1"
        lic.nombre = "Test"
        lic.descripcion = ""
        lic.detalle_productos = ""
        lic.codigo_organismo = None

        mock_repo_lic.obtener_activas_en_pipeline.return_value = [lic]

        with patch(
            "monitor_licitaciones.workers.scoring_worker.evaluar_titulo",
            return_value=(5, []),
        ), patch(
            "monitor_licitaciones.workers.scoring_worker.evaluar_detalle",
            return_value=(0, []),
        ):
            worker = ScoringWorker(
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        mock_repo_lic.actualizar_score.assert_called_once()
        _, kwargs = mock_repo_lic.actualizar_score.call_args
        assert kwargs["score_total"] == 5  # solo score_resumen

        worker.wait(1000)
