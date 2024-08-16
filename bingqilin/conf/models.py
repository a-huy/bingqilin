import logging

from typing import Any, Optional, Sequence, TypeVar, Union, List, Tuple

from fastapi import FastAPI
from pydantic import AfterValidator, AnyUrl, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource
from typing_extensions import Annotated

from bingqilin.conf.sources import IniSettingsSource
from bingqilin.db import validate_databases
from bingqilin.db.models import DBConfig
from bingqilin.utils.types import AttrKeysDict

DBConfigType = TypeVar("DBConfigType", bound=DBConfig)
DEFAULT_RECONFIGURE_URL = "/reconfigure"


class FastAPILicenseInfo(BaseModel):
    name: str = Field(description="The license name used for the API.")
    identifier: str = Field(
        description="An [SPDX](https://spdx.github.io/spdx-spec/latest/) license "
        "expression for the API. The `identifier` field is mutually exclusive of the "
        "`url` field."
    )
    url: AnyUrl = Field(
        description="A URL to the license used forf the API. MUST be in the format of a URL."
    )


class FastAPIContact(BaseModel):
    name: str = Field(
        default="",
        description="The identifying name of the contact person/organization.",
    )
    url: AnyUrl = Field(
        default="",
        description="The URL pointing to the contact Information. MUST be in the format of a URL.",
    )
    email: str = Field(
        default="",
        description="The email address of the contact person/organization. "
        "MUST be in the format of an email address.",
    )


class FastAPIServer(BaseModel):
    url: AnyUrl
    description: str


class OpenAPITagExternalDoc(BaseModel):
    description: str = Field(
        description="A `str` with a short description of the external docs."
    )
    url: AnyUrl = Field(
        description="A `str` with the URL for the external documentation."
    )


class OpenAPITag(BaseModel):
    name: str = Field(
        description="A `str` with the same tag name you use in the `tags` parameter in your "
        "path operations and `APIRouter`s."
    )
    description: Optional[str] = Field(
        default="",
        description="A `str` with a short description for the tag. "
        "It can contain Markdown and will be shown in the docs UI.",
    )
    externalDocs: Optional[OpenAPITagExternalDoc] = Field(
        default=None, description="A `dict` describing external documentation."
    )


class FastAPIConfig(BaseModel):
    """
    Config that will be passed to the FastAPI app during initialization, if
    bingqilin is expected to create the app instance.
    """

    title: str = Field(default="FastAPI", description="Title of your FastAPI app.")
    summary: Optional[str] = Field(
        default=None, description="Short explanation of your FastAPI app."
    )
    description: str = Field(default="", description="Description of your FastAPI app.")
    version: str = Field(default="0.1.0", description="Version of your FastAPI app.")
    openapi_url: str = Field(
        default="/openapi.json",
        description="Path for the OpenAPI schema JSON dump.",
    )
    openapi_tags: Optional[Sequence[OpenAPITag]] = Field(
        default=None, description="A list of metadata for tags used in path operations."
    )
    # Overriding the OpenAPI version as an init parameter is not allowed by FastAPI.
    # It is made available here to update it when calling `create_app()`, but it makes
    # no attempt to ensure that the OpenAPI JSON is compatible with the new version.
    openapi_version: Optional[str] = None
    servers: Optional[Sequence[FastAPIServer]] = Field(
        default=None,
        description="Specify additional servers in the OpenAPI schema. "
        "This can be used to test against other environments from the same docs page. "
        "More info [here](https://fastapi.tiangolo.com/advanced/behind-a-proxy/#additional-servers).",
    )
    redirect_slashes: bool = True
    docs_url: str = Field(
        default="/docs",
        description="Path for the Swagger UI page for the OpenAPI schema.",
    )
    redoc_url: str = Field(
        default="/redoc", description="Path for the ReDoc page for the OpenAPI schema."
    )
    swagger_ui_oauth2_redirect_url: str = "/docs/oauth2-redirect"
    swagger_ui_init_oauth: Optional[dict[str, Any]] = None
    terms_of_service: Optional[str] = Field(
        default=None,
        description="A URL to the Terms of Service for the API. If provided, this has to be a URL.",
    )
    contact: Optional[FastAPIContact] = Field(default=None)
    license_info: Optional[FastAPILicenseInfo] = Field(default=None)
    root_path: str = Field(
        default="",
        description="For use when the app is behind a proxy. "
        "More info [here](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).",
    )
    root_path_in_servers: bool = Field(
        default=True,
        description="Disable to remove prepending the root path to specified server URLs.",
    )
    deprecated: Optional[bool] = Field(
        default=None, description="Enable to mark _all_ path operations as deprecated."
    )
    include_in_schema: bool = Field(
        default=True,
        description="Disable to exclude _all_ path perations from the OpenAPI schema.",
    )
    swagger_ui_parameters: Optional[dict[str, Any]] = Field(
        default=None,
        description="A list of valid parameters can be found "
        "[here](https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/).",
    )
    separate_input_output_schemas: bool = Field(
        default=True,
        description="Use different schemas for validation vs. serialization for the same model. "
        "More info [here](https://fastapi.tiangolo.com/how-to/separate-openapi-schemas/).",
    )

    def create_app(self, **additional_options) -> FastAPI:
        app_options = self.model_dump()
        app_options.update(additional_options)
        app = FastAPI(**app_options)
        if self.openapi_version:
            app.openapi_version = self.openapi_version
        return app


class ConfigModelConfigDict(SettingsConfigDict, total=False):
    ini_files: Optional[Sequence[str]]
    ini_file_encoding: Optional[str]


class ConfigModel(BaseSettings):
    """
    This is the default config model. If no additional config values are defined, then these
    are defaults that are validated.
    """

    debug: bool = Field(
        default=True,
        description="Toggles debug features (do not enable in production!)",
    )
    loglevel: int = Field(default=logging.INFO, description="Default logging level")
    add_config_model_schema: bool = Field(
        default=True,
        description="Add the loaded config model schema to the OpenAPI spec as well as the docs.",
    )
    flatten_config_schema: bool = Field(
        default=False,
        description="Flattens all embedded models inside the config model so that they "
        "get listed as a top-level schema on the docs page. Otherwise, they will show up "
        "as a list under the $defs field in the schema for the config model.",
    )
    log_validation_errors: bool = Field(
        default=False,
        description="Adds a `RequestValidationError` exception handler "
        "that logs the invalid request and its validation errors. Useful for troubleshooting "
        "routes that support a lot of different types of requests, such as third-party "
        "callback handlers.",
    )
    allow_reconfigure: bool = Field(
        default=True,
        description="Enables reconfiguring settings and related constructs. If disabled, "
        "this will prevent any handlers being added to the reconfigure signal as well as "
        "the path operation from being added to the app's router.",
    )
    reconfigure_url: Optional[str] = Field(
        default=DEFAULT_RECONFIGURE_URL,
        description="Path to add the handler to trigger a reconfigure via an HTTP POST "
        "request. Set this to null or empty string to disable.",
    )
    # The `DBConfigType` type will be replaced with the injected schema of all registered
    # database config models in the OpenAPI schema
    databases: Annotated[
        AttrKeysDict[str, Union[dict, DBConfigType]], AfterValidator(validate_databases)  # type: ignore
    ] = Field(  # type: ignore
        default=AttrKeysDict(),
        description="Configuration for database connections. "
        "Each database is mapped by a string name to a DBConfig (or subclass) instance "
        "or a dict. If the config is an instance of DBConfig, then an attempt is made to "
        "initialize the client.",
    )

    # NOTE: These management config fields aren't put into their own model, because by default,
    # the user has no way to pass in any delimiter options when invoking core commands.
    # These fields must live in the top level config model.
    management_settings: Optional[str] = Field(
        default=None,
        description="A string using Python path syntax that points to the "
        "application-specific settings instance. This is used for management utility scripts.",
    )
    management_additional_commands: List[Union[str, Tuple[str, str]]] = Field(
        default=list(),
        description="A list of Python module paths where additional commands can be found.",
    )

    fastapi: FastAPIConfig = FastAPIConfig()

    @classmethod
    def add_settings_sources(
        cls, settings_cls: type[BaseSettings]
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        This classmethod is intended to be overridden and implemented by subclasses.

        The settings sources instances returned here will be appended to the end
        of the `settings_customise_sources()` list, giving them the highest precedence.

        Args:
            settings_cls (type[BaseSettings]): settings class

        Returns:
            tuple[PydanticBaseSettingsSource, ...]: A tuple of initialized settings sources
        """
        return tuple()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            IniSettingsSource(settings_cls),
        ) + (cls.add_settings_sources(settings_cls) or tuple())


ConfigModelType = TypeVar("ConfigModelType", bound=ConfigModel)
