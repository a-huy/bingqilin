import logging
import sys
from typing import Optional

import typer
from typer.core import TyperGroup

from .context import ManagementCommandConfig, ManagementContextObj
from .utils import log_panel


logger = logging.getLogger(__name__)


def get_command_class_from_handler(handler_method):
    vals = vars(sys.modules[handler_method.__module__])
    command_class = vals[handler_method.__qualname__.split(".")[0]]
    return command_class


def default_callback(ctx: typer.Context, loglevel: Optional[str] = None):
    ctx_obj: ManagementContextObj = ctx.obj
    if loglevel is not None:
        ctx_obj.loglevel = logging.getLevelName(loglevel)
    elif ctx_obj.config:
        ctx_obj.loglevel = ctx_obj.config.loglevel


def commands_group_callback(ctx: typer.Context):
    # Perform checks against config on the Command class object
    ctx_obj: ManagementContextObj = ctx.obj
    if not ctx.invoked_subcommand:
        return

    command_config = ctx_obj.command_config.get(ctx.invoked_subcommand)
    if not command_config:
        return

    if command_config.require_app_config and not ctx_obj.config:
        log_panel(
            f'The command "{ctx.invoked_subcommand}" requires an application settings instance '
            "to be specified, but one could not be loaded. Define one (using a Python path) "
            f'with either the "{ctx_obj.settings_manager_env_name}" environment variable or the '
            '"ConfigModel.management_settings" field.',
            level="error",
        )
        raise typer.Exit(code=1)

    if isinstance(ctx.command, TyperGroup):
        cmd_cb = ctx.command.commands[ctx.invoked_subcommand].callback
        cmd_class: BaseCommand = get_command_class_from_handler(cmd_cb)
        cmd_class.initialize(ctx)


def commands_group_result_callback(result):
    pass


class BaseCommand:
    # Typer command options.
    # See: https://typer.tiangolo.com/tutorial/commands/
    name: Optional[str] = None
    help: Optional[str] = None
    epilog: Optional[str] = None
    short_help: Optional[str] = None
    hidden: bool = False
    deprecated: bool = False
    rich_help_panel: Optional[str] = None

    # Bingqilin command options
    require_app_config = True

    def get_typer_command_kwargs(self):
        kwargs = {}
        if self.help:
            kwargs["help"] = self.help
        if self.epilog:
            kwargs["epilog"] = self.epilog
        if self.short_help:
            kwargs["short_help"] = self.short_help
        kwargs["hidden"] = self.hidden
        kwargs["deprecated"] = self.deprecated
        if self.rich_help_panel:
            kwargs["rich_help_panel"] = self.rich_help_panel
        return kwargs

    def get_management_config(self):
        return ManagementCommandConfig(require_app_config=self.require_app_config)

    # Optional methods
    #
    @classmethod
    def initialize(cls, ctx: typer.Context):
        pass

    # Methods that require overrides
    #
    def handle(self, ctx: typer.Context):
        raise NotImplementedError()
