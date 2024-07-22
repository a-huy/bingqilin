from .base import BaseCommand, CommandError
from .logging import setup_logging
from .utility import ManagementUtility, get_app_settings, get_resource_file_for_module


setup_logging()


__all__ = [
    "BaseCommand",
    "CommandError",
    "execute_from_command_line",
    "get_app_settings",
    "get_resource_file_for_module",
]


def execute_from_command_line():
    mgmt = ManagementUtility()
    mgmt.execute()
