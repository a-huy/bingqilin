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
    name = 'my_context'

    postgres: SQLAlchemyClient = SQLAlchemyField(is_default=True)
    redis: RedisClientTypes = RedisField()
    vector: VectorDatabaseClient = DatabaseField(
        config_model=VectorDatabaseConfig,
        initialize_func=lambda config: VectorDatabaseClient.create_from_config(
            **config
        ),
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
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

class AppContext(LifespanContext):
    name = 'app'

    ml_models: dict = ContextField('ml', is_default=True)

context = AppContext(settings.data)
```

The default behavior of LifespanContext objects if a model is defined at init time and no initializers are found for the field is to look for a `settings_data.{context_name}.{field_name}` value, and use that as the config for setting up the field's annotated type. In the example above, since no custom initializers are found, it will look for the `ml_models` field config in `settings.data.app.ml_models`.

## Namespaces

Within a context, each field belongs to a namespace that will be grouped together. You can specify a particular field to be the default field for that namespace, and the following expressions will return the same field value:

* `context.ml_models`
* `context.get_default('ml')`

If there is only one namespace defined across all the fields in the context, you don't have to specify a namespace when getting the default field. `context.get_default()` will still return `context.ml_models`.

Bingqilin provides a couple conveniences for defining fields in common namespaces:

* `DatabaseField()` for the `databases` namespace
* `ThirdPartyField()` for the `third_parties` namespace

## Specifying a Pydantic Model

When declaring a `ContextField`, you can pass in a `config_model` parameter to validate the value of the settings instance to that model if it's not already an instance of the model:

```py hl_lines="15"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext

from .models import MLModelsConfig

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

class AppContext(LifespanContext):
    name = 'app'

    ml_models: dict = ContextField('ml', config_model=MLModelsConfig)

context = AppContext(settings.data)
```

This will take the value of `settings.data.app.ml_models` and attempt to validate it as an `MLModelsConfig` instance.

## Config Getter Functions

Sometimes, your config is located in a different location in your settings instance than what `LifespanContext` would assume. You can define a `config_getter_func` parameter for `ContextField`s that accept a parameter for your settings instance and returns the config for that field:

```py hl_lines="18"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext

from .models import MLModelsConfig

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

class AppContext(LifespanContext):
    name = 'app'

    ml_models: dict = ContextField(
        'ml',
        config_model=MLModelsConfig
        config_getter_func=lambda settings: settings.other_config_model.ml_models
    )

context = AppContext(settings.data)
```

Or, your config might not even come from settings at all:

```py hl_lines="12 20"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext

from .models import MLModelsConfig

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

ML_MODELS_CONFIG = {'the_best_model': 42}

class AppContext(LifespanContext):
    name = 'app'

    ml_models: dict = ContextField(
        'ml',
        config_model=MLModelsConfig
        config_getter_func=lambda settings: ML_MODELS_CONFIG
    )

context = AppContext(settings.data)
```

## Initializers

You specify logic for intializing a field in two ways:

### The `initialize_func` Parameter

```py hl_lines="5 22"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext

from .learning import initialize_learning
from .models import MLModelsConfig

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

ML_MODELS_CONFIG = {'the_best_model': 42}

class AppContext(LifespanContext):
    name = 'app'

    ml_models: dict = ContextField(
        'ml',
        config_model=MLModelsConfig
        config_getter_func=lambda settings: ML_MODELS_CONFIG,
        initialize_func=lambda config: initialize_learning(config)
    )

context = AppContext(settings.data)
```

Functions specified this way must take a parameter for the validated config value.

### The `@initializer` Decorator

```py hl_lines="5 24-26"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext

from .learning import initialize_learning
from .models import MLModelsConfig

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

ML_MODELS_CONFIG = {'the_best_model': 42}

class AppContext(LifespanContext):
    name = 'app'

    ml_models: dict = ContextField(
        'ml',
        config_model=MLModelsConfig
        config_getter_func=lambda settings: ML_MODELS_CONFIG
    )

    @initializer('ml_models')
    def initialize_ml_models(cls, config: MLModelsConfig):
        return initialize_learning(config)

context = AppContext(settings.data)
```

Decorated methods MUST be a classmethod. Each initializer must accept a parameter for the validated config value.

## Terminators

Similar methods and functions can be defined to do any cleanup for fields, by using the `terminate_func` parameter for `ContextField`s or the `@terminator` decorator. These methods do not have to accept any parameters.

## `SQLAlchemyField` and `RedisField`

Additionally, Bingqilin also provides a couple convenience fields that tie together some SQLAlchemy or Redis utilities you might use together to define database connections:

```py hl_lines="3 14-15"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext, RedisField, SQLAlchemyField
from bingqilin.db.redis import RedisClientTypes
from bingqilin.db.sqlalchemy import SQLAlchemyClient

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

class DatabasesContext(ContextManager):
    name = 'databases'
    postgres: SQLAlchemyClient = SQLAlchemyField(is_default=True)
    redis: RedisClientTypes = RedisField()

context = DatabasesContext(settings.data)
```

`SQLAlchemyField` is a proxy call to `DatabaseField()` with three parameters set: A `namespace` for `databases`, `SQLAlchemyDBConfig` as the `config_model`, and `initialize_func` with an inline function to call `initialize_client()` on the config model instance. the `RedisField` call does the same for its respective config model (`RedisDBConfig`).

### `DatabaseField`s

If you have a database connection you'd like to declare, you can just put them under the `databases` namespace by declaring it as a `DatabaseField()`. You can override any initializers and config models as well.

## Multiple Contexts

You don't have to put everything under one context - if it fits your needs better, you can define multiple contexts if it makes more sense:

```py hl_lines="30-31"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext, RedisField, SQLAlchemyField
from bingqilin.db.redis import RedisClientTypes
from bingqilin.db.sqlalchemy import SQLAlchemyClient

from .learning import initialize_learning
from .models import MLModelsConfig

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

class DatabasesContext(ContextManager):
    name = 'databases'
    postgres: SQLAlchemyClient = SQLAlchemyField(is_default=True)
    redis: RedisClientTypes = RedisField()

class LearningContext(LifespanContext):
    name = 'ai'

    ml_models: dict = ContextField(
        'ml',
        config_model=MLModelsConfig
        config_getter_func=lambda settings: ML_MODELS_CONFIG,
        initialize_func=lambda config: initialize_learning(config)
    )

databases = DatabasesContext(settings.data)
learning_models = LearningContext(settings.data)
```

## Disabling Reconfiguration

By default, whenever a lifespan context instance is created, it will automatically add a reconfigure handler. You can disable this by setting the `allow_reconfigure` class attribute to `False`:

```py hl_lines="18"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext

from .learning import initialize_learning
from .models import MLModelsConfig

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings()

ML_MODELS_CONFIG = {'the_best_model': 42}

class AppContext(LifespanContext):
    name = 'app'

    allow_reconfigure = False

    ml_models: dict = ContextField(
        'ml',
        config_model=MLModelsConfig
        config_getter_func=lambda settings: ML_MODELS_CONFIG,
        initialize_func=lambda config: initialize_learning(config)
    )

context = AppContext(settings.data)
```