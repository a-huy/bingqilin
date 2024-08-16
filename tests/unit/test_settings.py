from fastapi import FastAPI
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic_settings.sources import (
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
)

from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel, ConfigModelConfigDict
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

    def test_config_with_yaml_file(self, yaml_config_file):
        class TestConfig(ConfigModel):
            model_config = ConfigModelConfigDict(
                extra="allow", yaml_file=yaml_config_file.name
            )

            @classmethod
            def add_settings_sources(
                cls, settings_cls: type[BaseSettings]
            ) -> tuple[PydanticBaseSettingsSource, ...]:
                return (YamlConfigSettingsSource(settings_cls),)

        class TestSettings(SettingsManager):
            data: TestConfig

        settings = TestSettings().load()
        self.assertEqual(settings.data.fastapi.title, "test yaml config file")

    def test_config_with_env_file(self, env_config_file):
        class TestConfig(ConfigModel):
            model_config = ConfigModelConfigDict(
                extra="allow", env_file=env_config_file.name, env_nested_delimiter="__"
            )

        class TestSettings(SettingsManager):
            data: TestConfig

        settings = TestSettings().load()
        self.assertEqual(settings.data.fastapi.title, "test env config file")

    def test_create_app(self):
        class TestSettings(SettingsManager):
            data: ConfigModel

        settings = TestSettings().load()
        app = settings.data.fastapi.create_app()
        self.assertIsInstance(app, FastAPI)
        self.assertEqual(app.openapi_version, "3.1.0")

    def test_override_openapi_version(
        self, settings_manager_with_yaml_file, settings_manager_with_env_file
    ):
        yaml_app = settings_manager_with_yaml_file.data.fastapi.create_app()
        self.assertEqual(yaml_app.openapi_version, "4.0.0")

        env_app = settings_manager_with_env_file.data.fastapi.create_app()
        self.assertEqual(env_app.openapi_version, "4.1.0")
