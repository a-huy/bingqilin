---
title: Setup
---
Bingqilin exposes a `setup_utils()` function that takes a `ConfigModel` settings instance and your FastAPI app instance to add any configured features.

```py
from bingqilin import setup_utils

from .settings import settings

app = FastAPI()
setup_utils(app, settings.data)
```

You can pass in keyword arguments that override the values from your settings data, or you can forgo the `setup_utils()` function call completely and enable whatever utilities you'd like.

`setup_utils()` does the following things:

* Adds an exception handler to log validation errors
* Adds the route operation to handle reconfigures
* Adds the `ConfigModel` instance to the OpenAPI spec

In the example above, `settings` is an instance of `bingqilin.conf:SettingsManager`, which you can learn more about [here](configuration.md).