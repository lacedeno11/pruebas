"""
Alembic Environment Configuration for DERCAS PEI Backend

This module configures Alembic for:
- Async SQLAlchemy migrations using asyncio
- Auto-generation of migration scripts from SQLAlchemy models
- Proper handling of database enums and constraints
- Online and offline migration contexts

The configuration supports both:
- Offline mode: Generates SQL without executing (for code review)
- Online mode: Executes migrations directly against database
"""

import asyncio
import logging
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.core.database import Base

# ============================================================================
# Alembic Configuration
# ============================================================================

# Get Alembic config
config = context.config

# Set sqlalchemy.url from environment
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# ============================================================================
# Target Metadata for Auto-generation
# ============================================================================

target_metadata = Base.metadata
"""
Target metadata for Alembic auto-generation.

This connects Alembic to our SQLAlchemy models so that migration files
can be auto-generated when the models change.

When you run: alembic revision --autogenerate
Alembic compares the current database schema with target_metadata
and generates the necessary migration operations.
"""


# ============================================================================
# Offline Migration Context
# ============================================================================

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL without a live database connection.
    Useful for:
    - Code review of migrations before applying
    - Generating SQL for manual application
    - CI/CD pipelines where DB isn't available during build
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================================
# Online Migration Context (Async)
# ============================================================================

async def run_async_migrations() -> None:
    """
    Run migrations asynchronously using async SQLAlchemy engine.
    
    This is the primary migration runner for the DERCAS system using
    async/await patterns with asyncio and AsyncPG driver.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=pool.NullPool,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(
            context.configure,
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            await connection.run_sync(context.run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode with async support.
    
    Detects if we're using an async driver (asyncpg) and runs
    migrations asynchronously in that case.
    """
    # Check if using async driver
    if "asyncpg" in settings.DATABASE_URL or "asyncio" in settings.DATABASE_URL:
        # Run async migrations
        asyncio.run(run_async_migrations())
    else:
        # Fallback to sync migrations (if using sync driver)
        configuration = config.get_section(config.config_ini_section)
        configuration["sqlalchemy.url"] = settings.DATABASE_URL

        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )

            with context.begin_transaction():
                context.run_migrations()


# ============================================================================
# Migration Execution
# ============================================================================

if context.is_offline_mode():
    logger.info("Running migrations in offline mode")
    run_migrations_offline()
else:
    logger.info("Running migrations in online mode")
    run_migrations_online()

