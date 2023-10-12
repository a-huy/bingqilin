from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field, AnyUrl, validator

from bingqilin.db import validate_databases
from bingqilin.db.models import DBDict


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
        description="The identifying name of the contact person/organization."
    )
    url: AnyUrl = Field(
        description="The URL pointing to the contact Information. MUST be in the format of a URL."
    )
    email: str = Field(
        description="The email address of the contact person/organization. "
        "MUST be in the format of an email address."
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
    openapi_tags: Optional[List[OpenAPITag]] = Field(
        default=None, description="A list of metadata for tags used in path operations."
    )
    servers: Optional[List[FastAPIServer]] = Field(
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


class ConfigModel(BaseModel):
    """
    This is the default config model. If no additional config values are defined, then these
    are defaults that are validated.
    """

    debug: bool = Field(
        default=True, description="Toggles debug features (do not use in production!)"
    )
    additional_config_files: List[str] = Field(
        default=[],
        description="Additional config files to load after the initial load "
        "(via an .env file or config.yaml)",
    )
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

    # The `Any` type will be replaced with the injected schema of all registered database
    # config models
    databases: DBDict[str, Union[dict, Any]] = Field(  # type: ignore
        default=DBDict(),
        description="Configuration for database connections. "
        "Each database is mapped by a string name to a DBConfig (or subclass) instance "
        "or a dict. If the config is an instance of DBConfig, then an attempt is made to "
        "initialize the client.",
    )

    fastapi: FastAPIConfig = FastAPIConfig()

    @validator("databases")
    def validate_databases(cls, databases):
        return validate_databases(databases)
