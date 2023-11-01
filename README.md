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

Documentation: [https://a-huy.github.io/bingqilin/](https://a-huy.github.io/bingqilin/)
Source Code: [https://github.com/a-huy/bingqilin](https://github.com/a-huy/bingqilin)

---

## Features

This package contains some utilities for common actions and resources for your FastAPI app:

* **Extended Settings Loading** - Bingqilin provides additional pieces to enhance Pydantic's `BaseSettings`:
    * Add settings sources to enable loading from `.yaml` files or `.ini` files
    * Allow the option to add the settings model to the OpenAPI docs (`/docs`)
    * A base `ConfigModel` derived from Pydantic's `BaseSettings` that will allow configuring parts of your FastAPI app and Bingqilin's utilities via settings 
    * Provides a `SettingsManager` class to attach your settings model to allow live reconfiguring

* **Reconfigurable Contexts** - Provide constructs to declare shared connection objects (such as databases and third-party clients) that can be initialized from settings and can be enabled for live reconfiguring.

* **Validation Error Logging** - Add an exception handler for `RequestValidationError` that emits a log. 
    Useful for troubleshooting routes that support a lot of different types of requests, such as 
    third-party callback handlers.

## Requirements

This package is intended for use with any recent version of FastAPI (`>=0.95.2`).

## Installation

    pip install bingqilin

## License
This project is licensed under the terms of the MIT license.
