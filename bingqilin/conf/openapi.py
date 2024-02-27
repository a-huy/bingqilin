from typing import Any, Callable, Mapping

from fastapi import FastAPI
from fastapi.openapi.constants import REF_TEMPLATE
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from bingqilin.db import DATABASE_CONFIG_MODELS
from bingqilin.logger import bq_logger

logger = bq_logger.getChild("conf.routes")


def get_flat_config_model_schema(config_model: BaseModel):
    json_schema = config_model.model_json_schema(ref_template=REF_TEMPLATE)
    defs_key = "$defs"
    if defs_key not in json_schema:
        return {config_model.__name__: json_schema}

    defs = json_schema.pop(defs_key)
    defs[config_model.__name__] = json_schema
    return defs


def add_config_model_to_openapi(
    settings_data: BaseModel, app: FastAPI, flatten_schema: bool = False
):
    def openapi_with_config_schema():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            webhooks=app.webhooks.routes,
            tags=app.openapi_tags,
            servers=app.servers,
            separate_input_output_schemas=app.separate_input_output_schemas,
        )
        openapi_schema.setdefault("components", {})
        openapi_schema["components"].setdefault("schemas", {})

        if flatten_schema:
            openapi_schema["components"]["schemas"].update(
                get_flat_config_model_schema(settings_data)
            )
        else:
            openapi_schema["components"]["schemas"][
                settings_data.__class__.__name__
            ] = settings_data.model_json_schema(
                ref_template=f"#/components/schemas/{settings_data.__class__.__name__}/$defs/"
                + "{model}"
            )

        if hasattr(settings_data, "databases"):
            inject_registry_models_to_openapi(
                settings_data,
                openapi_schema,
                "databases",
                DATABASE_CONFIG_MODELS,
                lambda m: m,
            )

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = openapi_with_config_schema


def _inject_config_schemas(
    config_model_name: str,
    schema: dict,
    registry: Mapping,
    model_getter_func: Callable[[Any], BaseModel],
):
    model_defs_dict = {}
    for value in registry.values():
        model = model_getter_func(value)
        model_schema = model.model_json_schema(
            ref_template=f"#/components/schemas/{config_model_name}/$defs/" + "{model}"
        )
        if sub_defs := model_schema.pop("$defs", None):
            for sub_name, sub_schema in sub_defs.items():
                model_defs_dict[sub_name] = sub_schema
        model_defs_dict[model.__name__] = model_schema
    schema.update(model_defs_dict)


def _inject_conf_property_refs(
    config_model_name: str,
    properties_schema: dict,
    registry: Mapping,
    model_getter_func: Callable[[Any], BaseModel],
):
    model_ref_list = [
        {
            "$ref": f"#/components/schemas/{config_model_name}/"
            + f"$defs/{model_getter_func(value).__name__}"
        }
        for value in registry.values()
    ]
    properties_schema["additionalProperties"] = {
        "anyOf": [{"type": "object"}] + model_ref_list
    }


def inject_registry_models_to_openapi(
    settings_data: BaseModel,
    openapi_schema,
    config_field: str,
    registry: Mapping,
    model_getter_func: Callable[[Any], BaseModel],
):
    if components := openapi_schema.get("components"):
        if schemas := components.get("schemas"):
            config_model_name = settings_data.__class__.__name__
            if config_schema := schemas.get(config_model_name):
                if defs := config_schema.get("$defs"):
                    _inject_config_schemas(
                        config_model_name, defs, registry, model_getter_func
                    )

            if properties := config_schema.get("properties"):
                if config_prop := properties.get(config_field):
                    _inject_conf_property_refs(
                        config_model_name, config_prop, registry, model_getter_func
                    )
