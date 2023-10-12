import json
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler

from bingqilin.logger import bq_logger


logger = bq_logger.getChild("handlers")


async def log_validation_exception(request: Request, exc: RequestValidationError):
    logger.error(
        "Validation error: BODY: %s, ERRORS: %s", json.dumps(exc.body), exc.errors()
    )
    return await request_validation_exception_handler(request, exc)


def add_log_validation_exception_handler(app: FastAPI):
    app.exception_handler(RequestValidationError)(log_validation_exception)
