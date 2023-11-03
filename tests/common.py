from typing import Optional


class BaseTestCase:
    def assertEqual(self, val_a, val_b, message: Optional[str] = None):
        assert val_a == val_b, message or f"{val_a} is not equal to {val_b}"

    def assertNone(self, value, message: Optional[str] = None):
        assert value is None, message or f"{value} is not None"

    def assertNotNone(self, value, message: Optional[str] = None):
        assert value is not None, message or f"{value} is None"

    def assertIsInstance(self, value, types, message: Optional[str] = None):
        assert isinstance(value, types), (
            message or f"{value} is not one of the following types: ({types})"
        )

    def assertIsSubclass(self, value, types, message: Optional[str] = None):
        assert issubclass(value, types), (
            message or f"{value} is not a subclass of all of the following: ({types})"
        )


class SimpleKeyValueClient:
    host: str
    port: int

    def __init__(self) -> None:
        self._db = {}

    def set(self, key, value):
        self._db[key] = value

    def get(self, key):
        return self._db.get(key, None)
