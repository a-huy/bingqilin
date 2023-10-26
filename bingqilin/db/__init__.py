from typing import Any, Optional

from pydantic import BaseModel

from bingqilin.db.models import DATABASE_CONFIG_MODELS, DBConfig
from bingqilin.logger import bq_logger

logger = bq_logger.getChild("db")


DATABASE_CLIENTS = {}
DEFAULT_CLIENT_NAME = "default"


def initialize_databases(db_config):
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
    _db_config = databases
    if isinstance(_db_config, BaseModel):
        _db_config = {
            _n: getattr(_db_config, _n) for _n in _db_config.model_fields.keys()
        }
    for name, db_conf in _db_config.items():
        if isinstance(db_conf, dict):
            if adapter_type := db_conf.get("type"):
                if adapter_type in DATABASE_CONFIG_MODELS:
                    conf_model = DATABASE_CONFIG_MODELS[adapter_type](**db_conf)
                    databases[name] = conf_model

    return databases


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
