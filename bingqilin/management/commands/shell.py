import logging
import os
import select
import sys
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional

import rich
import typer
from rich.padding import Padding
from rich.panel import Panel
from typer import Option
from typing_extensions import Annotated

from bingqilin.management import BaseCommand, get_resource_file_for_module
from bingqilin.management.utils import log_panel

logger = logging.getLogger(__name__)


class Shell(str, Enum):
    ipython = "ipython"
    bpython = "bpython"
    python = "python"


class Command(BaseCommand):
    def validate_init_scripts(self, init_scripts) -> List[str]:
        validated = []
        if not init_scripts:
            init_scripts = [
                "{}{}init_shell.py".format(
                    get_resource_file_for_module("bingqilin.management"),
                    os.path.sep,
                )
            ]

        for _script in init_scripts:
            if not os.path.isfile(_script):
                continue
            validated.append(_script)

        return validated

    def print_init_scripts(self, init_scripts):
        if not init_scripts:
            return

        title = "[b green]Found init scripts[/b green]"
        panel = Padding(
            Panel(
                "\n".join([f"🐍 {fname}" for fname in init_scripts]),
                title=title,
                expand=False,
                padding=(1, 2),
            ),
            1,
        )
        rich.print(panel)

    def exec_init_scripts(self, init_scripts) -> Dict[str, Any]:
        # Set up a dictionary to serve as the environment for the shell.
        imported_objects = {}

        for _script in init_scripts:
            if not _script:
                continue
            if not os.path.isfile(_script):
                continue
            with open(_script) as handle:
                pythonrc_code = handle.read()
            # Match the behavior of the cpython shell where an error in
            # PYTHONSTARTUP prints an exception and continues.
            try:
                exec(compile(pythonrc_code, _script, "exec"), imported_objects)
            except Exception:
                traceback.print_exc()

        return imported_objects

    def ipython(self, **options):
        from IPython.terminal.ipapp import TerminalIPythonApp

        app = TerminalIPythonApp()
        app.initialize([])
        if init_scripts := options.get("init_scripts"):
            for fname in init_scripts:
                app._exec_file(fname)
        app.start()

    def bpython(self, **options):
        import bpython

        init_scripts = [
            os.environ.get("PYTHONSTARTUP"),
            os.path.expanduser("~/.pythonrc.py"),
        ] + (options.get("init_scripts") or [])
        imported_objects = self.exec_init_scripts(init_scripts)

        bpython.embed(locals_=imported_objects)

    def python(self, **options):
        import code

        init_scripts = [
            os.environ.get("PYTHONSTARTUP"),
            os.path.expanduser("~/.pythonrc.py"),
        ] + (options.get("init_scripts") or [])
        imported_objects = self.exec_init_scripts(init_scripts)

        # By default, this will set up readline to do tab completion and to read and
        # write history to the .python_history file, but this can be overridden by
        # $PYTHONSTARTUP or ~/.pythonrc.py.
        try:
            hook = sys.__interactivehook__
        except AttributeError:
            # Match the behavior of the cpython shell where a missing
            # sys.__interactivehook__ is ignored.
            pass
        else:
            try:
                hook()
            except Exception:
                # Match the behavior of the cpython shell where an error in
                # sys.__interactivehook__ prints a warning and the exception
                # and continues.
                print("Failed calling sys.__interactivehook__")
                traceback.print_exc()

        # Set up tab completion for objects imported by $PYTHONSTARTUP or
        # ~/.pythonrc.py.
        try:
            import readline
            import rlcompleter

            readline.set_completer(rlcompleter.Completer(imported_objects).complete)
        except ImportError:
            pass

        # Start the interactive interpreter.
        code.interact(local=imported_objects)

    def handle(
        self,
        startup: Annotated[
            bool,
            Option(
                help="Tell the shell to run PYTHONSTARTUP and ~/.pythonrc.py scripts. "
                "Only affects the plain Python interpreter."
            ),
        ] = True,
        init: Annotated[
            Optional[List[str]],
            typer.Option(
                help="Specify one or more scripts (specified as file paths) to load "
                "before starting the shell."
            ),
        ] = None,
        interface: Annotated[
            Optional[Shell],
            Option(help="Specify an interactive interpreter interface."),
        ] = None,
    ):
        """
        Command that runs a Python interactive interpreter.
        Tries to use IPython or bpython, if one of them is available.
        Any standard input is executed as code.

        This command is adapted from django's "manage.py shell" command.
        """
        # Execute stdin if it has anything to read and exit.
        # Not supported on Windows due to select.select() limitations.
        if (
            sys.platform != "win32"
            and not sys.stdin.isatty()
            and select.select([sys.stdin], [], [], 0)[0]
        ):
            exec(sys.stdin.read(), globals())
            return

        available_shells = [interface] if interface else list(Shell)

        if startup:
            init_scripts = self.validate_init_scripts(init)
            self.print_init_scripts(init_scripts)
        else:
            init_scripts = []

        for shell in available_shells:
            try:
                return getattr(self, shell)(startup=startup, init_scripts=init_scripts)
            except ImportError:
                pass

        log_panel(
            'Couldn\'t import the "{}" interface.'.format(shell.value), level="error"
        )
        raise typer.Exit(code=1)
