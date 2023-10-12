<p align="center">
    <em>A collection of utilities that serve as syntactic ice cream for your FastAPI app</em>
</p>

<img src="https://badge.fury.io/py/bingqilin.svg" alt="Package version"> <img src="https://img.shields.io/pypi/pyversions/bingqilin.svg"> <img src="https://img.shields.io/github/license/a-huy/bingqilin.svg">

---

Documentation: TBD

Source Code: [https://github.com/a-huy/bingqilin](https://github.com/a-huy/bingqilin)

---

## Features

This package contains some utilities for common actions and resources for your FastAPI app:

* **Config Loading and Validation** - Bingqilin provides a config loading system that enables the following:
    * Allow loading config from a dotenv file (`.env`) or via yaml (`config.yml` in the project directory)
    * Specify a `pydantic.BaseModel` to validate against loaded configuration
    * Add the specified config model to the OpenAPI spec and the Swagger UI docs (`/docs`)

* **Database Client Initialization** - Allow initializing connection clients and pools from database config. 
    This will provide a way to grab a client handle via `bingqilin.db:get_db_client()`.

* **Validation Error Logging** - Add an exception handler for `RequestValidationError` that emits a log. 
    Useful for troubleshooting routes that support a lot of different types of requests, such as 
    third-party callback handlers.

## Requirements

This package is intended for use with any recent version of FastAPI that supports `pydantic>=2.0` and Python 3.10+.

## Installation

    pip install bingqilin

## License
This project is licensed under the terms of the MIT license.
