
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.core.config import settings

sync_database_url = settings.database_url.replace("+asyncpg", "").replace("asyncpg", "psycopg2")

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