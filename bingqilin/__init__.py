from typing import Type, Optional

from fastapi import FastAPI

from bingqilin.conf import ConfigModel, ConfigInitializer


def initialize(fastapi_app: FastAPI, config_model: Optional[Type[ConfigModel]] = None):
    ConfigInitializer.init(model=config_model)
