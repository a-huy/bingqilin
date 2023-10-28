from datetime import datetime
from typing import Any, Self, Type

from pydantic_settings import BaseSettings

from bingqilin.logger import bq_logger
from bingqilin.signal import RECONFIGURE_SIGNAL, signal_handler

from .models import ConfigModel

logger = bq_logger.getChild("conf")


class SettingsManager:
    data: Any
    last_loaded_at: datetime

    def __init__(self) -> None:
        super().__init__()
        self._get_data_annotated_class()

    def _get_data_annotated_class(self) -> Type[BaseSettings]:
        data_class = self.__annotations__.get("data")
        if not data_class:
            raise ValueError("No annotated data attribute defined.")
        if not issubclass(data_class, BaseSettings):
            raise RuntimeError(
                "Annotated type for config data is not a subclass of BaseSettings: "
                f"{data_class} ({type(data_class)})"
            )
        return data_class

    def load(self, allow_reconfigure: bool = True, **settings_init_kwargs) -> Self:
        data_class = self._get_data_annotated_class()

        def reload():
            self.data = data_class(**settings_init_kwargs)
            self.last_loaded_at = datetime.now()

        reload()

        if allow_reconfigure:
            # If a different settings model is being used, then assume that reconfiguring
            # is allowed (otherwise it can be disabled via the parameter)
            if not isinstance(self.data, ConfigModel) or self.data.allow_reconfigure:
                signal_handler(RECONFIGURE_SIGNAL)(reload)

        return self
