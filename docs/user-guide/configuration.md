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

app = settings.data.fastapi.create_app()
```

## SettingsManager

The `SettingsManager` object is a thin wrapper around your settings model instance that will automatically register a reconfigure handler and update the references to it from other parts of your app if your config changes after a live reload.

!!! info "Why not just initialize an instance of the settings on the module level?"
    You can do this if you know that the settings instance will not change after the initial import/load. Otherwise, all other modules that reference the settings instance would have to reimport it (thereby adding an import statement in the middle of your code) to get the updated values.

The `load()` function for `SettingsManager` will take whatever keyword arguments are passed into it and use it to initialize the settings model instance:

```py hl_lines="7"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings().load(_env_file=".env", _env_nested_delimiter="__")

app = settings.data.fastapi.create_app()
```

If you'd like to disable the registration of a reconfigure handler for your settings, you can pass `allow_reconfigure=False` into `load()`.

## ConfigModel

Underneath the hood, Bingqilin's `ConfigModel` is extending a Pydantic settings' `BaseSettings` object, so working with it should be familiar. However, there are several primary differences:

* `ConfigModel` overrides `settings_customise_sources()` to add a `YamlSettingsSource` and an `IniSettingsSource` as the lowest precedences sources.
* It has a `fastapi` field you can use to configure initialization behavior when creating your FastAPI app.
* It has a `databases` field you can use to define your database connection config. Values for the config mapping must be derived from the `DBConfig` class.
* There are boolean fields defined that toggle the various Bingqilin utilities.

!!! warning
    `YamlSettingsSource` is deprecated in lieu of `pydantic_settings`'s `YamlConfigSettingsSource`, introduced in 2.2.0. It will be removed in a later version.

!!! warning
    The YAML settings source depends on the `pyyaml` package to load its files. If you attempt to specify a YAML file via the `files` keyword argument without it installed, a `MissingDependencyError` will be raised to inform you about the missing package.

If your settings model does derive from `ConfigModel`, the `fastapi` model value (as an instance of `bingqilin.conf.models:FastAPIConfig`) provides a convenience function to create your app instance:

```py hl_lines="9"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel

class AppSettings(SettingsManager):
    data: ConfigModel

settings = AppSettings().load(_env_file=".env", _env_nested_delimiter="__")

app = settings.data.fastapi.create_app()
```
