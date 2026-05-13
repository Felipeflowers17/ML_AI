"""Script de inicialización de la base de datos para primer uso.

Verifica conectividad con PostgreSQL antes de ejecutar migraciones.
A diferencia de ``migrate.py``, este comando comprueba que la BD
esté accesible antes de intentar cualquier operación.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine


def main() -> None:
    """Punto de entrada para ``poetry run init-db``.

    1. Carga ``.env``.
    2. Verifica que ``DATABASE_URL`` esté configurada.
    3. Prueba la conexión a PostgreSQL.
    4. Ejecuta ``alembic upgrade head`` para crear todas las tablas.
    """
    load_dotenv()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL no configurada.")
        print("Edite el archivo .env y configure DATABASE_URL.")
        sys.exit(1)

    # ── Verificar conectividad ───────────────────────────────────────
    try:
        engine = create_engine(db_url)
        with engine.connect():
            pass
        print("Conexión a PostgreSQL: OK")
    except Exception as e:
        print(f"ERROR: No se pudo conectar a PostgreSQL: {e}")
        print("Verifique que PostgreSQL esté corriendo y accesible.")
        sys.exit(1)

    # ── Migrar ────────────────────────────────────────────────────────
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Base de datos inicializada correctamente.")
