"""Tests para PilotoWorker — QThread de ejecución automática programada.

Usa mocks de repositorio de configuración y time.sleep para controlar
el timing del worker. Verifica condiciones de hora, persistencia de
fecha de ejecución y comportamiento de reintentos.
"""

import threading
import time as time_module
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from monitor_licitaciones.config import PILOTO_ULTIMO_ERROR
from PySide6.QtTest import QSignalSpy
from pytestqt.qtbot import QtBot


@pytest.fixture
def mock_repo_config():
    repo = MagicMock()
    repo.obtener_todas.return_value = {
        "piloto_activo": "true",
        "piloto_hora": "22:30",
        "piloto_ultima_ejecucion": None,
        "piloto_ultimo_error": "",
    }
    return repo


class TestPilotoWorker:
    """Suite de tests para PilotoWorker."""

    def test_no_ejecuta_si_ya_se_ejecuto_hoy(
        self,
        qtbot: QtBot,
        mock_repo_config,
    ):
        """repo_config devuelve fecha de hoy en PILOTO_ULTIMA_EJECUCION,
        extraccion_iniciada no se emite."""
        from monitor_licitaciones.workers.piloto_worker import PilotoWorker

        hoy = datetime.now().strftime("%Y-%m-%d")
        mock_repo_config.obtener_todas.return_value = {
            "piloto_activo": "true",
            "piloto_hora": datetime.now().strftime("%H:%M"),
            "piloto_ultima_ejecucion": hoy,
            "piloto_ultimo_error": "",
        }

        worker = PilotoWorker(repo_config=mock_repo_config)
        spy_iniciada = QSignalSpy(worker.extraccion_iniciada)

        worker._ejecutando = True
        with patch("monitor_licitaciones.workers.piloto_worker.time.sleep"):
            worker._iterar_ciclo()
            worker.detener()

        assert spy_iniciada.count() == 0
        worker.wait(1000)

    def test_ejecuta_si_es_la_hora_y_no_se_ejecuto(
        self,
        qtbot: QtBot,
        mock_repo_config,
    ):
        """Hora coincide, fecha distinta, extraccion_iniciada se emite."""
        from monitor_licitaciones.workers.piloto_worker import PilotoWorker

        ahora = datetime.now()
        mock_repo_config.obtener_todas.return_value = {
            "piloto_activo": "true",
            "piloto_hora": ahora.strftime("%H:%M"),
            "piloto_ultima_ejecucion": "2020-01-01",
            "piloto_ultimo_error": "",
        }

        worker = PilotoWorker(repo_config=mock_repo_config)
        spy_iniciada = QSignalSpy(worker.extraccion_iniciada)

        worker._ejecutando = True
        with patch(
            "monitor_licitaciones.workers.piloto_worker.time.sleep"
        ), patch.object(worker, "_ejecutar_extraccion_real"):
            worker._iterar_ciclo()
            worker.detener()

        assert spy_iniciada.count() == 1
        worker.wait(1000)

    def test_lee_config_de_bd_en_cada_ciclo(
        self,
        qtbot: QtBot,
        mock_repo_config,
    ):
        """Cambiar la config entre ciclos afecta el comportamiento
        del siguiente ciclo sin reiniciar el worker."""
        from monitor_licitaciones.workers.piloto_worker import PilotoWorker

        ahora = datetime.now()

        # Primer ciclo: inactivo
        mock_repo_config.obtener_todas.return_value = {
            "piloto_activo": "false",
            "piloto_hora": ahora.strftime("%H:%M"),
            "piloto_ultima_ejecucion": None,
            "piloto_ultimo_error": "",
        }

        worker = PilotoWorker(repo_config=mock_repo_config)
        spy_iniciada = QSignalSpy(worker.extraccion_iniciada)

        worker._ejecutando = True
        with patch(
            "monitor_licitaciones.workers.piloto_worker.time.sleep"
        ), patch.object(worker, "_ejecutar_extraccion_real"):
            worker._iterar_ciclo()
            ciclo_1_calls = spy_iniciada.count()

            # Segundo ciclo: activo
            mock_repo_config.obtener_todas.return_value = {
                "piloto_activo": "true",
                "piloto_hora": ahora.strftime("%H:%M"),
                "piloto_ultima_ejecucion": None,
                "piloto_ultimo_error": "",
            }
            worker._iterar_ciclo()
            worker.detener()

        assert ciclo_1_calls == 0
        assert spy_iniciada.count() == 1
        worker.wait(1000)

    def test_sleep_interrumpible_responde_a_detener(
        self,
        qtbot: QtBot,
        mock_repo_config,
    ):
        """detener() durante el sleep de 60s, el worker termina en menos de 2 segundos."""
        from monitor_licitaciones.workers.piloto_worker import PilotoWorker

        worker = PilotoWorker(repo_config=mock_repo_config)
        worker._ejecutando = True

        resultado = []

        def dormir():
            worker._sleep_interrumpible(60)
            resultado.append("fin")

        hilo = threading.Thread(target=dormir, daemon=True)
        hilo.start()

        time_module.sleep(0.2)
        worker.detener()

        hilo.join(2.0)
        assert len(resultado) == 1
        assert not hilo.is_alive()
        worker.wait(1000)

    def test_persiste_error_tras_agotar_reintentos(
        self,
        qtbot: QtBot,
        mock_repo_config,
    ):
        """Extracción siempre falla, repo_config.guardar(PILOTO_ULTIMO_ERROR)
        se llama y error_ocurrido se emite."""
        from monitor_licitaciones.workers.piloto_worker import PilotoWorker

        worker = PilotoWorker(repo_config=mock_repo_config)
        spy_error = QSignalSpy(worker.error_ocurrido)

        def extraccion_siempre_falla():
            raise Exception("Error de conexión")

        with patch(
            "monitor_licitaciones.workers.piloto_worker.time.sleep"
        ):
            worker._ejecutar_con_reintentos(
                datetime.now(), extraccion_siempre_falla
            )

        args_list = [
            call_args[0]
            for call_args in mock_repo_config.guardar.call_args_list
        ]
        claves_guardadas = [args[0] for args in args_list]
        assert PILOTO_ULTIMO_ERROR in claves_guardadas

        assert spy_error.count() >= 1
        worker.wait(1000)


class TestEjecutarExtraccionReal:
    """Tests para _ejecutar_extraccion_real() del PilotoWorker."""

    def test_ejecuta_extraccion_para_dia_anterior(
        self, qtbot, mock_repo_config
    ):
        """_ejecutar_extraccion_real() crea ExtraccionWorker con fecha del día anterior."""
        from unittest.mock import MagicMock, patch
        from datetime import datetime, timedelta

        from monitor_licitaciones.workers.piloto_worker import PilotoWorker

        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Mock de las dependencias
        mock_cliente = MagicMock()
        mock_repo_lic = MagicMock()
        mock_repo_reglas = MagicMock()
        mock_gestor = MagicMock()

        worker = PilotoWorker(
            repo_config=mock_repo_config,
            cliente_mp=mock_cliente,
            repo_licitaciones=mock_repo_lic,
            repo_reglas=mock_repo_reglas,
            gestor_reglas=mock_gestor,
        )

        with patch(
            "monitor_licitaciones.workers.extraccion_worker.ExtraccionWorker"
        ) as mock_extraccion_cls:
            mock_worker_instance = MagicMock()
            mock_extraccion_cls.return_value = mock_worker_instance

            worker._ejecutar_extraccion_real()

            # Verificar que ExtraccionWorker se creó con los parámetros correctos
            mock_extraccion_cls.assert_called_once_with(
                fecha_inicio=ayer,
                fecha_fin=ayer,
                cliente_mp=mock_cliente,
                repo_licitaciones=mock_repo_lic,
                repo_reglas=mock_repo_reglas,
                gestor_reglas=mock_gestor,
            )
            # Verificar que se ejecutó run()
            mock_worker_instance.run.assert_called_once()

    def test_lanza_error_sin_dependencias(
        self, qtbot, mock_repo_config
    ):
        """Sin dependencias de extracción, lanza RuntimeError."""
        from monitor_licitaciones.workers.piloto_worker import PilotoWorker

        worker = PilotoWorker(repo_config=mock_repo_config)

        with pytest.raises(RuntimeError, match="no tiene todas las dependencias"):
            worker._ejecutar_extraccion_real()

        worker.wait(1000)

    def test_reintentos_capturan_error_de_dependencias(
        self, qtbot, mock_repo_config
    ):
        """El RuntimeError de dependencias faltantes es capturado por reintentos."""
        from monitor_licitaciones.workers.piloto_worker import PilotoWorker
        from datetime import datetime

        worker = PilotoWorker(repo_config=mock_repo_config)
        spy_error = QSignalSpy(worker.error_ocurrido)

        with patch(
            "monitor_licitaciones.workers.piloto_worker.time.sleep"
        ):
            worker._ejecutar_con_reintentos(datetime.now())

        # Debe haber emitido error_ocurrido porque _ejecutar_extraccion_real()
        # falla con RuntimeError al no tener dependencias
        args_list = [
            call_args[0]
            for call_args in mock_repo_config.guardar.call_args_list
        ]
        claves_guardadas = [args[0] for args in args_list]
        assert PILOTO_ULTIMO_ERROR in claves_guardadas
        assert spy_error.count() >= 1
        worker.wait(1000)
