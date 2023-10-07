from typing import Type, Optional

from fastapi import FastAPI

from bingqilin.conf import ConfigModel, ConfigInitializer
from bingqilin.conf.openapi import add_config_model_to_openapi


def initialize(fastapi_app: FastAPI, config_model: Optional[Type[ConfigModel]] = None):
    ConfigInitializer.init(model=config_model)
    add_config_model_to_openapi(fastapi_app)
