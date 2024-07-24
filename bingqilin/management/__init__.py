import os
import sys

from .base import BaseCommand
from .logging import setup_logging
from .cli import ManagementUtility, get_app_settings, get_resource_file_for_module


setup_logging()


__all__ = [
    "BaseCommand",
    "execute_from_command_line",
    "get_app_settings",
    "get_resource_file_for_module",
]


def execute_from_command_line():
    if os.curdir not in sys.path:
        sys.path.append(os.curdir)
    mgmt = ManagementUtility()
    mgmt.execute()
