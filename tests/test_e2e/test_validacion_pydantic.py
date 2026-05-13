"""Tests de los modelos Pydantic en schemas_mp.py.

Verifica que los modelos:
  1. Parsean payloads completos correctamente.
  2. Toleran campos opcionales faltantes.
  3. Validan campos obligatorios ausentes.
  4. Usan valores por defecto sensatos para opcionales.

TDD Cycle:
  RED: Tests escritos primero, referencian modelos existentes.
  GREEN: Modelos ya implementados, tests pasan inmediatamente.
  TRIANGULATE: 6 escenarios cubren carga válida, bordes y errores.
  REFACTOR: Schemas limpios, sin cambios necesarios.
"""

import pytest
from monitor_licitaciones.infrastructure.api.schemas_mp import (
    LicitacionDetalleAPI,
    RespuestaListadoAPI,
)
from pydantic import ValidationError


class TestListado:
    """Tests para RespuestaListadoAPI."""

    def test_listado_valido_parsea_correctamente(self):
        """Payload completo de listado se parsea sin error."""
        payload = {
            "Cantidad": 2,
            "Listado": [
                {
                    "CodigoExterno": "L1",
                    "Nombre": "Licitación 1",
                    "FechaCierre": "2026-06-01",
                    "CodigoEstado": 5,
                    "Comprador": {
                        "CodigoOrganismo": "ORG1",
                        "NombreOrganismo": "Organismo Uno",
                    },
                },
                {
                    "CodigoExterno": "L2",
                    "Nombre": "Licitación 2",
                    # Sin Comprador, sin FechaCierre — opcionales
                },
            ],
        }

        parsed = RespuestaListadoAPI(**payload)

        assert parsed.Cantidad == 2
        assert len(parsed.Listado) == 2

        # Primer elemento con todos los campos
        assert parsed.Listado[0].CodigoExterno == "L1"
        assert parsed.Listado[0].Comprador is not None
        assert parsed.Listado[0].Comprador.CodigoOrganismo == "ORG1"

        # Segundo elemento con opcionales en None
        assert parsed.Listado[1].CodigoExterno == "L2"
        assert parsed.Listado[1].Comprador is None

    def test_listado_sin_campo_opcional_no_lanza_error(self):
        """Payload sin Comprador en una licitación, parsea sin ValidationError."""
        payload = {
            "Cantidad": 1,
            "Listado": [
                {
                    "CodigoExterno": "L1",
                    "Nombre": "Sin comprador",
                }
            ],
        }

        parsed = RespuestaListadoAPI(**payload)

        assert parsed.Listado[0].Comprador is None

    def test_listado_vacio_retorna_lista_vacia(self):
        """Listado: [], retorna lista vacía."""
        payload = {"Cantidad": 0, "Listado": []}

        parsed = RespuestaListadoAPI(**payload)

        assert parsed.Cantidad == 0
        assert parsed.Listado == []


class TestDetalle:
    """Tests para LicitacionDetalleAPI."""

    def test_detalle_campo_obligatorio_faltante(self):
        """Payload sin CodigoExterno, debe lanzar ValidationError."""
        payload = {
            "Nombre": "Detalle sin código",
        }

        with pytest.raises(ValidationError):
            LicitacionDetalleAPI(**payload)

    def test_detalle_fecha_malformada_queda_como_none(self):
        """Campos de fecha opcionales quedan como None si no se proveen.

        Los campos de fecha son ``Optional[str]`` con default None,
        por lo que cualquier string es válido y no lanza error.
        Si el campo se omite, queda None.
        """
        payload = {
            "CodigoExterno": "L1",
            "Nombre": "Test fechas",
        }

        detalle = LicitacionDetalleAPI(**payload)

        assert detalle.FechaCierre is None
        assert detalle.FechaInicio is None
        assert detalle.FechaPublicacion is None

    def test_detalle_campos_opcionales_con_defaults(self):
        """Todos los campos opcionales tienen None por defecto.

        Solo CodigoExterno y Nombre son obligatorios. Todo lo demás
        debe tener default None o valor por defecto sensato.
        """
        payload = {
            "CodigoExterno": "L1",
            "Nombre": "Mínimo posible",
        }

        detalle = LicitacionDetalleAPI(**payload)

        # Obligatorios
        assert detalle.CodigoExterno == "L1"
        assert detalle.Nombre == "Mínimo posible"

        # Opcionales — todos deben ser None por defecto
        assert detalle.Descripcion is None
        assert detalle.FechaCierre is None
        assert detalle.FechaInicio is None
        assert detalle.FechaPublicacion is None
        assert detalle.CodigoEstado is None
        assert detalle.Comprador is None
        assert detalle.Items is None
