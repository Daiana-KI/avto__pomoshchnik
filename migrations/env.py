import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
import sys
import os
from pathlib import Path

# Добавляем путь к приложению, чтобы импортировать Base
sys.path.append(str(Path(__file__).parent.parent))

from app.database import Base
from app.models import *  # Импорт всех моделей

# target_metadata - обязательно для autogenerate
target_metadata = Base.metadata

# Интерпретируем alembic.ini для логов
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline():
    """Запуск миграций в offline-режиме."""
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
    """Запуск миграций в online-режиме (синхронно)."""
    # Берём URL из переменной окружения DATABASE_URL, если она есть
    # и заменяем +asyncpg на пустую строку для синхронного драйвера
    database_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    if database_url and "+asyncpg" in database_url:
        database_url = database_url.replace("+asyncpg", "")

    # Создаём конфиг для Alembic
    alembic_config = config.get_section(config.config_ini_section)
    alembic_config["sqlalchemy.url"] = database_url

    connectable = engine_from_config(
        alembic_config,
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