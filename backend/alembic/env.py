"""
Alembic environment configuration for PEI Agentic Platform.

This script is run by the alembic command line tool and handles:
1. Setting up the SQLAlchemy connection (engine)
2. Running migrations
3. Setting the target metadata for automatic migrations
"""

import asyncio
import logging
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context

# Import all models to ensure they're registered with Base.metadata
from app.core.database import Base
from app.models import OT, Cuadrilla, LogAgente, Assignment

# this is the Alembic Config object, which provides
# the values of the [alembic] section of the .ini file, and can be
# used to configure programmatic migration behavior. The values may be
# modified to produce SQLAlchemy-style arguments which are passed
# to the functions configure_engine and do_revision_objects
# see the full configuration reference for more information on
# Alembic configuration

config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# set the new alembic logger
logger = logging.getLogger("alembic.env")

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# ============================================================================
# CONFIGURATION FROM ENVIRONMENT VARIABLES
# ============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./pei.db"
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        url = DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """
    Run migrations given a connection object.

    Args:
        connection: SQLAlchemy connection object
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """

    # Get database URL from environment or config
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        url = DATABASE_URL

    # Create async engine with proper configuration
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = url

    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        echo=False,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# ============================================================================
# MAIN MIGRATION EXECUTION
# ============================================================================

if context.is_offline_mode():
    logger.info("Running migrations offline")
    run_migrations_offline()
else:
    logger.info("Running migrations online")
    asyncio.run(run_migrations_online())

