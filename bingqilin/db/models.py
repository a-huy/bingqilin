from abc import abstractmethod
from functools import reduce
from typing import (
    Any,
    Optional,
    Literal,
    Mapping,
    Union,
    Sequence,
    Dict,
    List,
    Type,
)

from pydantic import BaseModel, model_validator, Field
from pydantic._internal._model_construction import ModelMetaclass
from pydantic._internal._generics import PydanticGenericMetadata

from bingqilin.utils.types import RegistryMeta


DATABASE_CONFIG_MODELS: Dict[str, Type["DBConfig"]] = {}


class DBConfigMeta(ModelMetaclass, RegistryMeta):
    registry_field: Literal["type"]
    root_class: Literal["bingqilin.db.models:DBConfig"]

    @classmethod
    def get_registry(cls):
        return DATABASE_CONFIG_MODELS


class DBConfig(BaseModel, metaclass=DBConfigMeta):
    """Base model for database configuration."""

    type: Literal[""]
    host: str = "localhost"
    port: Optional[int] = None

    @abstractmethod
    def initialize_client(self):
        return

    @property
    def extra_fields(self) -> set[str]:
        return set(self.__dict__) - set(self.__fields__)

    @property
    def extra_data(self) -> Dict[str, Any]:
        return {f: getattr(self, f) for f in self.extra_fields}

    @classmethod
    def get_model_db_type(cls):
        schema = cls.model_json_schema()
        properties = schema["properties"]
        return properties["type"]["const"]

    class Config:
        extra = "allow"


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
                "Information to specify a database is missing. Either a URI or (engine) "
                "must be specified."
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


class RedisClusterNodeConfig(BaseModel):
    host: str
    port: Union[str, int]
    server_type: Optional[Union[Literal["primary"], Literal["replica"]]] = None


class RedisDBConfig(DBConfig):
    type: Literal["redis"]

    # Usual Redis fields used for connecting
    port: int = 6379
    db: int = 0
    username: Optional[str] = None
    password: Optional[str] = None

    # Less common options
    unix_socket_path: Optional[str] = None
    ssl: bool = False
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_cert_reqs: str = "required"
    ssl_ca_certs: Optional[str] = None
    ssl_ca_data: Optional[str] = None
    ssl_check_hostname: bool = False
    socket_connect_timeout: Optional[int] = None

    is_async: bool = Field(
        default=True,
        description="If set, this will use the Redis/RedisCluster connection clients "
        "from `redis.asyncio`.",
    )

    # If not empty, this will return a RedisCluster object.
    nodes: Optional[List[RedisClusterNodeConfig]] = None

    def initialize_client(self):
        from .redis import make_redis_client

        return make_redis_client(self)
