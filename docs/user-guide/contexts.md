---
title: LifespanContext objects
---

Lifespan contexts are a kind of model that you can create declaratively for connections, clients, and other data that you can share across your app. For example:

```py
from bingqilin.contexts import (
    LifespanContext,
    ContextField,
    DatabaseField,
    RedisField,
    SQLAlchemyField,
    ThirdPartyField,
    initializer,
)
from bingqilin.db.sqlalchemy import SQLAlchemyClient, RedisClientTypes

from .clients import MyAPIClientClass
from .config import settings
from .learning import load_models, cleanup_models
from .models import MyAPIConfig, VectorDatabaseClient, VectorDatabaseConfig

class MyContext(LifespanContext):

    postgres: SQLAlchemyClient = SQLAlchemyField(is_default=True)
    redis: RedisClientTypes = RedisField()
    vector: VectorDatabaseClient = DatabaseField(
        config_model=VectorDatabaseConfig,
        initialize_func=lambda config: VectorDatabaseClient.create_from_config(**config),
        config_getter_func=lambda settings: settings.databases.vector
    )

    my_api_client: MyAPIClientClass = ThirdPartyField(
        config_model=MyAPIConfig,
        initialize_func=lambda config: MyAPIClientClass(config),
        config_getter_func=lambda settings: settings.my_client
    )

    ml_models: dict = ContextField('ml')

    @initializer('ml_models')
    @classmethod
    def initialize_ml_models(cls, init_values):
        return load_models()

    @terminator('ml_models')
    @classmethod
    def terminate_ml_models(cls):
        cleanup_models()


context = MyContext(settings)
context.configure(ml_models={'config_1': 42, 'tuning_values': [1, 49, 200]})
```

The snippet above is intended to demonstrate everything that context managers have to offer.

Defining a lifespan context will require you to provide a couple things:

* How to refer to the connection, and what its type is
* How to initialize the field by either using a convenience `ContextField` derived class, by specifying an initialization function, or with a `@initiator` decorated classmethod.

## Defining a field with `ContextField`

```py
from bingqilin.contexts import LifespanContext

class AppContext(LifespanContext):

    ml_models: dict = ContextField('ml')
```
