import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import Base
from app.models import *

target_metadata = Base.metadata
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # Берём URL из переменной окружения, если она есть
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = config.get_main_option("sqlalchemy.url")
    # Убираем +asyncpg для синхронного драйвера
    if database_url and "+asyncpg" in database_url:
        database_url = database_url.replace("+asyncpg", "")
    # Передаём URL в конфиг Alembic
    config.set_main_option("sqlalchemy.url", database_url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()