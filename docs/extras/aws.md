---
title: AWS/Boto Utilities
---

# ARN Types

Bingqilin provides an ARN Pydantic type that you can use for validation:

```py
from pydantic import BaseModel
from bingqilin.lib.aws.types import ARN

class MyModel(BaseModel):
    some_resource: ARN

model = MyModel(
    some_resource="arn:aws:ssm:us-west-2:123456789012:parameter/some_param"
)

# some_resource=<bingqilin.extras.aws.conf.types.ARN object at 0x102d44610>
```
<br>

# Additional Settings Sources

This extras module provides two settings sources that you can use to grab values from commonly used AWS services:

!!! warning
    These settings sources require the `boto3` package.

## AWS Systems Manager Parameters Storage

To draw values from the SSM parameter store when loading your settings, you'll have to do two things:

1. Add an instance of `AWSSystemsManagerParamsSource` to your return list in `settings_customise_sources()`
2. Initialize each model field to an instance of `SSMParameterField`

```py hl_lines="7 16"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.extras.aws.conf.sources import AWSSystemsManagerParamsSource
from bingqilin.extras.aws.conf.types import SSMParameterField

class AppConfigModel(ConfigModel):
    test_ssm_field: str = SSMParameterField()

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], *args, **kwargs
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources = list(
            ConfigModel.settings_customise_sources(cls, *args, **kwargs)
        )
        sources.append(AWSSystemsManagerParamsSource(settings_cls))
        return tuple(sources)

class AppSettings(SettingsManager):
    data: AppConfigModel

settings = AppSettings()
settings.load()
```

By default, this will tell the `boto` client to use the default AWS credentials. For the parameter retrieval, it will default to using the field name in an environment variable format (UPPER_SNAKE_CASE).

!!! info "Why do I need to use an instance of `SSMParameterField` for every parameter I want to load?"
    Because retrieving a parameter from the Systems Manager requires an external HTTP call, this is done to minimize the amount of network calls made.

There are a couple changes to the behavior that you can do:

### Passing in credentials

You can specify a region, access key ID, and a secret access key as config for the settings model to initialize the settings source with those credentials:

```py
class AppConfigModel(ConfigModel):

    model_config = SettingsConfigDict(
        aws_region='us-west-1',
        aws_access_key_id='a_key_id',
        aws_secret_access_key='totally_secret_key'
    )
```

```py hl_lines="12-17"
class AppConfigModel(ConfigModel):
    test_ssm_field: str = SSMParameterField()

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], *args, **kwargs
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources = list(
            ConfigModel.settings_customise_sources(cls, *args, **kwargs)
        )
        sources.append(
            AWSSystemsManagerParamsSource(
                settings_cls, 
                region='us-west-1', 
                access_key_id='a_key_id', 
                secret_access_key='totally_secret_key'
            )
        )
        return tuple(sources)
```

### Specify an ARN for an SSM param field

```py hl_lines="3"
class AppConfigModel(ConfigModel):
    test_ssm_field: str = SSMParameterField(
        arn="arn:aws:ssm:us-west-2:123456789012:parameter/some_param"
    )
```

### Use the field name exactly as-is for parameter retrieval

```py hl_lines="3"
class AppConfigModel(ConfigModel):
    test_ssm_field: str = SSMParameterField(
        env_var_format=False
    )
```

This will use the name `test_ssm_field` when requesting the parameter instead of `TEST_SSM_FIELD`.
    

## AWS Secrets Manager

Using this settings source is almost identical to `AWSSystemsManagerParamsSource`, but using the respective settings source and field objects for the Secrets Manager:

```py hl_lines="7 16"
from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.extras.aws.conf.sources import AWSSecretsManagerSource
from bingqilin.extras.aws.conf.types import SecretsManagerField

class AppConfigModel(ConfigModel):
    test_secret_field: str = SecretsManagerField()

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], *args, **kwargs
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        sources = list(
            ConfigModel.settings_customise_sources(cls, *args, **kwargs)
        )
        sources.append(AWSSecretsManagerSource(settings_cls))
        return tuple(sources)

class AppSettings(SettingsManager):
    data: AppConfigModel

settings = AppSettings()
settings.load()
```

The same support for specifying AWS credentials and also using an ARN will work for the secrets manager settings source/field.

### Passing in a secret name

Additionally, you can specify a `secret_name` to retrieve the secret value:

```py hl_lines="3"
class AppConfigModel(ConfigModel):
    test_secret_field: str = SecretsManagerField(
        secret_name='test/a-secret-name'
    )
```
