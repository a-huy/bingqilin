import json
from contextlib import asynccontextmanager
from typing import Callable, Optional

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from bingqilin.conf.models import ConfigModel, DEFAULT_RECONFIGURE_URL
from bingqilin.conf.openapi import add_config_model_to_openapi
from bingqilin.contexts import LifespanContext
from bingqilin.handlers import add_log_validation_exception_handler
from bingqilin.logger import bq_logger
from bingqilin.signal import RECONFIGURE_SIGNAL, dispatcher

logger = bq_logger.getChild("handlers")


def contexts_lifespan(
    *contexts: LifespanContext,
    settings_data: Optional[BaseModel] = None,
    **all_ctx_kwargs,
) -> Callable:
    """Convenience lifespan function to setup and teardown context objects.

    Args:
        settings_data (Optional[BaseModel], optional): The settings instance passed in
        at configure time. Defaults to None.

    Returns:
        _type_: Lifespan function to use when initializing your FastAPI app
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        for ctx in contexts:
            ctx_field_kwargs = {}
            if ctx.name:
                ctx_field_kwargs = all_ctx_kwargs.get(ctx.name) or {}
            ctx.configure(settings_data, **ctx_field_kwargs)

        yield

        for ctx in contexts:
            ctx.terminate()

    return lifespan


async def log_validation_exception(request: Request, exc: RequestValidationError):
    logger.error(
        "Validation error: BODY: %s, ERRORS: %s", json.dumps(exc.body), exc.errors()
    )
    return await request_validation_exception_handler(request, exc)


async def reconfigure_handler() -> dict:
    dispatcher.dispatch_handlers(RECONFIGURE_SIGNAL)
    return {}


def add_reconfigure_handler(path: str, app: FastAPI):
    app.router.post(path)(reconfigure_handler)


def setup_utils(
    app: FastAPI,
    settings_data: Optional[ConfigModel],
    log_validation_errors: bool = True,
    allow_reconfigure: bool = True,
    reconfigure_url: str = DEFAULT_RECONFIGURE_URL,
):
    """
    Initializes all the default utilities of bingqilin.
    You can opt to manually initialize whatever features you'd like,
    but most of them are built on top of a validated settings model.

    Allow some overrides via kwargs.
    """
    if log_validation_errors or (settings_data and settings_data.log_validation_errors):
        add_log_validation_exception_handler(app)

    if (allow_reconfigure or (settings_data and settings_data.allow_reconfigure)) and (
        _reconfigure_url := (
            reconfigure_url or (settings_data and settings_data.reconfigure_url)
        )
    ):
        add_reconfigure_handler(_reconfigure_url, app)

    # This feature is exclusive to ConfigModels
    if settings_data and settings_data.add_config_model_schema:
        add_config_model_to_openapi(
            settings_data, app, settings_data.flatten_config_schema
        )
