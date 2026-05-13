"""Tests para ClienteAPI usando la librería responses para mock HTTP.

TDD Cycle:
  RED: Tests escritos primero, referencian código existente de cliente_mp.py.
  GREEN: ClienteAPI ya implementado, tests pasan inmediatamente.
  TRIANGULATE: Múltiples escenarios cubren éxito, errores, reintentos y pausa.
  REFACTOR: Código limpio, sin cambios necesarios.
"""

from unittest.mock import patch

import pytest
import responses
from monitor_licitaciones.config import API_MAX_INTENTOS, API_PAUSA_SEGUNDOS
from monitor_licitaciones.infrastructure.api.cliente_mp import ClienteAPI


@pytest.fixture
def mock_resp():
    """Fixture que activa responses.RequestsMock para cada test."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(autouse=True)
def mock_time():
    """Mock time.time y time.sleep para evitar esperas reales.

    Con time.time() = 0.0 constante, _esperar_pausa() siempre detecta
    que no ha pasado tiempo y llama a sleep(), que es no-op.
    Esto hace todos los tests de cliente_mp rápidos (<100ms) sin
    modificar la lógica de pausa ni reintentos.
    """
    with patch("monitor_licitaciones.infrastructure.api.cliente_mp.time") as mock:
        mock.time.return_value = 0.0
        mock.sleep.return_value = None
        yield mock


class TestObtenerLicitacionesDia:
    """Tests para ClienteAPI.obtener_licitaciones_dia()."""

    URL = ClienteAPI.BASE_URL

    def test_obtener_licitaciones_dia_exitoso(self, mock_resp):
        """Mock 200 con payload válido, retorna lista parseada con longitud correcta."""
        mock_resp.get(
            self.URL,
            json={
                "Cantidad": 2,
                "Listado": [
                    {
                        "CodigoExterno": "L1",
                        "Nombre": "Licitación 1",
                        "Comprador": {
                            "CodigoOrganismo": "ORG1",
                            "NombreOrganismo": "Orguno",
                        },
                    },
                    {
                        "CodigoExterno": "L2",
                        "Nombre": "Licitación 2",
                    },
                ],
            },
            status=200,
        )

        cliente = ClienteAPI(ticket="test_ticket")
        resultado = cliente.obtener_licitaciones_dia("01012026")

        assert len(resultado) == 2
        assert resultado[0]["CodigoExterno"] == "L1"
        assert resultado[1]["CodigoExterno"] == "L2"

    def test_obtener_licitaciones_dia_respuesta_sin_listado(self, mock_resp):
        """Payload sin clave 'Listado', retorna [] sin excepción."""
        mock_resp.get(self.URL, json={"Cantidad": 0}, status=200)

        cliente = ClienteAPI(ticket="test_ticket")
        resultado = cliente.obtener_licitaciones_dia("01012026")

        assert resultado == []


class TestObtenerDetalle:
    """Tests para ClienteAPI.obtener_detalle()."""

    URL = ClienteAPI.BASE_URL

    def test_obtener_detalle_exitoso(self, mock_resp):
        """Mock 200 con detalle, retorna dict con CodigoExterno."""
        mock_resp.get(
            self.URL,
            json={"CodigoExterno": "L1", "Nombre": "Detalle Test"},
            status=200,
        )

        cliente = ClienteAPI(ticket="test_ticket")
        resultado = cliente.obtener_detalle("L1")

        assert resultado is not None
        assert resultado["CodigoExterno"] == "L1"
        assert resultado["Nombre"] == "Detalle Test"

    def test_obtener_detalle_404_retorna_none(self, mock_resp):
        """Mock 404, retorna None sin lanzar excepción."""
        mock_resp.get(self.URL, status=404)

        cliente = ClienteAPI(ticket="test_ticket")
        resultado = cliente.obtener_detalle("L1")

        assert resultado is None

    def test_obtener_detalle_reintenta_en_500(self, mock_resp):
        """Mock 500 seguido de 200, la segunda llamada retorna datos.

        Verifica que el reintento con backoff funciona correctamente
        y que el error transitorio no propaga al llamador.
        """
        mock_resp.get(self.URL, status=500)
        mock_resp.get(
            self.URL,
            json={"CodigoExterno": "L1", "Nombre": "Ok"},
            status=200,
        )

        cliente = ClienteAPI(ticket="test_ticket")
        resultado = cliente.obtener_detalle("L1")

        assert resultado is not None
        assert resultado["CodigoExterno"] == "L1"

    def test_obtener_detalle_agota_reintentos(self, mock_resp):
        """3 mocks 500 consecutivos, retorna None sin lanzar excepción."""
        for _ in range(API_MAX_INTENTOS):
            mock_resp.get(self.URL, status=500)

        cliente = ClienteAPI(ticket="test_ticket")
        resultado = cliente.obtener_detalle("L1")

        assert resultado is None


class TestPausaEntrePeticiones:
    """Tests para la pausa mínima entre peticiones."""

    URL = ClienteAPI.BASE_URL

    def test_pausa_entre_peticiones(self, mock_resp):
        """Dos llamadas consecutivas, el tiempo transcurrido es >= API_PAUSA_SEGUNDOS.

        Con time.time() = 0.0 constante, _esperar_pausa() siempre detecta
        que no ha pasado tiempo suficiente entre llamadas y debe dormir.
        """
        sleeps: list[float] = []

        with patch("monitor_licitaciones.infrastructure.api.cliente_mp.time") as mock:
            mock.time.return_value = 0.0
            mock.sleep.side_effect = lambda s: sleeps.append(s)

            mock_resp.get(
                self.URL,
                json={"CodigoExterno": "L1", "Nombre": "A"},
                status=200,
            )
            mock_resp.get(
                self.URL,
                json={"CodigoExterno": "L2", "Nombre": "B"},
                status=200,
            )

            cliente = ClienteAPI(ticket="test_ticket")
            cliente.obtener_detalle("L1")
            cliente.obtener_detalle("L2")

        # Al menos una sleep >= API_PAUSA_SEGUNDOS debe ocurrir
        # (la pausa entre la primera y segunda llamada, o la inicial)
        assert any(s >= API_PAUSA_SEGUNDOS for s in sleeps), (
            f"Ninguna sleep alcanzó el mínimo de {API_PAUSA_SEGUNDOS}s. "
            f"Sleeps registradas: {sleeps}"
        )
