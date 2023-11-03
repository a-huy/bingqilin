from bingqilin.contexts import ContextField, LifespanContext
from tests.common import BaseTestCase


class TestLifespanContexts(BaseTestCase):
    def test_simple_context(self, test_settings_manager):
        class TestObject:
            def __init__(self, config):
                self.config = config

        class Context(LifespanContext):
            test_field: TestObject = ContextField("test")

        ctx = Context(test_settings_manager).configure()
        self.assertIsInstance(ctx.test_field, TestObject)
