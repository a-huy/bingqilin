from pydantic import BaseModel

from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from tests.common import BaseTestCase


class TestSettingsManager(BaseTestCase):
    def test_basic_config(self):
        class TestSettings(SettingsManager):
            data: ConfigModel

        settings = TestSettings().load()
        self.assertNotNone(settings.last_loaded_at)

    def test_config_with_databases(
        self, test_db_config_model, with_databases_config_in_env
    ):
        class DatabasesConfig(BaseModel):
            test_db: test_db_config_model

        class TestConfig(ConfigModel):
            databases: DatabasesConfig

        class TestSettings(SettingsManager):
            data: TestConfig

        settings = TestSettings().load(
            _env_nested_delimiter="__", _env_prefix="BINGQILIN_TEST_"
        )
        test_db_config = settings.data.databases.test_db
        self.assertEqual(test_db_config.type, "test")
        self.assertEqual(test_db_config.host, "127.0.0.1")
        self.assertEqual(test_db_config.port, 12345)
