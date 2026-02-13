"""
Alembic environment script.

Provides the env.py script for Alembic migrations.
Configures target_metadata with all SQLAlchemy models.
"""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import the Base from db configuration
from backend.app.db.base import Base, DATABASE_URL

# Import all models to register them with Base.metadata
from backend.app.models import (
    OrdenTrabajo,
    Cuadrilla,
    LogAgente,
    Asignacion,
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# set the sqlalchemy.url from environment
config.set_main_option('sqlalchemy.url', DATABASE_URL)

# add your model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the create_engine() step
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    
    # Create engine configuration
    engine_config = {
        "sqlalchemy.url": config.get_main_option("sqlalchemy.url"),
        "sqlalchemy.echo": False,
    }
    
    # Get additional config from environment
    pool_size = int(os.getenv("SQLALCHEMY_POOL_SIZE", "10"))
    max_overflow = int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "20"))
    pool_recycle = int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "3600"))
    
    engine_config["sqlalchemy.pool_size"] = pool_size
    engine_config["sqlalchemy.max_overflow"] = max_overflow
    engine_config["sqlalchemy.pool_recycle"] = pool_recycle
    engine_config["sqlalchemy.pool_pre_ping"] = True
    
    engine = engine_from_config(
        engine_config,
        prefix="sqlalchemy.",
        poolclass=pool.QueuePool,
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite compatibility
        )

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

