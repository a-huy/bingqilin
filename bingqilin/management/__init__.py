from .base import BaseCommand, CommandError
from .utility import ManagementUtility


__all__ = ["BaseCommand", "CommandError", "execute_from_command_line"]


def execute_from_command_line():
    mgmt = ManagementUtility()
    mgmt.execute()
