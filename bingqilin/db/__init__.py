from typing import Optional, Any

from bingqilin.db.models import DBConfig, DATABASE_CONFIG_MODELS
from bingqilin.logger import bq_logger


logger = bq_logger.getChild("db")


DATABASE_CLIENTS = {}
DEFAULT_CLIENT_NAME = "default"


def initialize_databases(db_config=None):
    if not db_config:
        from bingqilin.conf import config

        db_config = config.data.databases

    if not db_config:
        logger.debug("No databases config found.")
        return

    for client_name, db_conf in db_config.items():
        if not isinstance(db_conf, DBConfig):
            logger.warning(
                'DB config with type "%s" not recognized. '
                "You must create a model subclass of DBConfig for that type "
                "or initialize this database manually. Config: %s",
                db_conf.get("type") or "unknown",
                db_conf,
            )
            continue
        db_client = db_conf.initialize_client()
        register_db_client(client_name, db_client)


def validate_databases(databases):
    for name, db_conf in databases.items():
        if isinstance(db_conf, dict):
            if adapter_type := db_conf.get("type"):
                if adapter_type in DATABASE_CONFIG_MODELS:
                    conf_model = DATABASE_CONFIG_MODELS[adapter_type](**db_conf)
                    databases[name] = conf_model

    return databases


def _inject_db_conf_schemas(schema, config):
    config_defs_dict = {}
    for model in DATABASE_CONFIG_MODELS.values():
        model_schema = model.model_json_schema(
            ref_template=f"#/components/schemas/{config.model.__name__}/$defs/"
            + "{model}"
        )
        if sub_defs := model_schema.pop("$defs", None):
            for sub_name, sub_schema in sub_defs.items():
                config_defs_dict[sub_name] = sub_schema
        config_defs_dict[model.__name__] = model_schema
    schema.update(config_defs_dict)


def _inject_dbs_property_refs(schema, config):
    model_ref_list = [
        {"$ref": f"#/components/schemas/{config.model.__name__}/$defs/{m.__name__}"}
        for m in DATABASE_CONFIG_MODELS.values()
    ]
    schema["additionalProperties"] = {"anyOf": [{"type": "object"}] + model_ref_list}


def inject_database_config_models_openapi(openapi_schema, config):
    assert config.is_loaded
    if components := openapi_schema.get("components"):
        if schemas := components.get("schemas"):
            if config_schema := schemas.get(config.model.__name__):
                if defs := config_schema.get("$defs"):
                    _inject_db_conf_schemas(defs, config)

                if properties := config_schema.get("properties"):
                    if databases_prop := properties.get("databases"):
                        _inject_dbs_property_refs(databases_prop, config)


def register_db_client(client_name, db_client):
    if client_name in DATABASE_CLIENTS:
        raise ValueError(
            "A database client with the name %s already exists: %s",
            client_name,
            DATABASE_CLIENTS[client_name],
        )
    DATABASE_CLIENTS[client_name] = db_client


def get_db_client(name: Optional[str] = None) -> Any:
    if len(DATABASE_CLIENTS) == 1:
        return list(DATABASE_CLIENTS.values())[0]
    if not name:
        name = DEFAULT_CLIENT_NAME
    if name not in DATABASE_CLIENTS:
        raise ValueError(f'Database client with name "{name}", not found.')
    return DATABASE_CLIENTS[name]
