"""Tests para el motor de scoring (funciones puras).

Strict TDD: estos tests se escribieron ANTES de la implementación.
Cada test describe comportamiento esperado del motor de scoring sin
ninguna dependencia de infraestructura.
"""

from monitor_licitaciones.domain.scoring.motor_scoring import (
    evaluar_detalle,
    evaluar_titulo,
)
from monitor_licitaciones.domain.scoring.tipos import ReglaScoring

# ---------------------------------------------------------------------------
# Fixture de reglas para todos los tests de scoring
# ---------------------------------------------------------------------------

REGLAS_TEST: list[ReglaScoring] = [
    ReglaScoring(
        termino="silla",
        peso_titulo=10,
        peso_descripcion=5,
        peso_productos=1,
    ),
    ReglaScoring(
        termino="mesa",
        peso_titulo=20,
        peso_descripcion=10,
        peso_productos=2,
    ),
]

# ---------------------------------------------------------------------------
# evaluar_titulo
# ---------------------------------------------------------------------------


class TestEvaluarTitulo:
    """Tests para evaluar_titulo(texto, reglas)."""

    def test_coincidencia_simple(self):
        """Texto con 'silla' → score 10, un motivo."""
        score, motivos = evaluar_titulo("Compra de silla de oficina", REGLAS_TEST)
        assert score == 10
        assert len(motivos) == 1
        assert "[TÍTULO]" in motivos[0]
        assert "'silla'" in motivos[0]

    def test_multiples_coincidencias(self):
        """Texto con 'silla' y 'mesa' → score 30 (10 + 20)."""
        score, motivos = evaluar_titulo(
            "Compra de silla y mesa de oficina", REGLAS_TEST
        )
        assert score == 30
        assert len(motivos) == 2

    def test_sin_coincidencias(self):
        """Texto sin términos buscados → (0, [])."""
        score, motivos = evaluar_titulo("Servicio de aseo", REGLAS_TEST)
        assert score == 0
        assert motivos == []

    def test_case_insensitive(self):
        """"SILLA" en mayúsculas coincide con regla 'silla'."""
        score, motivos = evaluar_titulo("COMPRA DE SILLA DE OFICINA", REGLAS_TEST)
        assert score == 10
        assert len(motivos) == 1

    def test_texto_none(self):
        """texto=None → (0, []) sin excepción."""
        score, motivos = evaluar_titulo(None, REGLAS_TEST)
        assert score == 0
        assert motivos == []

    def test_boundary_palabra_completa(self):
        """"sillas" (plural) NO coincide con 'silla' gracias a \\b."""
        score, motivos = evaluar_titulo("Compra de sillas de oficina", REGLAS_TEST)
        assert score == 0
        assert motivos == []


# ---------------------------------------------------------------------------
# evaluar_detalle
# ---------------------------------------------------------------------------


class TestEvaluarDetalle:
    """Tests para evaluar_detalle(descripcion, productos, reglas)."""

    def test_descripcion(self):
        """Texto en descripción suma peso_descripcion."""
        score, motivos = evaluar_detalle(
            "Descripción con silla", "productos varios", REGLAS_TEST
        )
        assert score == 5
        assert len(motivos) == 1
        assert "[DESC]" in motivos[0]

    def test_productos(self):
        """Texto en productos suma peso_productos."""
        score, motivos = evaluar_detalle(
            "descripción genérica", "silla ergonómica", REGLAS_TEST
        )
        assert score == 1
        assert len(motivos) == 1
        assert "[PROD]" in motivos[0]

    def test_textos_none(self):
        """descripcion=None y productos=None → (0, []) sin excepción."""
        score, motivos = evaluar_detalle(None, None, REGLAS_TEST)
        assert score == 0
        assert motivos == []

    def test_motivos_incluyen_termino_y_puntaje_con_signo(self):
        """El string de motivo contiene el término y el puntaje con '+'."""
        score, motivos = evaluar_titulo("mesa de comedor", REGLAS_TEST)
        assert score == 20
        assert len(motivos) == 1
        motivo = motivos[0]
        assert "'mesa'" in motivo
        assert "(+20)" in motivo
        assert motivo.startswith("[TÍTULO]")
