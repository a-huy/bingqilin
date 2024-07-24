import importlib
import importlib.resources
import logging
import os
import pkgutil
from typing import Optional

import typer

from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel

from .base import (
    BaseCommand,
    commands_group_callback,
    commands_group_result_callback,
    default_callback,
)
from .context import ManagementContextObj

logger = logging.getLogger(__name__)


COMMANDS_IGNORE_PREFIX = "_"
SETTINGS_MANAGER_ENV_NAME = "BINGQILIN_SETTINGS"
CORE_COMMANDS_MODULE = "bingqilin.management.commands"
CORE_COMMANDS_GROUP_NAME = "core"


def _commands_in_directory(root_directory, current_directory):
    commands = []
    for _, name, is_pkg in pkgutil.iter_modules([current_directory]):
        if name.startswith(COMMANDS_IGNORE_PREFIX):
            continue
        if is_pkg:
            _cmds = _commands_in_directory(
                root_directory, os.path.join(current_directory, name)
            )
        else:
            python_module_path = (
                current_directory.replace(root_directory, "")
                .lstrip(os.path.sep)
                .replace(os.path.sep, ".")
            )
            _cmds = [
                "{}{}{}".format(
                    python_module_path, "." if python_module_path else "", name
                )
            ]
        commands += _cmds
    return commands


def get_resource_file_for_module(module_path: str):
    return str(importlib.resources.files(module_path))


def find_commands(commands_root_dir):
    """
    Files and directories that start with a "_" will be ignored.
    """
    if not commands_root_dir:
        return []
    return _commands_in_directory(commands_root_dir, commands_root_dir)


def get_app_settings_path():
    if env_value := os.environ.get(SETTINGS_MANAGER_ENV_NAME):
        return env_value

    from bingqilin.conf import ConfigModel, SettingsManager
    from bingqilin.conf.models import ConfigModelConfigDict

    class _T_Config(ConfigModel):
        model_config = ConfigModelConfigDict(extra="allow")

    class _T_Settings(SettingsManager):
        data: _T_Config

    _settings = _T_Settings().load(_env_file=".env")
    return _settings.data.management_settings


def get_app_settings() -> SettingsManager | None:
    settings_path = get_app_settings_path()
    if not settings_path:
        return None

    try:
        settings_module, settings_attr = settings_path.split(":")
        mod = importlib.import_module(settings_module)

        attr_vals = settings_attr.split(".")
        val = mod
        while attr_vals:
            val = getattr(val, attr_vals[0])
            attr_vals = attr_vals[1:]
    except ImportError:
        raise RuntimeError(
            f'Could not import the module "{settings_module}" while getting app settings.'
        )
    except AttributeError:
        raise RuntimeError(
            f'Could not get attribute "{attr_vals[0]}" from value "{val}" when loading app '
            "settings."
        )

    if not (val and isinstance(val, SettingsManager)):
        raise RuntimeError(
            f'The value of {settings_path} is not an instance of "SettingsManager" '
            f"(expected: SettingsManager, got: {type(val)})"
        )

    return val


def get_app_root() -> str | None:
    settings_path = get_app_settings_path()
    if not settings_path:
        return None

    settings_module, _ = settings_path.split(":")
    try:
        mod = importlib.import_module(settings_module)
    except ImportError:
        raise RuntimeError(
            f'Could not import the module "{settings_module}" while getting app settings.'
        )

    mod_file_parts = str(mod.__file__).replace(".py", "").split(os.path.sep)
    settings_module_parts = settings_module.split(".")
    root_parts = mod_file_parts[: -len(settings_module_parts)]
    return os.path.sep.join(root_parts)


class ManagementUtility:
    def __init__(self) -> None:
        self.app_config = self.get_app_config()
        self.ctx_obj = ManagementContextObj(
            config=self.app_config,
            settings_manager_env_name=SETTINGS_MANAGER_ENV_NAME,
        )
        self.typer = typer.Typer(
            context_settings={"obj": self.ctx_obj},
            callback=default_callback,
        )

    def get_app_config(self) -> Optional[ConfigModel]:
        if val := get_app_settings():
            return val.data

    def load_command(self, base_module, command_name, typer_app=None):
        cmd_mod = importlib.import_module(".".join([base_module, command_name]))
        cmd_class: BaseCommand = cmd_mod.Command()
        _typer = typer_app or self.typer

        _name = cmd_class.name or command_name
        self.ctx_obj.command_config[_name] = cmd_class.get_management_config()

        command_kwargs = cmd_class.get_typer_command_kwargs()
        _typer.command(_name, **command_kwargs)(cmd_class.handle)

    def load_command_group(self, cmd_module: str, group_name=None):
        if not group_name:
            group_name = "app"

        try:
            cmd_dir = get_resource_file_for_module(cmd_module)
        except ModuleNotFoundError:
            logger.warning(
                f'[yellow]Could not load module "{cmd_module}", skipping.[/yellow]'
            )
            return

        commands = find_commands(cmd_dir)
        if not commands:
            return

        _group_typer = typer.Typer()

        for _name in commands:
            self.load_command(cmd_module, _name, _group_typer)

        self.typer.add_typer(
            _group_typer,
            name=group_name,
            callback=commands_group_callback,
            result_callback=commands_group_result_callback,
        )

    def execute(self):
        additional_commands = (
            self.app_config.management_additional_commands if self.app_config else []
        )
        cmd_modules = [
            (CORE_COMMANDS_MODULE, CORE_COMMANDS_GROUP_NAME)
        ] + additional_commands

        existing_groups = set()
        for item in cmd_modules:
            if isinstance(item, str):
                cmd_module = item
                group_name = None
            elif isinstance(item, tuple):
                cmd_module, group_name = item
                if group_name in existing_groups:
                    logger.warning(
                        f'[yellow]Additional commands module "{cmd_module}" is specified with '
                        f'the group name "{group_name}", and will override already loaded '
                        "commands.[/yellow]",
                    )
            else:
                raise ValueError(
                    f"Got unexpected additional commands item (type: {type(item)})"
                )
            self.load_command_group(cmd_module, group_name)

        self.typer()
