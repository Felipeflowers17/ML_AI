"""Repositorio de configuración — pares clave-valor de la aplicación.

Tres métodos para obtener, guardar y listar toda la configuración.
"""

from monitor_licitaciones.infrastructure.database.models import Configuracion
from sqlalchemy.orm import Session


class RepositorioConfiguracion:
    """Repositorio para la tabla ``configuracion``."""

    def __init__(self, session: Session):
        self._session = session

    def obtener(self, clave: str) -> str | None:
        """Obtiene el valor de una clave. Retorna ``None`` si no existe."""
        instancia: Configuracion | None = (
            self._session.query(Configuracion)
            .filter(Configuracion.clave == clave)
            .first()
        )
        return instancia.valor if instancia else None

    def guardar(self, clave: str, valor: str) -> None:
        """UPSERT: inserta o actualiza una clave."""
        instancia: Configuracion | None = (
            self._session.query(Configuracion)
            .filter(Configuracion.clave == clave)
            .first()
        )
        if instancia:
            instancia.valor = valor
        else:
            self._session.add(Configuracion(clave=clave, valor=valor))

    def obtener_todas(self) -> dict[str, str]:
        """Retorna todos los pares clave-valor como dict."""
        resultados = (
            self._session.query(Configuracion).all()
        )
        return {r.clave: r.valor for r in resultados if r.valor is not None}
