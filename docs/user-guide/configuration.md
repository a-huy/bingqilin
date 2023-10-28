---
title: Configuration
---

Creating a settings instance in Bingqilin is a little different:

```py
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings().load(_env_file=".env", _env_nested_delimiter="__")
settings.load(_env_file=".env", _env_nested_delimiter="__")

app = settings.data.fastapi.create_app()
```

## SettingsManager

The `SettingsManager` object is a thin wrapper around your settings model instance that will automatically register a reconfigure handler while preserving references to it from other parts of your app.

## ConfigModel

Underneath the hood, Bingqilin's `ConfigModel` is extending a Pydantic settings' `BaseSettings` object, so working with it should be familiar. However, there are several primary differences:

* `ConfigModel` overrides `settings_customise_sources()` to add a `YamlSettingsSource` and an `IniSettingsSource` as the lowest precedences sources.
* It has a `fastapi` field you can use to configure initialization behavior when creating your FastAPI app.
* It has a `databases` field you can use to define your database connection config. Values for the config mapping must be derived from the `DBConfig` class.

!!! warning
    The YAML settings source depends on the `pyyaml` package to load its files. If you attempt to specify a YAML file via the `files` keyword argument without it installed, a `MissingDependencyError` will be raised to inform you about the missing package.

