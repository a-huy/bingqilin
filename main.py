from bingqilin import setup_utils
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.contexts import ContextManager, initializer
from bingqilin.db.models import RedisDBConfig


class AppSettings(SettingsManager):
    data: ConfigModel


settings = AppSettings()


class Context(ContextManager):
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
