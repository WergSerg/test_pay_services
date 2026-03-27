# backend/core/database_sync.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.core.config import settings

# Синхронный движок для миграций
# Заменяем asyncpg на psycopg2 или psycopg2-binary
sync_database_url = settings.database_url.replace("+asyncpg", "").replace("asyncpg", "psycopg2")
# Если используете postgresql+asyncpg, то после replace получится postgresql://...

sync_engine = create_engine(
    sync_database_url,
    echo=True,
    pool_size=20,
    max_overflow=10,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False,
)

Base = declarative_base()