import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ------------------------------------------------------------------
# Make sure 'backend/' is on the path so app.* imports work
# ------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ------------------------------------------------------------------
# Import Base + all models so Alembic can see the full metadata.
# ------------------------------------------------------------------
from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401 — must import to populate Base.metadata

# ------------------------------------------------------------------
# Alembic config
# ------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url from .env — uses sync psycopg2 driver
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ------------------------------------------------------------------
# Only manage tables that belong to our app.
# This prevents Alembic from touching PostGIS internal tables
# (tiger, topology, spatial_ref_sys, etc.)
# ------------------------------------------------------------------

# Exact set of table names our app owns
OUR_TABLES = {"cameras", "emissions"}


def include_name(name, type_, parent_names):
    """
    Filter what Alembic pays attention to during autogenerate.

    - schemas: only 'public'
    - tables:  only our own two tables
    - everything else (indexes, sequences, etc.) follows the table filter
    """
    if type_ == "schema":
        return name in (None, "public")
    if type_ == "table":
        return name in OUR_TABLES
    return True


# ------------------------------------------------------------------
# Offline mode — generates SQL without a DB connection
# ------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------------
# Online mode — connects to DB and applies changes
# ------------------------------------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=True,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()