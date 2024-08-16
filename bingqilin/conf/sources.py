from configparser import ConfigParser
from deprecated import deprecated
from pathlib import Path
from typing import Any, Dict, List, Optional, Self, Type, Union

from pydantic import BaseModel, ConfigDict, create_model
from pydantic.fields import FieldInfo
from pydantic.types import FilePath
from pydantic_settings import (
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SecretsSettingsSource,
)
from pydantic_settings.main import BaseSettings
from pydantic_settings.sources import ENV_FILE_SENTINEL, DotenvType
from typing_extensions import Literal

from bingqilin.logger import bq_logger
from bingqilin.utils.dict import merge
from bingqilin.utils.types import RegistryMeta, get_annotation_literal_value

logger = bq_logger.getChild("conf.sources")

SETTINGS_SOURCES: Dict[str, Type["BingqilinSettingsSource"]] = {}


class MissingDependencyError(Exception):
    def __init__(
        self,
        settings_source: "BingqilinSettingsSource",
        *args: object,
    ) -> None:
        self.source_type = get_annotation_literal_value(settings_source, "type")
        self.package_deps = settings_source.package_deps or []
        deps_string = ", ".join(self.package_deps)
        self.message = (
            f'Settings source "{self.source_type}" requires package(s) '
            + f'"{deps_string}" to be installed.'
        )
        super().__init__(self.message)


class SourcesRegistryMeta(RegistryMeta):
    registry_field: Literal["type"]
    root_class: Literal["bingqilin.conf.sources:BingqilinSettingsSource"]

    def __new__(
        __mcls: type[Self],
        __name: str,
        __bases: tuple[type, ...],
        __namespace: dict[str, Any],
        **kwargs: Any,
    ) -> Self:
        new_class = super().__new__(__mcls, __name, __bases, __namespace, **kwargs)
        root_class_name = __mcls.get_root_class_name()
        if __name != root_class_name:
            __mcls.create_shadow_config_model(new_class)  # type: ignore
        return new_class

    @classmethod
    def get_registry(cls):
        return SETTINGS_SOURCES

    @classmethod
    def create_shadow_config_model(cls, new_class: "BingqilinSettingsSource"):
        """This method contains logic to create a shadow model that uses the defined
        SourceConfig model on the parent settings source class to add an additional
        "source" field. Since this is the model that will be used as one of the possible
        schemas in `ConfigModel.additional_config`, this injection is done so that the
        SourceConfig definition doesn't have to include a redundant Literal[<source_type>]
        field.

        Args:
            new_class (BingqilinSettingsSource): The settings source class to inject
                the shadow model into.
        """
        registry_field_value = cls.get_registry_field_literal()
        type_value = new_class.get_registry_type(registry_field_value)  # type: ignore
        model_name = new_class.SourceConfig.model_config.get("title")
        if not model_name:
            model_name = f"{type_value.title()}SourceConfig"
        new_class.__source_config_model__ = create_model(
            model_name,
            source=(Literal[type_value], FieldInfo(exclude=True)),  # type: ignore
            __base__=new_class.SourceConfig,
        )


class BaseSourceConfig(BaseModel):
    """
    This is a pydantic model that will be used by the config system to validate
    an entry in the `additional_files` list.
    """

    source: Literal[""]


class BingqilinSettingsSource(
    PydanticBaseSettingsSource, metaclass=SourcesRegistryMeta
):
    type: Literal[""]
    package_deps: List[str] = []
    imported_pkg: Any = None

    # See `SourcesRegistryMeta.create_shadow_config_model()`
    __source_config_model__: Type[BaseSourceConfig]

    class SourceConfig(BaseSourceConfig):
        pass

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        return value

    def __call__(self) -> dict[str, Any]:
        data: Dict[str, Any] = {}
        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field, field_name
            )
            field_value = self.prepare_field_value(
                field_name, field, field_value, value_is_complex
            )
            if field_value is not None:
                data[field_key] = field_value

        return data


class BingqilinDotEnvSettingsSource(DotEnvSettingsSource, BingqilinSettingsSource):
    type: Literal["dotenv"]

    class SourceConfig(BaseSourceConfig):
        env_file: DotenvType = ENV_FILE_SENTINEL
        env_file_encoding: Optional[str] = None
        case_sensitive: Optional[bool] = None
        env_prefix: Optional[str] = None
        env_nested_delimiter: Optional[str] = None

        model_config = ConfigDict(title="DotEnvSourceConfig")


class BingqilinSecretSettingsSource(SecretsSettingsSource, BingqilinSettingsSource):
    type: Literal["secrets"]

    class SourceConfig(BaseSourceConfig):
        secrets_dir: Optional[Union[str, Path]] = None
        case_sensitive: Optional[bool] = None
        env_prefix: Optional[str] = None

        model_config = ConfigDict(title="SecretsSourceConfig")


class YamlSettingsSource(BingqilinSettingsSource):
    type: Literal["yaml"]
    package_deps = ["pyyaml"]

    class SourceConfig(BaseSourceConfig):
        files: List[FilePath]

        model_config = ConfigDict(title="YamlSourceConfig")

    @deprecated(
        version="0.6.1",
        reason="Pydantic settings has support for YAML files as of 2.2.0",
    )
    def __init__(self, settings_cls: Type[BaseSettings], files=None):
        super().__init__(settings_cls)
        self.files = files or settings_cls.model_config.get("yaml_files") or []
        configs = []
        try:
            for filename in self.files:
                configs.append(self._load_file(filename))
        except (ModuleNotFoundError, ImportError):
            logger.warning("YamlSettingsSource: file name %s not found.", filename)
            raise MissingDependencyError(self)

        self.loaded_config = merge({}, *configs)

    def _load_file(self, file_name: FilePath) -> dict:
        import yaml

        try:
            with open(file_name, "r") as yaml_file:
                return yaml.safe_load(yaml_file)
        except FileNotFoundError:
            return {}

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return self.loaded_config.get(field_name), field_name, False


class IniSettingsSource(BingqilinSettingsSource):
    type: Literal["ini"]

    class SourceConfig(BaseSourceConfig):
        files: List[Path]
        file_encoding: Optional[str] = None

        model_config = ConfigDict(title="IniSourceConfig")

    def __init__(
        self, settings_cls: Type[BaseSettings], files=None, file_encoding=None
    ):
        super().__init__(settings_cls)
        self.files = files or settings_cls.model_config.get("ini_files") or []
        self.file_encoding = (
            file_encoding
            if file_encoding is not None
            else settings_cls.model_config.get("ini_file_encoding") or None
        )

        parser = ConfigParser()
        for filename in self.files:
            parser.read(filename)

        config = {}
        sections = parser.sections()
        for section in sections:
            config[section] = parser.options(section)

        self.loaded_config = config

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return self.loaded_config.get(field_name), field_name, False
