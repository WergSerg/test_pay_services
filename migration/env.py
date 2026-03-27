
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from backend.core.database_sync import Base
import backend.domain.models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


# Импортируйте ваши модели здесь, чтобы Alembic их видел
# from backend.domain.models import User, Payment  # и т.д.

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    # Убираем asyncpg из URL
    url = url.replace("+asyncpg", "").replace("asyncpg", "psycopg2")
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
    # Получаем URL из конфига
    url = config.get_main_option("sqlalchemy.url")
    # Заменяем asyncpg на psycopg2 для синхронной работы
    sync_url = url.replace("+asyncpg", "").replace("asyncpg", "psycopg2")

    # Создаем конфигурацию для движка
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = sync_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()