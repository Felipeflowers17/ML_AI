"""Repositorio de reglas — palabras clave y organismos.

Cinco métodos que cubren CRUD de palabras clave (con soft delete)
y consulta/actualización de puntajes de organismos.
"""

from monitor_licitaciones.infrastructure.database.models import (
    Organismo,
    PalabraClave,
)
from sqlalchemy.orm import Session


class RepositorioReglas:
    """Repositorio para palabras clave y organismos."""

    def __init__(self, session: Session):
        self._session = session

    def obtener_palabras_clave(self) -> list[PalabraClave]:
        """Retorna solo palabras clave activas."""
        return (
            self._session.query(PalabraClave)
            .filter(PalabraClave.activa)
            .all()
        )

    def guardar_palabra_clave(self, datos: dict) -> PalabraClave:
        """INSERT si sin ``id``, UPDATE si con ``id``."""
        if "id" in datos and datos["id"] is not None:
            instancia: PalabraClave | None = (
                self._session.query(PalabraClave)
                .filter(PalabraClave.id == datos["id"])
                .first()
            )
            if instancia:
                for campo, valor in datos.items():
                    if campo != "id":
                        setattr(instancia, campo, valor)
                return instancia

        instancia = PalabraClave(**datos)
        self._session.add(instancia)
        return instancia

    def eliminar_palabra_clave(self, id: int) -> bool:
        """Soft delete: pone ``activa=False`` en lugar de borrar."""
        instancia: PalabraClave | None = (
            self._session.query(PalabraClave)
            .filter(PalabraClave.id == id)
            .first()
        )
        if instancia is None:
            return False
        instancia.activa = False
        return True

    def obtener_organismos(self) -> list[Organismo]:
        """Todos los organismos, ordenados por nombre."""
        return (
            self._session.query(Organismo)
            .order_by(Organismo.nombre)
            .all()
        )

    def actualizar_puntaje_organismo(
        self, codigo: str, puntaje: int
    ) -> bool:
        """Actualiza el ``puntaje_fijo`` de un organismo."""
        instancia: Organismo | None = (
            self._session.query(Organismo)
            .filter(Organismo.codigo == codigo)
            .first()
        )
        if instancia is None:
            return False
        instancia.puntaje_fijo = puntaje
        return True
