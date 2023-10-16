import copy

from typing import Type, Optional, List, Dict, Any

from bingqilin.logger import bq_logger
from bingqilin.utils.dict import merge

from .models import ConfigModel
from .sources import SETTINGS_SOURCES, BingqilinSettingsSource


logger = bq_logger.getChild("conf")


class Config:
    model: Type[ConfigModel] = ConfigModel
    # This should be an instance of a model derived from ConfigModel, but since the
    # type can change during runtime, it is annotated with `Any` to suppress type
    # checking errors.
    data: ConfigModel
    is_loaded: bool = False

    def __init__(self, model: Optional[Type[ConfigModel]] = None) -> None:
        if not model:
            model = ConfigModel
        self.model = model

    def set_model(self, model: Type[ConfigModel]) -> None:
        self.model = model
        # Create an instance that is an empty shell. We need to collect all the
        # processed configs before we run any validation.
        self.data = model.model_construct()

    def merge(self, configs: List[Dict[str, Any]]):
        merged = merge(self.data.model_dump(), *configs)
        for field, value in merged.items():
            setattr(self.data, field, value)

        self.data.validate()


def load_additional_config(config: Config):
    sources: List[BingqilinSettingsSource] = []
    additional_config: List[Dict[str, Any]] = config.data.additional_config
    for source_config in additional_config:
        assert "source" in source_config
        # Create a copy. The source class does not accept a "source" parameter,
        # but the data going into the model will require it.
        config_copy = copy.copy(source_config)
        source_type = config_copy.pop("source")
        assert source_type in SETTINGS_SOURCES
        source_class = SETTINGS_SOURCES[source_type]
        sources.append(source_class(config.data.__class__, **config_copy))

    config.merge([s() for s in sources])


def initialize_config(model: Optional[Type[ConfigModel]] = None) -> Config:
    """Takes a `ConfigModel` or a subclass and creates an instance with loaded config
    value.

    This initialization doesn't immediately create the `ConfigModel` instance, because
    it needs to do a second processing step for reading `additional_config` files.
    The initialization steps are as follows:

    1. The internal function for collecting settings values using the `pydantic_settings`
    default sources is called (the normal behavior for creating a `BaseSettings()` instance)/
    2. The `additional_config` field is read from the initial values. If there is a non-empty
    list, the parameters are parsed and passed into the appropriate source classes to load
    additional files.
    3. All the collected config data are deep merged.
    4. Finally, the internal validation function is called on the config model with the
    merged data.

    Args:
        model (Optional[Type[ConfigModel]], optional): A subclass of ConfigModel.
        Defaults to None.

    Returns:
        Config: The loaded Config object that can be imported from other parts of the app.
    """
    if not model:
        model = ConfigModel

    config.set_model(model)
    # Trigger the normal behavior of Pydantic's BaseSettings when initialized
    initial_values = config.data._settings_build_values({})
    configs = []

    if additional_config := initial_values.get("additional_config"):
        sources: List[BingqilinSettingsSource] = []
        for source_config in additional_config:
            assert "source" in source_config
            config_copy = copy.copy(source_config)
            source_type = config_copy.pop("source")
            assert source_type in SETTINGS_SOURCES
            source_class = SETTINGS_SOURCES[source_type]
            sources.append(source_class(config.data.__class__, **config_copy))

        configs += [s() for s in sources]

    # Finally, run a validation pass
    merged = merge(initial_values, *configs)
    config.data.__pydantic_validator__.validate_python(
        merged, self_instance=config.data
    )

    config.is_loaded = True
    return config


config = Config()
