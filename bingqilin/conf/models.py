from typing import Optional, List, Any
from pydantic import BaseModel, Field, AnyUrl, EmailStr


class FastAPILicenseInfo(BaseModel):
    name: str
    identifier: str
    url: AnyUrl


class FastAPIContact(BaseModel):
    name: str
    url: AnyUrl
    email: str


class FastAPIServer(BaseModel):
    url: AnyUrl
    description: str


class OpenAPITagExternalDoc(BaseModel):
    description: str
    url: AnyUrl


class OpenAPITag(BaseModel):
    name: str
    description: Optional[str] = ""
    externalDocs: Optional[OpenAPITagExternalDoc] = None


class FastAPIConfig(BaseModel):
    """
    Config that will be passed to the FastAPI app during initialization, if
    bingqilin is expected to create the app instance.
    """

    title: str = Field(default="FastAPI")
    summary: Optional[str] = Field(default=None)
    description: str = Field(default="")
    version: str = Field(default="0.1.0")
    openapi_url: str = Field(default="/openapi.json")
    openapi_tags: Optional[List[OpenAPITag]] = None
    servers: Optional[List[FastAPIServer]] = None
    redirect_slashes: bool = True
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    swagger_ui_oauth2_redirect_url: str = "/docs/oauth2-redirect"
    swagger_ui_init_oauth: Optional[dict[str, Any]] = None
    terms_of_service: Optional[str] = None
    contact: Optional[FastAPIContact] = None
    license_info: Optional[FastAPILicenseInfo] = None
    openapi_prefix: str = ""
    root_path: str = ""
    root_path_in_servers: bool = True
    deprecated: Optional[bool] = None
    include_in_schema: bool = True
    swagger_ui_parameters: Optional[dict[str, Any]] = None
    separate_input_output_schemas: bool = True


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
        description="Additional config files to load after the initial load (via an .env file or config.yaml)",
    )
    add_config_model_schema: bool = Field(
        default=True,
        description="Add the loaded config model schema to the OpenAPI spec as well as the docs",
    )
    flatten_config_schema: bool = Field(
        default=False,
        description="Flattens all embedded models inside the config model so that they get listed as a "
        "top-level schema on the docs page. Otherwise, they will show up as a list under the $defs field "
        "in the schema for the config model.",
    )

    fastapi: FastAPIConfig = FastAPIConfig()
