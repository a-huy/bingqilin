from typing import Any, Callable, Mapping, Type

from fastapi import FastAPI
from fastapi.openapi.constants import REF_TEMPLATE
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from bingqilin.conf import SETTINGS_SOURCES, ConfigModel, config
from bingqilin.db import DATABASE_CONFIG_MODELS
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

        if hasattr(config.data, "databases"):
            inject_registry_models_to_openapi(
                openapi_schema, "databases", DATABASE_CONFIG_MODELS, lambda m: m
            )

        if hasattr(config.data, "additional_config"):
            inject_registry_models_to_openapi(
                openapi_schema,
                "additional_config",
                SETTINGS_SOURCES,
                lambda s: s.__source_config_model__,
            )

        fastapi_app.openapi_schema = openapi_schema
        return fastapi_app.openapi_schema

    fastapi_app.openapi = openapi_with_config_schema


def _inject_config_schemas(
    schema: dict, registry: Mapping, model_getter_func: Callable[[Any], BaseModel]
):
    model_defs_dict = {}
    for value in registry.values():
        model = model_getter_func(value)
        model_schema = model.model_json_schema(
            ref_template=f"#/components/schemas/{config.model.__name__}/$defs/"
            + "{model}"
        )
        if sub_defs := model_schema.pop("$defs", None):
            for sub_name, sub_schema in sub_defs.items():
                model_defs_dict[sub_name] = sub_schema
        model_defs_dict[model.__name__] = model_schema
    schema.update(model_defs_dict)


def _inject_conf_property_refs(
    properties_schema: dict,
    registry: Mapping,
    model_getter_func: Callable[[Any], BaseModel],
):
    model_ref_list = [
        {
            "$ref": f"#/components/schemas/{config.model.__name__}/"
            + f"$defs/{model_getter_func(value).__name__}"
        }
        for value in registry.values()
    ]
    properties_schema["additionalProperties"] = {
        "anyOf": [{"type": "object"}] + model_ref_list
    }


def inject_registry_models_to_openapi(
    openapi_schema,
    config_field: str,
    registry: Mapping,
    model_getter_func: Callable[[Any], BaseModel],
):
    assert config.is_loaded
    if components := openapi_schema.get("components"):
        if schemas := components.get("schemas"):
            if config_schema := schemas.get(config.model.__name__):
                if defs := config_schema.get("$defs"):
                    _inject_config_schemas(defs, registry, model_getter_func)

            if properties := config_schema.get("properties"):
                if config_prop := properties.get(config_field):
                    _inject_conf_property_refs(config_prop, registry, model_getter_func)
