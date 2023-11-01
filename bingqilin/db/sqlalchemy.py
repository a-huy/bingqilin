from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Callable, Generator, Optional

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from bingqilin.contexts import ContextFieldTypes, LifespanContext
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


def get_sync_db(
    ctx_object: LifespanContext, client_name: Optional[str] = None
) -> Callable[..., Generator]:
    """Convenience function to make it easy to add a FastAPI dependency for a database
    client that may not exist until after configuration has loaded. When the dependency
    is resolved, it will return an SQLAlchemy Session object.

    Args:
        client_name (Optional[str], optional): The name of the client.
        If one is not provided, the "default" client is retrieved.

    Returns:
        Callable[..., Generator]: Function returned for use with `Depends()`
    """

    def _resolve():
        if not client_name:
            client: SQLAlchemyClient = ctx_object.get_default(
                ContextFieldTypes.DATABASES
            )
        else:
            client: SQLAlchemyClient = getattr(ctx_object, client_name)
        yield from client.get_sync_db()

    return _resolve


def get_async_db(
    ctx_object: LifespanContext, client_name: Optional[str] = None
) -> Callable[..., AsyncGenerator]:
    """Convenience function to make it easy to add a FastAPI dependency for a database
    client that may not exist until after configuration has loaded. When the dependency
    is resolved, it will return an SQLAlchemy AsyncSession object.

    Args:
        client_name (Optional[str], optional): The name of the client.
        If one is not provided, the "default" client is retrieved.

    Returns:
        Callable[..., AsyncGenerator]: Function returned for use with `Depends()`
    """

    async def _resolve():
        if not client_name:
            client: SQLAlchemyClient = ctx_object.get_default(
                ContextFieldTypes.DATABASES
            )
        else:
            client: SQLAlchemyClient = getattr(ctx_object, client_name)
        async for _ in client.get_async_db():
            yield _

    return _resolve
