"""Script para aplicar migraciones sobre una base existente.

A diferencia de ``init_db.py``, este comando asume que la conexión
ya está configurada y disponible (útil para CI/CD o actualizaciones).
"""

from dotenv import load_dotenv


def main() -> None:
    """Punto de entrada para ``poetry run migrate``.

    1. Carga ``.env``.
    2. Ejecuta ``alembic upgrade head`` para aplicar migraciones pendientes.
    """
    load_dotenv()

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Migraciones aplicadas correctamente.")
