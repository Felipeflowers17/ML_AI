"""Tests para ExtraccionWorker — QThread que extrae licitaciones desde la API.

Usa mocks de ClienteAPI y repositorios. Verifica señales, flujo de
extracción y comportamiento de detener().
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtTest import QSignalSpy
from pytestqt.qtbot import QtBot


@pytest.fixture
def mock_cliente():
    cliente = MagicMock()
    cliente.obtener_licitaciones_dia.return_value = []
    return cliente


@pytest.fixture
def mock_repo_lic():
    return MagicMock()


@pytest.fixture
def mock_repo_reglas():
    repo = MagicMock()
    repo.obtener_organismos.return_value = []
    return repo


@pytest.fixture
def mock_gestor():
    gestor = MagicMock()
    gestor.obtener_snapshot.return_value = []
    return gestor


class TestExtraccionWorker:
    """Suite de tests para ExtraccionWorker."""

    def test_emite_finalizado_al_completar_rango(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """API retorna lista vacía, finalizado se emite exactamente una vez."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        worker = ExtraccionWorker(
            fecha_inicio="2026-01-01",
            fecha_fin="2026-01-03",
            cliente_mp=mock_cliente,
            repo_licitaciones=mock_repo_lic,
            repo_reglas=mock_repo_reglas,
            gestor_reglas=mock_gestor,
        )
        spy = QSignalSpy(worker.finalizado)

        with qtbot.waitSignal(worker.finalizado, timeout=5000):
            worker.start()

        assert spy.count() == 1
        worker.wait(1000)

    def test_score_cero_no_descarga_detalle(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Mock de motor con score 0, obtener_detalle nunca se llama."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Servicio de aseo"}
        ]

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(0, []),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        mock_cliente.obtener_detalle.assert_not_called()
        worker.wait(1000)

    def test_score_positivo_descarga_detalle(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Mock de motor con score > 0, obtener_detalle se llama una vez."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Compra de sillas"}
        ]
        mock_cliente.obtener_detalle.return_value = {
            "CodigoExterno": "L1",
            "Descripcion": "Sillas de oficina",
            "Comprador": {"CodigoOrganismo": "ORG1", "NombreOrganismo": "Test"},
        }

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(10, ["[TÍTULO] 'silla' (+10)"]),
        ), patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_detalle",
            return_value=(5, ["[DESC] 'silla' (+5)"]),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        mock_cliente.obtener_detalle.assert_called_once_with("L1")
        worker.wait(1000)

    def test_upsert_llamado_por_cada_licitacion(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Verificar que repo_licitaciones.upsert() se llama por cada licitación."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Item uno"},
            {"CodigoExterno": "L2", "Nombre": "Item dos"},
        ]

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(0, []),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        # upsert debe llamarse 2 veces (una por cada licitación del día)
        assert mock_repo_lic.upsert.call_count == 2
        worker.wait(1000)

    def test_detener_interrumpe_el_loop(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """detener() durante ejecución, worker para antes de procesar todos los días."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        def licitaciones_por_dia(fecha):
            return [{"CodigoExterno": f"L-{fecha}", "Nombre": f"Item {fecha}"}]

        mock_cliente.obtener_licitaciones_dia.side_effect = licitaciones_por_dia

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(0, []),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-10",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            worker.start()
            qtbot.wait(50)
            worker.detener()
            ok = worker.wait(3000)

        assert ok, "Worker no terminó dentro del timeout tras detener()"
        assert mock_repo_lic.upsert.call_count >= 1

    def test_reintenta_en_error_500(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Mock de API que falla (1er día) y luego tiene éxito (2do día).
        El worker emite error para el día que falla, pero finalizado para
        el rango completo."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        # Primer día falla, segundo día vacío (sin licitaciones = éxito)
        mock_cliente.obtener_licitaciones_dia.side_effect = [
            Exception("Error 500 del servidor"),
            [],
        ]

        worker = ExtraccionWorker(
            fecha_inicio="2026-01-01",
            fecha_fin="2026-01-02",
            cliente_mp=mock_cliente,
            repo_licitaciones=mock_repo_lic,
            repo_reglas=mock_repo_reglas,
            gestor_reglas=mock_gestor,
        )
        spy_error = QSignalSpy(worker.error)
        spy_fin = QSignalSpy(worker.finalizado)

        with qtbot.waitSignal(worker.finalizado, timeout=5000):
            worker.start()

        # El worker emite error para el día fallido PERO también finalizado
        assert spy_error.count() >= 1
        assert spy_fin.count() == 1
        worker.wait(1000)

    def test_score_positivo_detalle_con_items_dict(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Score>0, detalle con Items como dict — productos_str es join de valores."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Compra de sillas"}
        ]
        mock_cliente.obtener_detalle.return_value = {
            "CodigoExterno": "L1",
            "Descripcion": "Sillas de oficina",
            "Items": {"1": "Silla ergonómica", "2": "Silla ejecutiva"},
            "Comprador": {"CodigoOrganismo": "ORG1"},
        }

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(10, ["[TÍTULO] 'silla' (+10)"]),
        ), patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_detalle",
            return_value=(3, []),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        mock_repo_lic.upsert.assert_called_once()
        args, _ = mock_repo_lic.upsert.call_args
        datos = args[0]
        assert datos["detalle_productos"] == "Silla ergonómica Silla ejecutiva"
        assert datos["tiene_detalle"] is True
        assert datos["etapa"] == "candidata"
        worker.wait(1000)

    def test_score_positivo_detalle_comprador_no_dict(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Score>0, Comprador no es dict — codigo_org = ''."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Sillas oficina"}
        ]
        mock_cliente.obtener_detalle.return_value = {
            "CodigoExterno": "L1",
            "Descripcion": "Sillas",
            "Comprador": "No un dict",
        }

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(10, ["[TÍTULO] 'silla' (+10)"]),
        ), patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_detalle",
            return_value=(0, []),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        mock_repo_lic.upsert.assert_called_once()
        args, _ = mock_repo_lic.upsert.call_args
        datos = args[0]
        assert datos["tiene_detalle"] is True
        assert datos["etapa"] == "candidata"
        worker.wait(1000)

    def test_score_positivo_detalle_no_encontrado(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Score>0, obtener_detalle retorna None — upsert con tiene_detalle=False."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Sillas oficina"}
        ]
        mock_cliente.obtener_detalle.return_value = None

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(10, ["[TÍTULO] 'silla' (+10)"]),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        mock_repo_lic.upsert.assert_called_once()
        args, _ = mock_repo_lic.upsert.call_args
        datos = args[0]
        assert datos["tiene_detalle"] is False
        assert datos["etapa"] == "candidata"
        assert datos["score_total"] == 10  # solo score_resumen
        worker.wait(1000)

    def test_emite_avance_cada_10(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Con 25 licitaciones en un día, avance se emite 2 veces (10 y 20)."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": f"L{i}", "Nombre": f"Item {i}"}
            for i in range(25)
        ]

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(0, []),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            spy_avance = QSignalSpy(worker.avance)

            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        # Con 25 licitaciones emite avance en 10 y 20 → 2 veces
        assert spy_avance.count() == 2
        worker.wait(1000)

    def test_extrae_fecha_publicacion_del_detalle(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """fecha_publicacion se extrae del detalle y se pasa a upsert()."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Compra de sillas"}
        ]
        mock_cliente.obtener_detalle.return_value = {
            "CodigoExterno": "L1",
            "Descripcion": "Sillas de oficina",
            "FechaPublicacion": "2026-01-15T10:30:00",
            "Comprador": {"CodigoOrganismo": "ORG1"},
        }

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(10, ["[TÍTULO] 'silla' (+10)"]),
        ), patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_detalle",
            return_value=(0, []),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        mock_repo_lic.upsert.assert_called_once()
        args, _ = mock_repo_lic.upsert.call_args
        datos = args[0]
        assert "fecha_publicacion" in datos
        # Debe ser un datetime, no un string
        from datetime import datetime

        assert isinstance(datos["fecha_publicacion"], datetime)
        assert datos["fecha_publicacion"].year == 2026
        assert datos["fecha_publicacion"].month == 1
        assert datos["fecha_publicacion"].day == 15
        worker.wait(1000)

    def test_fecha_publicacion_es_none_sin_detalle(
        self,
        qtbot: QtBot,
        mock_cliente,
        mock_repo_lic,
        mock_repo_reglas,
        mock_gestor,
    ):
        """Sin detalle, fecha_publicacion debe ser None."""
        from monitor_licitaciones.workers.extraccion_worker import (
            ExtraccionWorker,
        )

        mock_cliente.obtener_licitaciones_dia.return_value = [
            {"CodigoExterno": "L1", "Nombre": "Compra de sillas"}
        ]
        mock_cliente.obtener_detalle.return_value = None

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.evaluar_titulo",
            return_value=(10, ["[TÍTULO] 'silla' (+10)"]),
        ):
            worker = ExtraccionWorker(
                fecha_inicio="2026-01-01",
                fecha_fin="2026-01-01",
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            with qtbot.waitSignal(worker.finalizado, timeout=5000):
                worker.start()

        mock_repo_lic.upsert.assert_called_once()
        args, _ = mock_repo_lic.upsert.call_args
        datos = args[0]
        assert datos.get("fecha_publicacion") is None
        worker.wait(1000)
