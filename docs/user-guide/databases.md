---
title: Databases
---

Bingqilin offers a base model class to read and convert database client options into instances that can be accessed via `bingqilin.db:get_db_client()`.

## Configuring a Database Client

Information for your database clients are declared in the `databases` field of your config. The field is a mapping that is keyed by the ID or name that you would like to use to retrieve that client in your app.

Ex:

```yaml title="config.yaml"
databases:
    default:
        type: sqlalchemy
        engine: postgresql
        user: user
        password: testdb123
        host: postgresserver
        database: db
        port: 5432
    redis:
        type: redis
        host: redisserver
        port: 6379
        db: 0
...
```

Here, there are two databases configured - An SQLAlchemy client connected to a PostgreSQL server, and a Redis client.

!!! tip
    If you declare config for a database client under the `default` key, it will be the client retrieved if no client ID is specified when calling `#!python get_db_client()`.

## Custom Database Config Models

You can also declare your own database config models to use in your `ConfigModel` and determine how the client object is created:

```py
from typing import Literal, Optional
from bingqilin.db.models import DBConfig

from database_lib import DatabaseClient


class MyDBConfig(DBConfig):
    type: Literal["my_database"]
    name: str
    user: Optional[str]
    password: Optional[str]
    port: int = 10101

    def initialize_client(self):
        return DatabaseClient(
            host=self.host, 
            port=self.port, 
            username=self.user, 
            password=self.password, 
            name=self.name
        )
```

1. Custom database config models must derive from `DBConfig`. This allows the model to be registered and have their `initialize_client()` method called after validation.
2. DB config models must define a `type` class attributed annotated with a `Literal` string. This is used when loading config so that the validator knows which model to validate against.
3. DB config models must implement an `initialize_client()` method that returns a handle to the configured database, ORM, client pool, etc.

!!! note
    The base `DBConfig` model already has the `host` and `port` fields for use. Under the hood, it's really just a Pydantic `BaseModel`, so you can override these if you'd like.

Then declare a database connection client in your config:

```yaml title="config.yaml"
databases:
    default:
        type: my_database
...
```

Finally, retrieve the client in your app and use it:

```py hl_lines="1 12"
from bingqilin.db import get_db_client
from database_lib import DatabaseClient
from fastapi import APIRouter
from uuid import UUID

from .models import ObjectOrm, ObjectOut

router = APIRouter()

@router.get('/object/{object_id}')
async def get_object(object_id: UUID):
    my_database_client: DatabaseClient = get_db_client()
    with my_database_client.session() as session:
        return ObjectOut(**session.get(ObjectOrm, object_id))
```

## SQLAlchemy

Bingqilin provides an SQLAlchemy client class you can declare in config with the type `sqlalchemy`. This will return a `bingqilin.db.sqlalchemy:SQLAlchemyClient` instance after validation. The module also provides a couple convenience functions (`get_sync_db()` and `get_async_db()`) to inject a session object as a dependency:

```py hl_lines="1 13 16"
from bingqilin.db import get_sync_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from .models import ObjectOrm, ObjectOut

router = APIRouter()

@router.get('/object/{object_id}')
async def get_object(
    object_id: UUID, 
    db: Session = Depends(get_sync_db("the_other_db_client"))
):
    return ObjectOut(
        **db.query(ObjectOrm).filter(ObjectOrm.id==object_id).one()
    )
```