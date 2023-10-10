from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import Session, sessionmaker

from bingqilin.db.models import SQLAlchemyDBConfig


class SQLAlchemyClient:
    sync_engine: Engine
    sync_session: sessionmaker[Session]

    async_engine: AsyncEngine
    async_session: async_sessionmaker[AsyncSession]

    def __init__(self, config: SQLAlchemyDBConfig):
        url: URL = config.get_url()
        self.sync_engine = create_engine(url)
        self.sync_session = sessionmaker(
            bind=self.sync_engine, autoflush=False, autocommit=False
        )

        self.async_engine = create_async_engine(url)
        self.async_session = async_sessionmaker(
            bind=self.async_engine, autoflush=False, autocommit=False
        )

    def get_sync_db(self):
        db: Session = self.sync_session()

        try:
            yield db
        except SQLAlchemyError:
            db.rollback()
            raise
        else:
            db.commit()
        finally:
            db.close()

    @contextmanager
    def sync_db_ctx(self):
        yield from self.get_sync_db()

    async def get_async_db(self):
        db: AsyncSession = self.async_session()

        try:
            yield db
        except SQLAlchemyError:
            await db.rollback()
            raise
        else:
            await db.commit()
        finally:
            await db.close()

    @asynccontextmanager
    async def async_db_ctx(self):
        async for _ in self.get_async_db():
            yield _
