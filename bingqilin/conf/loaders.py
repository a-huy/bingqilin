from functools import wraps
from io import StringIO


AVAILABLE_CONFIG_LOADERS = {}
LOADERS_BY_FILE_TYPES = {}


def config_loader(cls):
    AVAILABLE_CONFIG_LOADERS[cls.loader_type] = cls
    if cls.filetypes:
        for ft in cls.filetypes:
            LOADERS_BY_FILE_TYPES[ft.lstrip(".")] = cls

    @wraps(cls)
    def wrapper(*args, **kwargs):
        return cls(*args, **kwargs)

    return wrapper


class LoaderRequiresPackageInstalledError(Exception):
    def __init__(
        self, *args: object, loader_name: str = "", package_deps: str = ""
    ) -> None:
        super().__init__(*args)
        self.loader_name = loader_name
        self.package_deps = package_deps

    def __repr__(self) -> str:
        deps_string = ", ".join(self.package_deps)
        return f'Loader "{self.loader_name}" requires package(s) "{deps_string}" to be installed.'


class ConfigLoader(object):
    loader_type = None
    package_deps = ["pyyaml"]
    imported_pkg = None

    @classmethod
    def set_import(cls):
        raise NotImplementedError()

    @classmethod
    def check_dependencies(cls):
        try:
            cls.set_import()
        except ImportError:
            raise LoaderRequiresPackageInstalledError(cls.loader_type, cls.package_deps)

    @classmethod
    def load(cls, file_name):
        raise NotImplementedError()

    @classmethod
    def load_from_string(cls, config_string):
        raise NotImplementedError()


@config_loader
class YAMLConfigLoader(ConfigLoader):
    loader_type = "yaml"
    filetypes = [".yml", ".yaml"]
    package_deps = ["pyyaml"]

    @classmethod
    def set_import(cls):
        import yaml

        cls.imported_pkg = yaml

    @classmethod
    def load(cls, file_name):
        with open(file_name, "r") as yaml_file:
            config = cls.imported_pkg.safe_load(yaml_file)

        return config

    @classmethod
    def load_from_string(cls, config_string):
        return cls.imported_pkg.safe_load(StringIO(config_string))


@config_loader
class DotenvConfigLoader(ConfigLoader):
    loader_type = "dotenv"
    filetypes = [".env"]
    package_deps = ["dotenv"]

    path_delimiter = "__"

    @classmethod
    def set_import(cls):
        import dotenv

        cls.imported_pkg = dotenv

    @classmethod
    def _set_config_value(cls, config, key_parts, value):
        """
        Creates intermediary dicts for a given key path if they don't exist.
        """
        if len(key_parts) == 1:
            config[key_parts[0]] = value
            return

        if key_parts[0] not in config:
            config[key_parts[0]] = {}

        cls._set_config_value(config[key_parts[0]], key_parts[1:], value)

    @classmethod
    def _process_dotenv_dict(cls, dotenv_dict):
        config = {}
        for key, value in dotenv_dict.items():
            key_parts = key.lower().split(cls.path_delimiter)
            cls._set_config_value(config, key_parts, value)

        return config

    @classmethod
    def load(cls, file_name):
        return cls._process_dotenv_dict(cls.imported_pkg.dotenv_values(file_name))

    @classmethod
    def load_from_string(cls, config_string):
        return cls._process_dotenv_dict(
            cls.imported_pkg.dotenv_values(StringIO(config_string))
        )
