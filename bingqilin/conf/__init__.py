import os

from collections.abc import Sequence, Mapping
from typing import Any, Type, Optional, List

from pydantic import BaseModel, ValidationError

from bingqilin.logger import bq_logger

from .loaders import ConfigLoader, AVAILABLE_CONFIG_LOADERS, LOADERS_BY_FILE_TYPES


logger = bq_logger.getChild('conf')
DEFAULT_CONFIG_FILE_NAME = 'config.yml'
ENV_PATH_DELIMITER = '__'


class ConfigError(Exception):
    pass


class ConfigModel(BaseModel):

    debug: bool = True
    additional_config_files: List[str] = []


class Config:
    PATH_DELIMITER = '.'

    _validated = None

    is_loaded = False
    validation_error = None

    def __init__(
        self,
        initial_config: Optional[dict] = None,
        model: Optional[Type[BaseModel]] = None,
    ) -> None:
        self.config = initial_config or {}
        self.model = model

    def _get_from_config(
        self,
        path_parts: list,
        conf_child: Sequence | Mapping,
        default=None,
        create_if_missing_key: bool = False,
    ):
        if not path_parts:
            return conf_child

        part = path_parts.pop(0)
        is_conf_sequence = isinstance(conf_child, Sequence)
        if is_conf_sequence:
            try:
                part = int(part)
            except ValueError:
                raise ConfigError(
                    f'Attempting to get "{part}" from {conf_child}, '
                    'but config child is a sequence and index cannot be converted to an int.'
                )

        is_sequence_get = is_conf_sequence and isinstance(part, int)

        if not path_parts:  # Base case
            if is_sequence_get:
                return conf_child[part] if len(conf_child) > part else default
            else:
                if create_if_missing_key:
                    conf_child[part] = {}
                return conf_child.get(part, default)

        if (
            isinstance(conf_child, Mapping)
            and part not in conf_child
            and create_if_missing_key
        ):
            conf_child[part] = {}

        child = conf_child[part]
        return self._get_from_config(path_parts, child, default, create_if_missing_key)

    def get(self, key_path: str, default=None, is_bool=False):
        parts = key_path.split(self.PATH_DELIMITER)
        return self._get_from_config(parts, self.config, default)

    def set(self, key_path: str, new_value, create_parents=True):
        """
        NOTE: This cannot modify a sequence. The final object to update must be a value in a dict.
        """
        parts = key_path.split(self.PATH_DELIMITER)
        if len(parts) == 1:
            self.config[key_path] = new_value
            return

        conf_child = self.config
        for part in parts[:-1]:
            if part not in conf_child and create_parents:
                conf_child[part] = {}
            conf_child = conf_child[part]

        if not isinstance(conf_child, Mapping):
            raise ConfigError(
                'Only mappings values can be set. '
                f'Value at path "{self.PATH_DELIMITER.join(parts[:-1])}" '
                f'is of type {type(conf_child)}.'
            )
        conf_child[parts[-1]] = new_value

    def _iter_config_key_paths(self, config: Mapping, prefix=''):
        for key, value in config.items():
            if prefix:
                curr_path = '.'.join([prefix, key])
            else:
                curr_path = key
            if isinstance(value, Mapping):
                yield from self._iter_config_key_paths(config[key], curr_path)
            else:
                yield curr_path, value

    def merge(self, configs):
        for config in configs:
            if not config:
                continue
            for key_path, value in self._iter_config_key_paths(config):
                self.set(key_path, value)

    def set_model(self, model: Type[BaseModel]):
        self.model = model

    @property
    def is_valid(self):
        if not self.model:
            return True
        try:
            self._validated = self.model(**self.config)
            return True
        except ValidationError as exn:
            self.validation_error = exn
            return False

    @property
    def errors(self):
        if not self.validation_error:
            return None
        return self.validation_error.errors()

    def __getattribute__(self, __name: str) -> Any:
        try:
            return super().__getattribute__(__name)
        except AttributeError as exn:
            try:
                return getattr(self._validated, __name)
            except AttributeError:
                raise exn


# TODO: Support merging multiple config files?
class ConfigInitializer:
    @classmethod
    def get_default_config_files(cls):
        # Default to config.yml and .env files
        return [
            os.path.join(os.path.curdir, DEFAULT_CONFIG_FILE_NAME),
            os.path.join(os.path.curdir, '.env'),
        ]

    @classmethod
    def load_config_files(cls, config_files):
        def _get_suffix(cf_name):
            if not cf_name:
                return
            i = cf_name.rfind('.')
            if i == -1:
                return
            return cf_name[i:]

        def _load_file(cf):
            if not os.path.exists(cf):
                logger.warning('Config file %s does not exist. Skipping.', cf)
                return

            suffix = _get_suffix(cf)
            if suffix:
                normalized_suffix = suffix.lstrip('.')
                if normalized_suffix in LOADERS_BY_FILE_TYPES:
                    loader: Type[ConfigLoader] = LOADERS_BY_FILE_TYPES[normalized_suffix]
                    loader.check()
                    return loader.load(cf)

        configs = []
        for c_file in config_files:
            _config = _load_file(c_file)
            configs.append(_config)
        return configs

    @classmethod
    def init(cls, config_files=None, model=None) -> Config:
        if not config_files:
            default_configs = cls.get_default_config_files()
            config_files = [_c for _c in default_configs if os.path.exists(_c)]
            if not config_files:
                logger.warning(
                    'No config files specified, and none of the default configs could be found.'
                )

        configs = cls.load_config_files(config_files)
        if config_files and not configs:
            # TODO: Attempt to parse an unrecognized file type?
            raise Exception(
                'None of the specified config files were able to be loaded.'
            )

        # TODO: normalize?
        global CONFIG
        CONFIG.merge(configs)
        CONFIG.is_loaded = True
        if model:
            CONFIG.set_model(model)
            if not CONFIG.is_valid:
                raise RuntimeError(CONFIG.errors)
        return CONFIG

    @classmethod
    def update(cls, config_files):
        if not config_files:
            logger.warning('No config files specified. Nothing to do.')
            return
        new_configs = cls.load_config_files(config_files)
        if not new_configs:
            logger.warning('Could not read any specified config files.')
            return

        global CONFIG
        CONFIG.merge(new_configs)

    @classmethod
    def load_from_string(cls, config_string, loader_type) -> Config:
        if loader_type not in AVAILABLE_CONFIG_LOADERS:
            raise ValueError(f'Loader with type {loader_type} not found.')

        config = AVAILABLE_CONFIG_LOADERS[loader_type].load_from_string(config_string)

        global CONFIG
        CONFIG.config = config or {}
        CONFIG.is_loaded = True
        return CONFIG


CONFIG = Config()
