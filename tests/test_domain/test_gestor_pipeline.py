"""Tests para GestorPipeline — lógica de transiciones entre etapas.

Strict TDD: estos tests se escribieron ANTES de la implementación.
Verifican que las transiciones válidas e inválidas se comportan según
las reglas del pipeline definidas en el diseño.
"""

from monitor_licitaciones.domain.pipeline.gestor_pipeline import (
    GestorPipeline,
)


class TestGestorPipeline:
    """Tests de la lógica de transiciones del pipeline."""

    def setup_method(self):
        self.pipeline = GestorPipeline()

    # -- Transiciones válidas -------------------------------------------------

    def test_transicion_valida_candidata_seguimiento(self):
        """candidata → seguimiento es válida."""
        assert self.pipeline.es_transicion_valida("candidata", "seguimiento") is True

    def test_transicion_valida_candidata_ofertada(self):
        """candidata → ofertada es válida."""
        assert self.pipeline.es_transicion_valida("candidata", "ofertada") is True

    # -- Transiciones inválidas -----------------------------------------------

    def test_transicion_invalida_retorna_false(self):
        """ignorada → seguimiento NO es válida."""
        assert self.pipeline.es_transicion_valida("ignorada", "seguimiento") is False

    def test_ignorada_solo_puede_ir_a_candidata(self):
        """Desde ignorada, solo candidata es destino válido."""
        destinos = self.pipeline.destinos_disponibles("ignorada")
        assert destinos == ["candidata"]

    # -- Destinos disponibles -------------------------------------------------

    def test_destinos_disponibles_candidata(self):
        """Desde candidata, se puede ir a seguimiento u ofertada."""
        destinos = self.pipeline.destinos_disponibles("candidata")
        assert destinos == ["seguimiento", "ofertada"]
        # Verificar orden exacto
        assert len(destinos) == 2

    def test_destinos_disponibles_etapa_desconocida(self):
        """Etapa que no está en TRANSICIONES_VALIDAS retorna lista vacía."""
        destinos = self.pipeline.destinos_disponibles("inexistente")
        assert destinos == []

        destinos = self.pipeline.destinos_disponibles("")
        assert destinos == []
