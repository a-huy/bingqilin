from typing import Type, Optional, Union, Any

from fastapi import FastAPI

from bingqilin.conf import ConfigModel, initialize_config, config
from bingqilin.conf.openapi import add_config_model_to_openapi
from bingqilin.db import initialize_databases


def initialize(
    config_model: Optional[Type[ConfigModel]] = None,
    fastapi_app: Optional[FastAPI] = None,
    create_fastapi_app: bool = True,
    fastapi_kwargs: dict[str, Any] = {},
) -> Union[FastAPI, None]:
    """
    Initializes all the default features of bingqilin.
    You can opt to manually initialize whatever features you'd like,
    but most of them are built on top of a loaded config and require
    `initialize_config()` to be called first.

    If a FastAPI app is passed into this `initialize()` function,
    then its metadata will not be modified by the `fastapi` config.
    """
    initialize_config(model=config_model)

    if not fastapi_app and create_fastapi_app:
        app_init_kwargs = dict(config.data.fastapi)
        app_init_kwargs.update(**fastapi_kwargs)
        fastapi_app = FastAPI(**app_init_kwargs)

    if db_config := config.data.databases:
        initialize_databases(db_config)

    if fastapi_app and config.data.add_config_model_schema:
        add_config_model_to_openapi(fastapi_app)

    return fastapi_app
