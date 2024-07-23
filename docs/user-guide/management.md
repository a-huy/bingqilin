---
title: Management commands and scripts
---

Bingqilin provides a basic commands framework to run one-off scripts or do any offline work that includes your app and settings contexts.

## Setup

The base `ConfigModel` class has the following fields for management:

* `management_settings`: This is a string that represents a Python path to the module where you have a `SettingsManager` instantiated (e.g. `main:settings`)
* `management_additional_commands`: This is a list of strings that represent Python paths to additional modules containing user-defined commands. Module paths specified here will allow for command discovery and usage.

None of the management settings are required. However, many of the Bingqilin core commands (and most likely some of your own) will depend on a custom app-specific settings manager to have access to additional config values.

## Adding new commands

### Create a new commands module and add make it discoverable

For example, let's assume that you're adding a simple command that dumps the contents of your app settings under a `scripts/` module called `dump_settings.py`:

```
📦 project_root
│   📜 __init__.py
│   📜 app.py
│   📜 contexts.py
└── 📂 scripts
    │    📜 __init__.py
    │    📜 dump_settings.py
```

Then, you register the scripts module in your settings under `management_additional_commands` with a group name:

```bash title=".env"
MANAGEMENT_SETTINGS="contexts:settings"
MANAGEMENT_ADDITIONAL_COMMANDS='[["scripts", "scripts"]]'
```

Specifying a group name is optional, as it will default to `app`.

### Create the dump_settings command

At their core, Bingqilin commands are just a thin wrapper around [typer](https://typer.tiangolo.com/) commands. However, there are a few rules for creating a Bingqilin command:

1. Each command must have a class named `Command` that inherits from `BaseCommand` (this is a design choice taken from [django](https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/))
2. The `Command` class must implement a method called `handle()`. This is normally the command function that you would implement with typer, so all the args and kwargs annotations will work here.

Here's an implementation for our example command:

```py title="dump_settings.py"
from rich import print_json
from typer import Option
from typing import Optional
from typing_extensions import Annotated
from bingqilin.management import BaseCommand
from contexts import settings

class Command(BaseCommand):
    # Name will normally be set to the name of the command file.
    # Set this attribute to override it.
    name: Optional[str] = "dump_settings"
    # Displays a help message when the `--help` option is specified.
    help: Optional[str] = "Print the current values of your settings "
                          "to the console."
    # Adds a short text to the end of your help message of your command.
    epilog: Optional[str] = "This is an example command!"
    short_help: Optional[str] = "Dump current settings"
    # Prevents this command from being publicized when the `--help` option 
    # is used and available commands are listed.
    hidden: bool = False
    # Marks the command as deprecated.
    deprecated: bool = False
    # You can specify a custom section that this command will be displayed
    # under when available commands are listed.
    rich_help_panel: Optional[str] = None
    # Requires the app to set non-empty and valid `management_settings` Python 
    # path in order to invoke this command. This means that the command depends
    # on an app-specific settings manager to be defined.
    require_app_config = True

    def handle(
        self, 
        pretty: Annotated[
            bool,
            Option(
                help="Pretty print the config values JSON object. "
                     "Defaults to True."
            ),
        ] = True
    ):
        settings_json = settings.data.model_dump_json()
        print_func = print_json if pretty else print
        print_func(settings_json)
```

### Invoke the new command

Now, you can discover the new command by running the `bingqilin` command:

```output
bingqilin --help
                                                                                
 Usage: bingqilin [OPTIONS] COMMAND [ARGS]...                                   
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --loglevel                  TEXT  [default: None]                            │
│ --install-completion              Install completion for the current shell.  │
│ --show-completion                 Show completion for the current shell, to  │
│                                   copy it or customize the installation.     │
│ --help                            Show this message and exit.                │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ core                                                                         │
│ scripts                                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

And running the `scripts` subcommand with the `--help` option will give:

```output
bingqilin scripts --help
                                                                                
 Usage: bingqilin scripts [OPTIONS] COMMAND [ARGS]...                           
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ dump_settings   Dump current settings                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

Finally, we run the newly written command:

```json
bingqilin scripts dump_settings
{
  "debug": true,
  "loglevel": 20,
  ...
  "fastapi": {
    "title": "FastAPI",
    "summary": null,
    "description": "",
    "version": "0.1.0",
    ...
  }
}
```
