"""Configuración del entorno Alembic.

Agrega ``src/`` al sys.path, carga .env, configura la URL de la BD
e importa los modelos para migraciones automáticas.
"""

import sys
from pathlib import Path

from alembic import context
from dotenv import load_dotenv  # type: ignore[import-untyped]
from sqlalchemy import engine_from_config, pool

# Agregar src/ al path para poder importar los modelos
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Cargar variables de entorno desde .env
load_dotenv()

# Importar Base y modelos para target_metadata
from monitor_licitaciones.infrastructure.database.models import Base  # noqa: E402

target_metadata = Base.metadata

# Obtener DATABASE_URL
import os  # noqa: E402

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Config de Alembic
from alembic import config as alembic_config  # noqa: E402

alembic_config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
