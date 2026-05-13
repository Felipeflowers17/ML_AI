"""Cliente HTTP para la API de Mercado Público Chile.

Usa los schemas Pydantic de ``schemas_mp.py`` para validar respuestas.
Implementa reintentos con backoff exponencial y pausa mínima entre
peticiones.
"""

import time
from typing import Any

import requests
from loguru import logger

from monitor_licitaciones.config import (
    API_BASE_RETRASO,
    API_MAX_INTENTOS,
    API_PAUSA_SEGUNDOS,
    API_TIMEOUT_SEGUNDOS,
)
from monitor_licitaciones.infrastructure.api.schemas_mp import (
    LicitacionDetalleAPI,
    RespuestaListadoAPI,
)


class ClienteAPI:
    """Cliente para la API pública de Mercado Público.

    Args:
        ticket: Token de autenticación (TICKET_MERCADO_PUBLICO).
    """

    BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"

    def __init__(self, ticket: str):
        self._ticket = ticket
        self._ultima_peticion: float = 0.0

    def _esperar_pausa(self) -> None:
        """Espera el tiempo mínimo entre peticiones."""
        transcurrido = time.time() - self._ultima_peticion
        if transcurrido < API_PAUSA_SEGUNDOS:
            time.sleep(API_PAUSA_SEGUNDOS - transcurrido)

    def _request(
        self, params: dict[str, str] | None = None
    ) -> requests.Response | None:
        """Ejecuta una petición GET con reintentos y backoff."""
        self._esperar_pausa()
        for intento in range(1, API_MAX_INTENTOS + 1):
            try:
                resp = requests.get(
                    self.BASE_URL,
                    params=params,
                    timeout=API_TIMEOUT_SEGUNDOS,
                )
                if resp.status_code == 200:
                    self._ultima_peticion = time.time()
                    return resp
                if resp.status_code == 404:
                    # Error definitivo — no reintentar
                    return resp
                # 5xx — reintentar
                logger.warning(
                    "Intento {}/{}: HTTP {}", intento, API_MAX_INTENTOS, resp.status_code
                )
            except requests.RequestException as e:
                logger.warning(
                    "Intento {}/{}: error de red {}", intento, API_MAX_INTENTOS, e
                )

            if intento < API_MAX_INTENTOS:
                time.sleep(API_BASE_RETRASO ** intento)

        return None

    def obtener_licitaciones_dia(self, fecha: str) -> list[dict[str, Any]]:
        """Obtiene el listado de licitaciones publicadas en una fecha.

        Args:
            fecha: Formato DDMMYYYY.

        Returns:
            Lista de dicts con datos de licitaciones. Vacía si hay error.
        """
        params: dict[str, str] = {
            "ticket": self._ticket,
            "fechaPublicacion": fecha,
        }
        resp = self._request(params)
        if resp is None or resp.status_code != 200:
            logger.error("Error al obtener listado del día {}", fecha)
            return []

        try:
            data = resp.json()
            parsed = RespuestaListadoAPI(**data)
            return [item.model_dump() for item in parsed.Listado]
        except Exception as e:
            logger.error("Error al parsear listado del día {}: {}", fecha, e)
            return []

    def obtener_detalle(self, codigo_externo: str) -> dict[str, Any] | None:
        """Obtiene el detalle completo de una licitación.

        Args:
            codigo_externo: Código de la licitación.

        Returns:
            Dict con datos o ``None`` si hay error definitivo.
        """
        params: dict[str, str] = {
            "ticket": self._ticket,
            "codigo": codigo_externo,
        }
        resp = self._request(params)
        if resp is None:
            logger.error("Detalle de {}: agotados reintentos", codigo_externo)
            return None
        if resp.status_code == 404:
            logger.warning("Detalle de {}: 404 no encontrado", codigo_externo)
            return None
        if resp.status_code != 200:
            logger.error(
                "Detalle de {}: HTTP {} inesperado", codigo_externo, resp.status_code
            )
            return None

        try:
            data = resp.json()
            parsed = LicitacionDetalleAPI(**data)
            return parsed.model_dump()
        except Exception as e:
            logger.error(
                "Error al parsear detalle de {}: {}", codigo_externo, e
            )
            return None

    def obtener_organismos(self) -> list[dict[str, Any]]:
        """Obtiene el catálogo de organismos (BuscarComprador).

        Usado solo por el comando ``seed``, no en extracción rutinaria.
        """
        url = "https://api.mercadopublico.cl/servicios/v1/publico/BuscarComprador.json"
        params = {"ticket": self._ticket}
        try:
            resp = requests.get(url, params=params, timeout=API_TIMEOUT_SEGUNDOS)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("Listado", [])
        except Exception as e:
            logger.error("Error al obtener organismos: {}", e)
        return []
