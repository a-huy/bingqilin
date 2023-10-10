import os

from typing import Type, Optional, Any

from bingqilin.logger import bq_logger
from bingqilin.utils.dict import merge

from .loaders import ConfigLoader, AVAILABLE_CONFIG_LOADERS, LOADERS_BY_FILE_TYPES
from .models import ConfigModel


logger = bq_logger.getChild("conf")
DEFAULT_CONFIG_FILE_NAME = "config.yml"


class Config:
    model: Type[ConfigModel] = ConfigModel
    # This should be an instance of a model derived from ConfigModel, but since the
    # type can change during runtime, it is annotated with `Any` to suppress type
    # checking errors.
    data: Any = ConfigModel()
    is_loaded: bool = False

    def __init__(self, model: Optional[Type[ConfigModel]] = None) -> None:
        if not model:
            model = ConfigModel
        self.set_model(model)

    def set_model(self, model: Type[ConfigModel]) -> None:
        self.model = model

    def merge(self, configs):
        current = self.data.model_dump()
        merged = merge(current, *configs)
        self.data = self.model.model_validate(merged)


def get_default_config_files():
    # Default to config.yml and .env files
    return [
        os.path.join(os.path.curdir, DEFAULT_CONFIG_FILE_NAME),
        os.path.join(os.path.curdir, ".env"),
    ]


def load_config_files(config_files):
    def _get_suffix(cf_name):
        if not cf_name:
            return
        i = cf_name.rfind(".")
        if i == -1:
            return
        return cf_name[i:]

    def _load_file(cf):
        if not os.path.exists(cf):
            logger.warning("Config file %s does not exist. Skipping.", cf)
            return

        suffix = _get_suffix(cf)
        if suffix:
            normalized_suffix = suffix.lstrip(".")
            if normalized_suffix in LOADERS_BY_FILE_TYPES:
                loader: Type[ConfigLoader] = LOADERS_BY_FILE_TYPES[normalized_suffix]
                loader.check_dependencies()
                return loader.load(cf)

    configs = []
    for c_file in config_files:
        _config = _load_file(c_file)
        configs.append(_config)
    return configs


def update(config_files):
    if not config_files:
        logger.warning("No config files specified. Nothing to do.")
        return
    new_configs = load_config_files(config_files)
    if not new_configs:
        logger.warning("Could not read any specified config files.")
        return

    config.merge(new_configs)


def initialize_config(
    config_files=None, model: Optional[Type[ConfigModel]] = None
) -> Config:
    if not config_files:
        default_configs = get_default_config_files()
        config_files = [_c for _c in default_configs if os.path.exists(_c)]
        if not config_files:
            logger.warning(
                "No config files specified, and none of the default configs could be found."
            )

    configs = load_config_files(config_files)
    if config_files and not configs:
        # TODO: Attempt to parse an unrecognized file type?
        raise Exception("None of the specified config files were able to be loaded.")

    if not model:
        model = ConfigModel

    config.set_model(model)
    config.merge(configs)

    if additional_files := config.data.additional_config_files:
        update(additional_files)

    config.is_loaded = True
    return config


def load_from_string(config_string, loader_type) -> Config:
    if loader_type not in AVAILABLE_CONFIG_LOADERS:
        raise ValueError(f"Loader with type {loader_type} not found.")

    config_dict = AVAILABLE_CONFIG_LOADERS[loader_type].load_from_string(config_string)

    config.merge(config_dict)
    return config


config = Config()
