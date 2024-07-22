import os
import select
import sys
import traceback

from enum import Enum
from typing import Optional
from typing_extensions import Annotated

from typer import Option

from bingqilin.management import BaseCommand, CommandError


class Shell(str, Enum):
    ipython = "ipython"
    bpython = "bpython"
    python = "python"


class Command(BaseCommand):
    def ipython(self, **options):
        from IPython import start_ipython

        start_ipython(argv=[])

    def bpython(self, **options):
        import bpython

        bpython.embed()

    def python(self, **options):
        import code

        # Set up a dictionary to serve as the environment for the shell.
        imported_objects = {}

        # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
        # conventions and get $PYTHONSTARTUP first then .pythonrc.py.
        if options["startup"]:
            for pythonrc in [
                os.environ.get("PYTHONSTARTUP"),
                os.path.expanduser("~/.pythonrc.py"),
            ]:
                if not pythonrc:
                    continue
                if not os.path.isfile(pythonrc):
                    continue
                with open(pythonrc) as handle:
                    pythonrc_code = handle.read()
                # Match the behavior of the cpython shell where an error in
                # PYTHONSTARTUP prints an exception and continues.
                try:
                    exec(compile(pythonrc_code, pythonrc, "exec"), imported_objects)
                except Exception:
                    traceback.print_exc()

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
                help="Tell the shell to run a PYTHONSTARTUP and ~/.pythonrc.py scripts. "
                "Only affects the plain Python interpreter."
            ),
        ] = True,
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

        for shell in available_shells:
            try:
                return getattr(self, shell)(startup=startup)
            except ImportError:
                pass
        raise CommandError("Couldn't import {} interface.".format(shell))
