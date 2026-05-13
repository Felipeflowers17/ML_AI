"""Fixtures compartidos para todos los tests.

Los imports de modelos y repositorios son lazy (dentro de funciones)
para permitir que pytest arranque incluso si esos módulos no existen aún.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def engine():
    """SQLite in-memory engine con todos los modelos creados."""
    from monitor_licitaciones.infrastructure.database.models import Base

    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="function")
def session(engine):
    """Sesión SQLAlchemy con rollback automático al finalizar cada test.

    Aislamiento total entre tests: cada uno parte con BD limpia.
    """
    SessionLocal = sessionmaker(bind=engine)
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.rollback()
        sesion.close()


@pytest.fixture(scope="session")
def qapp():
    """Instancia única de QApplication para todo el proceso de pytest."""
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    yield app
    app.quit()


@pytest.fixture(scope="function")
def repo_licitaciones(session):
    """Repositorio de licitaciones inyectado con sesión de test."""
    from monitor_licitaciones.infrastructure.database.repositorio_licitaciones import (
        RepositorioLicitaciones,
    )

    return RepositorioLicitaciones(session)


@pytest.fixture(scope="function")
def repo_reglas(session):
    """Repositorio de reglas inyectado con sesión de test."""
    from monitor_licitaciones.infrastructure.database.repositorio_reglas import (
        RepositorioReglas,
    )

    return RepositorioReglas(session)


@pytest.fixture(scope="function")
def repo_config(session):
    """Repositorio de configuración inyectado con sesión de test."""
    from monitor_licitaciones.infrastructure.database.repositorio_configuracion import (
        RepositorioConfiguracion,
    )

    return RepositorioConfiguracion(session)
