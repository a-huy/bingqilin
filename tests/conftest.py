import os
import tempfile
from typing import Literal

import pytest
from pydantic_settings.sources import YamlConfigSettingsSource

from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel, ConfigModelConfigDict
from bingqilin.db.models import DBConfig
from tests.common import SimpleKeyValueClient


@pytest.fixture
def test_db_config_model():
    class TestDBConfig(DBConfig):
        type: Literal["test"]
        host: str = "127.0.0.1"
        port: int = 12345

        @classmethod
        def initialize_client(cls, config):
            return SimpleKeyValueClient(**config)

    return TestDBConfig


@pytest.fixture
def with_databases_config_in_env():
    key = "BINGQILIN_TEST_DATABASES"
    os.environ[key] = '{"test_db": {"type": "test"}}'
    yield
    del os.environ[key]


@pytest.fixture
def test_settings_manager():
    class TestSettings(SettingsManager):
        data: ConfigModel

    return TestSettings().load()


@pytest.fixture
def yaml_config_file():
    yaml_config = """
test_field: test_value
fastapi:
    title: test yaml config file
    openapi_version: 4.0.0
    """
    tfile = tempfile.NamedTemporaryFile()
    tfile.write(yaml_config.encode())
    tfile.flush()
    return tfile


@pytest.fixture
def env_config_file():
    env_config = """
TEST_FIELD=test_value
FASTAPI__TITLE="test env config file"
FASTAPI__OPENAPI_VERSION="4.1.0"
"""
    tfile = tempfile.NamedTemporaryFile()
    tfile.write(env_config.encode())
    tfile.flush()
    return tfile


@pytest.fixture
def settings_manager_with_yaml_file(yaml_config_file):
    class TestConfig(ConfigModel):
        model_config = ConfigModelConfigDict(
            extra="allow", yaml_file=yaml_config_file.name
        )

        @classmethod
        def add_settings_sources(cls, settings_cls):
            return (YamlConfigSettingsSource(settings_cls),)

    class TestSettings(SettingsManager):
        data: TestConfig

    return TestSettings().load()


@pytest.fixture
def settings_manager_with_env_file(env_config_file):
    class TestConfig(ConfigModel):
        model_config = ConfigModelConfigDict(
            extra="allow", env_file=env_config_file.name, env_nested_delimiter="__"
        )

    class TestSettings(SettingsManager):
        data: TestConfig

    return TestSettings().load()
