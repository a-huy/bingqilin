from typing import Type, Optional

from fastapi import FastAPI

from bingqilin.conf import ConfigModel, initialize_config, config
from bingqilin.conf.openapi import add_config_model_to_openapi


def initialize(
    config_model: Optional[Type[ConfigModel]] = None, **fastapi_kwargs
) -> FastAPI:
    """
    If a FastAPI app is passed into this `initialize()` function,
    then its metadata will not be modified by the `fastapi` config.
    """
    initialize_config(model=config_model)
    app_init_kwargs = dict(config.data.fastapi)
    app_init_kwargs.update(**fastapi_kwargs)
    fastapi_app = FastAPI(**app_init_kwargs)
    if config.data.add_config_model_schema:
        add_config_model_to_openapi(fastapi_app)
    return fastapi_app
