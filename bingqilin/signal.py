import signal
from functools import wraps
from typing import Callable, Dict, List


class DuplicateHandlerError(RuntimeError):
    pass


class SignalHandlerDispatcher:
    handlers: Dict[int, List[Callable]] = {}

    def add_handler(
        self, for_signal: int, handler: Callable, raise_on_duplicate: bool = False
    ):
        if for_signal not in self.handlers:
            self.handlers[for_signal] = []
            signal.signal(for_signal, self.dispatch_handlers)

        if handler in self.handlers[for_signal] and raise_on_duplicate:
            raise DuplicateHandlerError(
                f"Handler {handler} already present for signal {for_signal}."
            )

        self.handlers[for_signal].append(handler)

    def remove_handler(self, for_signal: int, handler: Callable):
        if handler not in (self.handlers.get(for_signal) or []):
            return

        self.handlers[for_signal].remove(handler)

    def get_handlers(self, for_signal: int) -> List[Callable]:
        return self.handlers.get(for_signal) or []

    def dispatch_handlers(self, for_signal: int, _=None):
        for handler in dispatcher.get_handlers(for_signal):
            handler()


dispatcher = SignalHandlerDispatcher()


def signal_handler(for_signal: int):
    def inner(func):
        dispatcher.add_handler(for_signal, func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return inner


RECONFIGURE_SIGNAL = signal.SIGUSR1
