from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Callable, Generator, List, Optional, Type

from pydantic import BaseModel
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase, Session, selectinload, sessionmaker

from bingqilin.contexts import ContextFieldTypes, LifespanContext
from bingqilin.db.models import SQLAlchemyDBConfig


class ObjectNotFoundError(Exception):
    pass


class SQLAlchemyClient:
    sync_engine: Engine
    sync_session: sessionmaker[Session]

    async_engine: AsyncEngine
    async_session: async_sessionmaker[AsyncSession]

    def __init__(self, config: SQLAlchemyDBConfig):
        self.sync_engine = create_engine(**config.to_engine_kwargs())
        self.sync_session = sessionmaker(
            bind=self.sync_engine, autoflush=False, autocommit=False
        )

        self.async_engine = create_async_engine(**config.to_engine_kwargs())
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

    # Synchronous convenience methods for db transactions

    def get(
        self,
        orm_model: Type[DeclarativeBase],
        validator: Type[BaseModel],
        raise_if_not_found: bool = True,
        **filters: Any,
    ) -> BaseModel | None:
        with self.sync_db_ctx() as db:
            q = select(orm_model).filter_by(**filters)
            result = db.scalars(q).one_or_none()
            if not result and raise_if_not_found:
                raise ObjectNotFoundError(
                    f"Object not found. Model: {orm_model}, filters: {filters}"
                )
            if not result:
                return None
            return validator.model_validate(result)

    def filter(
        self,
        orm_model: Type[DeclarativeBase],
        validator: Type[BaseModel],
        **filters: Any,
    ) -> List[BaseModel] | None:
        with self.sync_db_ctx() as db:
            q = select(orm_model).filter_by(**filters)
            results = db.scalars(q).all()
            return [validator.model_validate(r) for r in results]

    def modify(self, orm_model: Type[DeclarativeBase], **filters: Any):
        with self.sync_db_ctx() as db:
            q = select(orm_model).filter_by(**filters)
            result = db.scalars(q).one_or_none()
            if not result:
                raise ObjectNotFoundError(
                    f"Object not found. Model: {orm_model}, filters: {filters}"
                )
            yield result
            db.commit()

    # Asynchronous convenience methods for db transactions

    async def aget(
        self,
        orm_model: Type[DeclarativeBase],
        validator: Type[BaseModel],
        raise_if_not_found: bool = True,
        **filters: Any,
    ) -> BaseModel | None:
        async with self.async_db_ctx() as db:
            q = select(orm_model)
            # If the orm_model has mapped relationships, then we need to preload the related objects
            # so they can validate correctly in the pydantic model.
            relationships = inspect(orm_model).relationships
            for name, _ in relationships.items():
                q = q.options(selectinload(getattr(orm_model, name)))
            q = q.filter_by(**filters)

            result = (await db.scalars(q)).one_or_none()
            if not result and raise_if_not_found:
                raise ObjectNotFoundError(
                    f"Object not found. Model: {orm_model}, filters: {filters}"
                )
            if not result:
                return None

            return validator.model_validate(result)

    async def afilter(
        self,
        orm_model: Type[DeclarativeBase],
        validator: Type[BaseModel],
        **filters: Any,
    ) -> List[BaseModel] | None:
        async with self.async_db_ctx() as db:
            q = select(orm_model)
            # If the orm_model has mapped relationships, then we need to preload the related objects
            # so they can validate correctly in the pydantic model.
            relationships = inspect(orm_model).relationships
            for name, _ in relationships.items():
                q = q.options(selectinload(getattr(orm_model, name)))
            q = q.filter_by(**filters)
            results = (await db.scalars(q)).all()
            return [validator.model_validate(r) for r in results]

    @asynccontextmanager
    async def amodify(self, orm_model: Type[DeclarativeBase], **filters: Any):
        async with self.async_db_ctx() as db:
            q = select(orm_model)
            # If the orm_model has mapped relationships, then we need to preload the related objects
            # so they can validate correctly in the pydantic model.
            relationships = inspect(orm_model).relationships
            for name, _ in relationships.items():
                q = q.options(selectinload(getattr(orm_model, name)))
            q = q.filter_by(**filters)
            result = (await db.scalars(q)).one_or_none()
            if not result:
                raise ObjectNotFoundError(
                    f"Object not found. Model: {orm_model}, filters: {filters}"
                )
            yield result
            await db.commit()


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
