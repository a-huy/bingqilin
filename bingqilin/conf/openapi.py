from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from bingqilin.conf import CONFIG, ConfigModel
from bingqilin.logger import bq_logger


logger = bq_logger.getChild("conf.routes")


def add_config_model_to_openapi(fastapi_app: FastAPI):
    if not (CONFIG.is_loaded):
        logger.warning(
            "Attempting to modify the app's OpenAPI with the config model before CONFIG is loaded."
        )
        return

    config_model = CONFIG.model or ConfigModel

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
        openapi_schema["components"]["schemas"][
            config_model.__name__
        ] = config_model.model_json_schema()
        fastapi_app.openapi_schema = openapi_schema
        return fastapi_app.openapi_schema

    fastapi_app.openapi = openapi_with_config_schema
