import json

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError

from bingqilin.logger import bq_logger

logger = bq_logger.getChild("handlers")


async def log_validation_exception(request: Request, exc: RequestValidationError):
    _body = exc.body
    try:
        _body = json.dumps(exc.body)
    except TypeError:
        logger.warning(
            "Could not dump request body for validation error: %s", type(_body)
        )
    logger.error("Validation error: BODY: %s, ERRORS: %s", _body, exc.errors())
    return await request_validation_exception_handler(request, exc)


def add_log_validation_exception_handler(app: FastAPI):
    app.exception_handler(RequestValidationError)(log_validation_exception)
