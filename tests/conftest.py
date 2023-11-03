import os
from typing import Literal

import pytest

from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
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
