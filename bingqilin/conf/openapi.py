from typing import Type

from fastapi import FastAPI
from fastapi.openapi.constants import REF_TEMPLATE
from fastapi.openapi.utils import get_openapi

from bingqilin.conf import config, ConfigModel
from bingqilin.db import inject_database_config_models_openapi
from bingqilin.logger import bq_logger


logger = bq_logger.getChild("conf.routes")


def get_flat_config_model_schema(config_model: Type[ConfigModel]):
    json_schema = config_model.model_json_schema(ref_template=REF_TEMPLATE)
    defs_key = "$defs"
    if defs_key not in json_schema:
        return {config_model.__name__: json_schema}

    defs = json_schema.pop(defs_key)
    defs[config_model.__name__] = json_schema
    return defs


def add_config_model_to_openapi(fastapi_app: FastAPI):
    if not (config.is_loaded):
        logger.warning(
            "Attempting to modify the app's OpenAPI with the config model before config is loaded."
        )
        return

    config_model = config.model or ConfigModel

    def openapi_with_config_schema():
        if fastapi_app.openapi_schema:
            return fastapi_app.openapi_schema

        openapi_schema = get_openapi(
            title=fastapi_app.title,
            version=fastapi_app.version,
            openapi_version=fastapi_app.openapi_version,
            summary=fastapi_app.summary,
            description=fastapi_app.description,
            terms_of_service=fastapi_app.terms_of_service,
            contact=fastapi_app.contact,
            license_info=fastapi_app.license_info,
            routes=fastapi_app.routes,
            webhooks=fastapi_app.webhooks.routes,
            tags=fastapi_app.openapi_tags,
            servers=fastapi_app.servers,
            separate_input_output_schemas=fastapi_app.separate_input_output_schemas,
        )
        openapi_schema.setdefault("components", {})
        openapi_schema["components"].setdefault("schemas", {})

        if config.data.flatten_config_schema:
            openapi_schema["components"]["schemas"].update(
                get_flat_config_model_schema(config_model)
            )
        else:
            openapi_schema["components"]["schemas"][
                config_model.__name__
            ] = config_model.model_json_schema(
                ref_template=f"#/components/schemas/{config_model.__name__}/$defs/"
                + "{model}"
            )

        if config.data.databases:
            inject_database_config_models_openapi(openapi_schema, config)

        fastapi_app.openapi_schema = openapi_schema
        return fastapi_app.openapi_schema

    fastapi_app.openapi = openapi_with_config_schema
