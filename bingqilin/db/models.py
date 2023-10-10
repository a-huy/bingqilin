from abc import abstractmethod
from typing import Any, Optional, Literal, Mapping, Union, Sequence, Callable, Dict
from typing_extensions import get_args

from pydantic import BaseModel, model_validator
from pydantic._internal._model_construction import ModelMetaclass
from pydantic._internal._generics import PydanticGenericMetadata
from pydantic_core import core_schema


DATABASE_CONFIG_MODELS = {}


class DBConfigMeta(ModelMetaclass):
    def __new__(
        mcs,
        cls_name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        __pydantic_generic_metadata__: PydanticGenericMetadata | None = None,
        __pydantic_reset_parent_namespace__: bool = True,
        **kwargs: Any,
    ) -> type:
        cls = super().__new__(
            mcs,
            cls_name,
            bases,
            namespace,
            __pydantic_generic_metadata__,
            __pydantic_reset_parent_namespace__,
            **kwargs,
        )
        if cls_name != "DBConfig" and DBConfig in bases:
            DATABASE_CONFIG_MODELS[cls.get_model_db_type()] = cls  # type: ignore
        return cls


class DBDict(dict):
    """This is a thin wrapper around a dict that enables accessing keys as attributes."""

    def __getattribute__(self, __name: str) -> Any:
        try:
            return super().__getattribute__(__name)
        except AttributeError as exn:
            if __name in self:
                return self[__name]
            raise exn

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: Callable[[Any], core_schema.CoreSchema]
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        args = get_args(source)
        if args:
            # replace the type and rely on Pydantic to generate the right schema
            # for `Dict`
            dict_t_schema = handler.generate_schema(Dict[args[0], args[1]])  # type: ignore
        else:
            dict_t_schema = handler.generate_schema(Dict)

        non_instance_schema = core_schema.with_info_after_validator_function(
            lambda v, i: DBDict(v), dict_t_schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])

    def items(self):
        return dict(self).items()


class DBConfig(BaseModel, metaclass=DBConfigMeta):
    """Base model for database configuration."""

    type: Literal[""]
    host: str = "localhost"
    port: Optional[int] = None

    @abstractmethod
    def initialize_client(self):
        return

    @classmethod
    def get_model_db_type(cls):
        schema = cls.model_json_schema()
        properties = schema["properties"]
        return properties["type"]["const"]


class SQLAlchemyDBConfig(DBConfig):
    type: Literal["sqlalchemy"]
    url: Optional[str] = None
    engine: Optional[str] = None
    dialect: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    query: Mapping[str, Union[Sequence[str], str]] = {}

    @model_validator(mode="after")
    def check_required(self):
        if not (self.url or self.engine):
            raise ValueError(
                "Information to specify a database is missing. Either a URI or (engine) must be specified."
            )
        return self

    def get_url(self):
        from sqlalchemy import make_url, URL

        if self.url:
            return make_url(self.url)
        return URL.create(
            f"{self.engine}{'+' + self.dialect if self.dialect else ''}",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
            query=self.query,
        )

    def initialize_client(self):
        from .sqlalchemy import SQLAlchemyClient

        return SQLAlchemyClient(self)
