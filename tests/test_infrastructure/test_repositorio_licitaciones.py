"""Tests de integración para RepositorioLicitaciones.

Usan SQLite in-memory vía los fixtures de conftest.py.
Cada test parte con BD limpia gracias al fixture ``session`` (rollback).
"""


import pytest
from monitor_licitaciones.infrastructure.database.models import (
    Licitacion,
)
from sqlalchemy import text


@pytest.fixture(autouse=True)
def _limpiar_tablas(session):
    """Limpia las tablas antes de cada test (sin commit)."""
    for tabla in ["licitaciones", "estados_licitacion", "organismos"]:
        session.execute(text(f"DELETE FROM {tabla}"))
    session.flush()


@pytest.fixture
def repo(repo_licitaciones):
    return repo_licitaciones


def _crear_licitacion_simple(session, **kwargs) -> Licitacion:
    datos = {
        "codigo_externo": kwargs.get("codigo_externo", "L-001"),
        "nombre": kwargs.get("nombre", "Compra de sillas"),
        "etapa": kwargs.get("etapa", "candidata"),
        "score_total": kwargs.get("score_total", 10),
        "codigo_estado": kwargs.get("codigo_estado", None),
    }
    lic = Licitacion(**datos)
    session.add(lic)
    session.flush()
    return lic


class TestUpsert:
    """Pruebas del método upsert."""

    def test_upsert_inserta_nuevo(self, repo, session):
        """Licitación nueva se inserta correctamente."""
        resultado = repo.upsert({
            "codigo_externo": "L-001",
            "nombre": "Compra de sillas",
            "etapa": "candidata",
        })
        session.flush()
        assert resultado.id is not None
        assert resultado.codigo_externo == "L-001"
        assert resultado.nombre == "Compra de sillas"

    def test_upsert_actualiza_existente(self, repo, session):
        """Segunda llamada con mismo código actualiza campos."""
        repo.upsert({
            "codigo_externo": "L-001",
            "nombre": "Compra de sillas",
            "etapa": "candidata",
        })
        session.flush()

        repo.upsert({
            "codigo_externo": "L-001",
            "nombre": "Compra de sillas actualizada",
            "etapa": "candidata",
        })
        session.flush()

        assert repo.obtener_por_etapa("candidata", 0, 10)[0].nombre == (
            "Compra de sillas actualizada"
        )

    def test_upsert_no_retrocede_etapa_manual(self, repo, session):
        """Si etapa es 'seguimiento', upsert con 'candidata' no la pisa."""
        repo.upsert({
            "codigo_externo": "L-001",
            "nombre": "Test",
            "etapa": "seguimiento",
        })
        session.flush()

        repo.upsert({
            "codigo_externo": "L-001",
            "nombre": "Test",
            "etapa": "candidata",
        })
        session.flush()

        lic = repo.obtener_por_etapa("seguimiento", 0, 10)
        assert len(lic) == 1

    def test_upsert_asciende_de_ignorada_a_candidata(self, repo, session):
        """Si etapa es 'ignorada', upsert con 'candidata' la actualiza."""
        repo.upsert({
            "codigo_externo": "L-001",
            "nombre": "Test",
            "etapa": "ignorada",
        })
        session.flush()

        repo.upsert({
            "codigo_externo": "L-001",
            "nombre": "Test",
            "etapa": "candidata",
        })
        session.flush()

        lic = repo.obtener_por_etapa("candidata", 0, 10)
        assert len(lic) == 1


class TestObtenerPorEtapa:
    """Pruebas de paginación y filtro por etapa."""

    def test_obtener_por_etapa_paginacion(self, repo, session):
        """Respeta limit y offset, retorna solo la etapa pedida."""
        for i in range(5):
            _crear_licitacion_simple(
                session, codigo_externo=f"L-0{i}", nombre=f"Item {i}",
                etapa="candidata", score_total=i,
            )
        _crear_licitacion_simple(
            session, codigo_externo="L-99", nombre="Otra",
            etapa="seguimiento",
        )
        session.flush()

        pagina_0 = repo.obtener_por_etapa("candidata", pagina=0, por_pagina=3)
        assert len(pagina_0) == 3

        pagina_1 = repo.obtener_por_etapa("candidata", pagina=1, por_pagina=3)
        assert len(pagina_1) == 2

        # Orden descendente por score_total
        assert pagina_0[0].score_total >= pagina_0[-1].score_total

    def test_obtener_por_etapa_sin_resultados(self, repo):
        """Etapa sin datos retorna lista vacía."""
        assert repo.obtener_por_etapa("ofertada", 0, 10) == []


class TestBuscarPorTexto:
    """Pruebas de búsqueda ILIKE."""

    def test_buscar_por_texto_ilike_case_insensitive(self, repo, session):
        """Búsqueda con mayúsculas encuentra coincidencia en minúsculas."""
        _crear_licitacion_simple(
            session, codigo_externo="L-001", nombre="sillas de oficina",
            etapa="candidata",
        )
        session.flush()

        resultados = repo.buscar_por_texto("SILLAS", "candidata", 0, 10)
        assert len(resultados) == 1

    def test_buscar_por_texto_en_nombre_y_descripcion(self, repo, session):
        """El OR funciona en ambos campos."""
        lic1 = Licitacion(
            codigo_externo="L-001", nombre="mesa de reuniones",
            descripcion="Mueble para oficina", etapa="candidata",
        )
        lic2 = Licitacion(
            codigo_externo="L-002", nombre="servicio de aseo",
            descripcion="Limpieza de mesas", etapa="candidata",
        )
        session.add_all([lic1, lic2])
        session.flush()

        resultados = repo.buscar_por_texto("mesa", "candidata", 0, 10)
        assert len(resultados) == 2

    def test_buscar_por_texto_sin_coincidencias(self, repo, session):
        """Texto sin match retorna lista vacía."""
        _crear_licitacion_simple(
            session, codigo_externo="L-001", nombre="sillas",
            etapa="candidata",
        )
        session.flush()

        assert repo.buscar_por_texto("inexistente", "candidata", 0, 10) == []


class TestContarPorEtapa:
    """Pruebas del método contar_por_etapa."""

    def test_contar_por_etapa_retorna_ceros_cuando_no_hay_datos(self, repo):
        """Sin datos retorna diccionario con los tres valores en cero."""
        conteo = repo.contar_por_etapa()
        assert conteo == {"candidata": 0, "seguimiento": 0, "ofertada": 0}

    def test_contar_por_etapa_cuenta_correctamente(self, repo, session):
        """Con datos, retorna los conteos correctos."""
        for i in range(3):
            _crear_licitacion_simple(
                session, codigo_externo=f"L-0{i}", nombre=f"Item {i}",
                etapa="candidata",
            )
        _crear_licitacion_simple(
            session, codigo_externo="L-10", nombre="Seg",
            etapa="seguimiento",
        )
        _crear_licitacion_simple(
            session, codigo_externo="L-20", nombre="Of",
            etapa="ofertada",
        )
        _crear_licitacion_simple(
            session, codigo_externo="L-99", nombre="Ign",
            etapa="ignorada",
        )
        session.flush()

        conteo = repo.contar_por_etapa()
        assert conteo["candidata"] == 3
        assert conteo["seguimiento"] == 1
        assert conteo["ofertada"] == 1
        # ignorada no se cuenta
        assert sum(conteo.values()) == 5


class TestActualizarEtapa:
    """Pruebas de actualizar_etapa."""

    def test_actualizar_etapa_existente(self, repo, session):
        _crear_licitacion_simple(
            session, codigo_externo="L-001", etapa="candidata",
        )
        session.flush()

        assert repo.actualizar_etapa("L-001", "seguimiento") is True
        session.flush()

        lic = repo.obtener_por_etapa("seguimiento", 0, 10)
        assert len(lic) == 1

    def test_actualizar_etapa_inexistente(self, repo):
        assert repo.actualizar_etapa("NO-EXISTE", "candidata") is False


class TestActualizarScore:
    """Pruebas de actualizar_score."""

    def test_actualizar_score_actualiza_tres_campos(self, repo, session):
        _crear_licitacion_simple(
            session, codigo_externo="L-001", score_total=0,
        )
        session.flush()

        repo.actualizar_score(
            "L-001",
            score_resumen=10,
            score_detalle=5,
            score_total=15,
            justificacion="[TÍTULO] 'silla' (+10), [DESC] 'silla' (+5)",
        )
        session.flush()

        lic = repo.obtener_por_etapa("candidata", 0, 10)[0]
        assert lic.score_resumen == 10
        assert lic.score_detalle == 5
        assert lic.score_total == 15

    def test_actualizar_score_inexistente(self, repo):
        assert repo.actualizar_score("NO-EXISTE", 10, 5, 15, "") is False
