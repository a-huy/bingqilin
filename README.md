# Bingqilin
<p align="center">
    <em>A collection of utilities that serve as syntactic ice cream for your FastAPI app</em>
</p>
<p align="center">
<img src="https://img.shields.io/github/last-commit/a-huy/bingqilin.svg">
<a href="https://pypi.org/project/bingqilin" target="_blank">
    <img src="https://badge.fury.io/py/bingqilin.svg" alt="Package version">
</a>
<img src="https://img.shields.io/pypi/pyversions/bingqilin.svg">
<img src="https://img.shields.io/github/license/a-huy/bingqilin.svg">
</p>

---

Documentation: TBD

Source Code: [https://github.com/a-huy/bingqilin](https://github.com/a-huy/bingqilin)

---

## Features

This package contains some utilities for common actions and resources for your FastAPI app:

* **Extended Settings Loading** - Bingqilin provides a config loading system that is an extension on top of pydantic's `BaseSettings`:
    * Add settings sources to enable loading from `.yaml` files or `.ini` files
    * Allow the option to add the settings model to the OpenAPI docs (`/docs`)
    * Provide a handle to the loaded config instance via `bingqilin.conf:config`

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
