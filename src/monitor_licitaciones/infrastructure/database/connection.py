"""Session manager con patrón context manager para SQLAlchemy.

Expone ``get_session()`` como context manager que maneja commit/rollback
automáticamente. Usar así::

    with get_session() as session:
        results = session.query(Licitacion).all()
        # commit automático al salir del bloque
"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from monitor_licitaciones.infrastructure.database.models import Base

# ── Engine global (lazy: se configura al importar por primera vez) ───
_engine = None
_SessionLocal = None


def _get_engine():
    """Obtiene o crea el engine desde DATABASE_URL."""
    global _engine, _SessionLocal
    if _engine is None:
        import os

        from dotenv import load_dotenv

        load_dotenv()
        db_url = os.getenv("DATABASE_URL", "sqlite:///:memory:")
        _engine = create_engine(db_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db():
    """Crea todas las tablas en la BD (útil para tests o primer uso)."""
    engine = _get_engine()
    Base.metadata.create_all(engine)


@contextmanager
def get_session():
    """Context manager que provee una sesión con commit/rollback automático.

    Al salir del bloque exitosamente hace commit.
    Si hay una excepción, hace rollback y la re-lanza.
    Siempre cierra la sesión al final.
    """
    _get_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
