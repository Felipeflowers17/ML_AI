"""Tests para config.py — constantes globales y validación de entorno.

TDD: estos tests se escribieron ANTES de implementar config.py.
"""

import pytest
from monitor_licitaciones.config import (
    API_MAX_INTENTOS,
    API_PAUSA_SEGUNDOS,
    API_TIMEOUT_SEGUNDOS,
    CODIGO_ESTADO_PUBLICADA,
    ETAPA_CANDIDATA,
    ETAPA_IGNORADA,
    ETAPA_OFERTADA,
    ETAPA_SEGUIMIENTO,
    ETAPAS_ACTIVAS,
    EXPORT_CHUNK_SIZE,
    PILOTO_ACTIVO,
    PILOTO_HORA,
    PILOTO_HORA_DEFAULT,
    PILOTO_ULTIMA_EJECUCION,
    PILOTO_ULTIMO_ERROR,
    TAMANIO_PAGINA,
)


class TestEtapas:
    """Constantes de etapas del pipeline."""

    def test_etapas_activas_contiene_exactamente_tres_etapas(self):
        """ETAPAS_ACTIVAS tiene exactamente candidata, seguimiento, ofertada."""
        assert ETAPAS_ACTIVAS == [ETAPA_CANDIDATA, ETAPA_SEGUIMIENTO, ETAPA_OFERTADA]

    def test_etapas_activas_no_contiene_ignorada(self):
        """'ignorada' no debe estar en ETAPAS_ACTIVAS."""
        assert ETAPA_IGNORADA not in ETAPAS_ACTIVAS


class TestConstantes:
    """Valores exactos de constantes."""

    def test_piloto_hora_default_es_22_30(self):
        """Valor por defecto de la hora del piloto."""
        assert PILOTO_HORA_DEFAULT == "22:30"

    def test_codigo_estado_publicada_es_5(self):
        """Código de estado 'Publicada' en API Mercado Público."""
        assert CODIGO_ESTADO_PUBLICADA == 5

    def test_todas_las_constantes_son_strings_o_numeros(self):
        """Ninguna constante es None — verificación de integridad."""
        constantes = [
            ETAPA_CANDIDATA,
            ETAPA_SEGUIMIENTO,
            ETAPA_OFERTADA,
            ETAPA_IGNORADA,
            ETAPAS_ACTIVAS,
            CODIGO_ESTADO_PUBLICADA,
            PILOTO_HORA_DEFAULT,
            API_PAUSA_SEGUNDOS,
            API_MAX_INTENTOS,
            API_TIMEOUT_SEGUNDOS,
            TAMANIO_PAGINA,
            EXPORT_CHUNK_SIZE,
            PILOTO_ACTIVO,
            PILOTO_HORA,
            PILOTO_ULTIMA_EJECUCION,
            PILOTO_ULTIMO_ERROR,
        ]
        for c in constantes:
            assert c is not None, f"Constante es None: {c!r}"


class TestFailFast:
    """Validación de fail-fast en main.py — función validar_entorno()."""

    def test_fail_fast_con_database_url_faltante(self, monkeypatch):
        """Si falta DATABASE_URL, validar_entorno() retorna False."""
        monkeypatch.setattr("monitor_licitaciones.main.load_dotenv", lambda: None)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("TICKET_MERCADO_PUBLICO", "test_ticket")

        from monitor_licitaciones.main import validar_entorno

        assert validar_entorno() is False

    def test_fail_fast_con_ticket_faltante(self, monkeypatch):
        """Si falta TICKET_MERCADO_PUBLICO, validar_entorno() retorna False."""
        monkeypatch.setattr("monitor_licitaciones.main.load_dotenv", lambda: None)
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.delenv("TICKET_MERCADO_PUBLICO", raising=False)

        from monitor_licitaciones.main import validar_entorno

        assert validar_entorno() is False

    def test_fail_fast_con_ambas_presentes_retorna_true(self, monkeypatch):
        """Con ambas variables, validar_entorno() retorna True."""
        monkeypatch.setattr("monitor_licitaciones.main.load_dotenv", lambda: None)
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        monkeypatch.setenv("TICKET_MERCADO_PUBLICO", "test_ticket")

        from monitor_licitaciones.main import validar_entorno

        assert validar_entorno() is True
