from pydantic import BaseModel

from bingqilin.utils.types import CSVLine
from tests.common import BaseTestCase


class TestCSVLine(BaseTestCase):
    def test_simple_validation(self):
        class TestModel(BaseModel):
            test_line: CSVLine

        value = "a,b,c"
        instance = TestModel(test_line=value)
        self.assertEqual(instance.test_line, ["a", "b", "c"])

    def test_spaces_validation(self):
        class TestModel(BaseModel):
            test_line: CSVLine

        value = "a, b, c     "
        instance = TestModel(test_line=value)
        self.assertEqual(instance.test_line, ["a", "b", "c"])

    def test_simple_serialization(self):
        class TestModel(BaseModel):
            test_line: CSVLine

        value = "a,b,c"
        instance = TestModel(test_line=value)
        self.assertEqual(instance.test_line, ["a", "b", "c"])
        serialized = instance.model_dump()
        self.assertEqual(serialized["test_line"], "a,b,c")
