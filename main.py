from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic_settings.sources import PydanticBaseSettingsSource

from bingqilin import setup_utils
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import LifespanContext, initializer
from bingqilin.db.models import RedisDBConfig
from bingqilin.extras.aws.conf.sources import (
    AWSSecretsManagerSource,
    AWSSystemsManagerParamsSource,
)
from bingqilin.extras.aws.conf.types import SecretsManagerField, SSMParameterField


class TestConfig(BaseModel):
    test_ssm_field: str = SSMParameterField(
        # arn="arn:aws:ssm:us-west-2:064614371641:parameter/TEST_SSM_FIELD"
    )
    secret_field: dict = SecretsManagerField(
        secret_name="dev/test-field"
        # arn="arn:aws:secretsmanager:us-west-2:064614371641:secret:dev/test-field-awbO1z"
    )


class AppConfigModel(ConfigModel):
    # test: TestConfig

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], *args, **kwargs
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources = list(ConfigModel.settings_customise_sources(cls, *args, **kwargs))
        sources.append(AWSSystemsManagerParamsSource(settings_cls, always_fetch=False))
        sources.append(AWSSecretsManagerSource(settings_cls))
        return tuple(sources)


class AppSettings(SettingsManager):
    data: AppConfigModel


settings = AppSettings()


class Context(LifespanContext):
    test: int

    @initializer("redis")
    @classmethod
    def initialize_redis(cls, db_config: RedisDBConfig):
        return db_config.initialize_client()


settings.load(_env_file=".env", _env_nested_delimiter="__")
context = Context(settings)
context.configure()

app = settings.data.fastapi.create_app()
setup_utils(app, settings.data)


@app.get("/")
async def ping():
    return {"pong": True}
