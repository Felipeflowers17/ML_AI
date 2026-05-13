"""Tests de integración para RepositorioReglas.

Usan SQLite in-memory vía los fixtures de conftest.py.
Cada test parte con BD limpia.
"""


from monitor_licitaciones.infrastructure.database.models import (
    Organismo,
    PalabraClave,
)


class TestPalabrasClave:
    """Pruebas de CRUD de palabras clave."""

    def test_guardar_y_obtener_palabra_clave(self, repo_reglas, session):
        """Insertar palabra clave y recuperarla."""
        creada = repo_reglas.guardar_palabra_clave({
            "termino": "silla",
            "peso_titulo": 10,
            "peso_descripcion": 5,
            "peso_productos": 1,
        })
        session.flush()
        assert creada.id is not None

        palabras = repo_reglas.obtener_palabras_clave()
        assert len(palabras) == 1
        assert palabras[0].termino == "silla"

    def test_obtener_palabras_clave_excluye_inactivas(
        self, repo_reglas, session
    ):
        """Reglas con activa=False no se incluyen en obtener_palabras_clave."""
        repo_reglas.guardar_palabra_clave({
            "termino": "silla",
            "peso_titulo": 10,
        })
        session.flush()

        repo_reglas.guardar_palabra_clave({
            "termino": "mesa",
            "peso_titulo": 20,
        })
        session.flush()

        # Eliminar "silla" (soft delete)
        repo_reglas.eliminar_palabra_clave(1)
        session.flush()

        palabras = repo_reglas.obtener_palabras_clave()
        assert len(palabras) == 1
        assert palabras[0].termino == "mesa"

    def test_eliminar_es_soft_delete(self, repo_reglas, session):
        """Eliminar no borra físicamente, solo pone activa=False."""
        repo_reglas.guardar_palabra_clave({
            "termino": "silla",
            "peso_titulo": 10,
        })
        session.flush()

        repo_reglas.eliminar_palabra_clave(1)
        session.flush()

        # Verificar que existe en BD pero con activa=False
        from sqlalchemy import select

        result = session.execute(
            select(PalabraClave).where(PalabraClave.id == 1)
        ).scalar_one()
        assert result.activa is False

    def test_guardar_palabra_clave_con_id_actualiza(
        self, repo_reglas, session
    ):
        """Guardar con id existente actualiza en lugar de insertar."""
        creada = repo_reglas.guardar_palabra_clave({
            "termino": "silla",
            "peso_titulo": 10,
        })
        session.flush()

        repo_reglas.guardar_palabra_clave({
            "id": creada.id,
            "termino": "silla actualizada",
            "peso_titulo": 20,
        })
        session.flush()

        palabras = repo_reglas.obtener_palabras_clave()
        assert len(palabras) == 1
        assert palabras[0].termino == "silla actualizada"
        assert palabras[0].peso_titulo == 20

    def test_eliminar_inexistente_retorna_false(self, repo_reglas):
        """Eliminar un id que no existe retorna False."""
        assert repo_reglas.eliminar_palabra_clave(999) is False


class TestOrganismos:
    """Pruebas de CRUD de organismos."""

    def test_obtener_organismos_vacio(self, repo_reglas):
        """Sin organismos, retorna lista vacía."""
        assert repo_reglas.obtener_organismos() == []

    def test_actualizar_puntaje_organismo(self, repo_reglas, session):
        """Actualizar puntaje_fijo de un organismo."""
        org = Organismo(codigo="ABC-123", nombre="Municipalidad Test")
        session.add(org)
        session.flush()

        assert repo_reglas.actualizar_puntaje_organismo("ABC-123", 50) is True
        session.flush()

        organismo = repo_reglas.obtener_organismos()[0]
        assert organismo.puntaje_fijo == 50

    def test_actualizar_puntaje_organismo_inexistente(self, repo_reglas):
        """Actualizar un organismo que no existe retorna False."""
        assert (
            repo_reglas.actualizar_puntaje_organismo("NO-EXISTE", 10) is False
        )

    def test_obtener_organismos_ordenados(self, repo_reglas, session):
        """Organismos se retornan ordenados por nombre."""
        session.add_all([
            Organismo(codigo="C", nombre="Zeta"),
            Organismo(codigo="B", nombre="Beta"),
            Organismo(codigo="A", nombre="Alfa"),
        ])
        session.flush()

        organismos = repo_reglas.obtener_organismos()
        assert [o.nombre for o in organismos] == ["Alfa", "Beta", "Zeta"]
