import json
from typing import Any, Literal, Optional, Type

from botocore.exceptions import ClientError
from pydantic import ConfigDict
from pydantic.fields import FieldInfo
from pydantic_settings.main import BaseSettings

from bingqilin.conf.sources import (
    BaseSourceConfig,
    BingqilinSettingsSource,
    MissingDependencyError,
)
from bingqilin.extras.aws.conf.types import (
    AWS_FIELD_EXTRA_NAMESPACE,
    AWS_SECRETS_MANAGER_SERVICE,
    AWS_SSM_SERVICE,
)


class BaseAWSSettingsSource(BingqilinSettingsSource):
    type: Literal["aws"]
    package_deps = ["boto3"]
    AWS_SERVICE = None

    def __init__(
        self,
        settings_cls: Type[BaseSettings],
        region=None,
        access_key_id=None,
        secret_access_key=None,
    ):
        super().__init__(settings_cls)

        if not self.AWS_SERVICE:
            raise RuntimeError("An AWS service ID must be specified.")

        try:
            from boto3 import Session
        except (ModuleNotFoundError, ImportError):
            raise MissingDependencyError(self)

        self.default_region = region or settings_cls.model_config.get("aws_region")
        _access_key_id = access_key_id or settings_cls.model_config.get(
            "aws_accss_key_id"
        )
        _secret_access_key = secret_access_key or settings_cls.model_config.get(
            "aws_secret_access_key"
        )
        self.session = Session(
            region_name=region,
            aws_access_key_id=_access_key_id,
            aws_secret_access_key=_secret_access_key,
        )
        self.clients_by_region = {}
        self.clients_by_region[region] = self.session.client(
            service_name=self.AWS_SERVICE, region_name=region
        )

    def get_region_client(self, region=None):
        if not region:
            region = self.default_region
        if region not in self.clients_by_region:
            self.clients_by_region[region] = self.session.client(
                service_name=self.AWS_SERVICE, region_name=region
            )
        return self.clients_by_region[region]


class AWSSystemsManagerParamsSource(BaseAWSSettingsSource):
    type: Literal["aws_ssm"]

    AWS_SERVICE = AWS_SSM_SERVICE

    class SourceConfig(BaseSourceConfig):
        region: Optional[str]
        access_key_id: Optional[str]
        secret_access_key: Optional[str]

        model_config = ConfigDict(title="AWSSSMSourceConfig")

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        if not (
            isinstance(field.json_schema_extra, dict)
            and AWS_FIELD_EXTRA_NAMESPACE in field.json_schema_extra
        ):
            return None, field_name, False

        aws_extra = field.json_schema_extra[AWS_FIELD_EXTRA_NAMESPACE]
        if aws_extra.get("service") != self.AWS_SERVICE:
            return None, field_name, False

        if arn := aws_extra.get("arn"):
            _param_id = arn
        elif aws_extra.get("env_var_format"):
            _param_id = field_name.upper()
        else:
            _param_id = field_name

        try:
            client = self.get_region_client(aws_extra.get("region"))
            result = client.get_parameter(Name=_param_id, WithDecryption=True)
        except ClientError:
            return None, field_name, False
        else:
            value = result["Parameter"]["Value"]
            return value, field_name, False


class AWSSecretsManagerSource(BaseAWSSettingsSource):
    type: Literal["aws_secretsmanager"]

    AWS_SERVICE = AWS_SECRETS_MANAGER_SERVICE

    class SourceConfig(BaseSourceConfig):
        region: Optional[str]
        access_key_id: Optional[str]
        secret_access_key: Optional[str]

        model_config = ConfigDict(title="AWSSecretsManagerSourceConfig")

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        if not (
            isinstance(field.json_schema_extra, dict)
            and AWS_FIELD_EXTRA_NAMESPACE in field.json_schema_extra
        ):
            return None, field_name, False

        aws_extra = field.json_schema_extra[AWS_FIELD_EXTRA_NAMESPACE]
        if aws_extra.get("service") != self.AWS_SERVICE:
            return None, field_name, False

        if arn := aws_extra.get("arn"):
            _param_id = arn
        elif secret_name := aws_extra.get("secret_name"):
            _param_id = secret_name
        elif aws_extra.get("env_var_format"):
            _param_id = field_name.upper()
        else:
            _param_id = field_name

        try:
            client = self.get_region_client(aws_extra.get("region"))
            result = client.get_secret_value(SecretId=_param_id)
        except ClientError:
            return None, field_name, False
        else:
            value = result["SecretString"]
            try:
                json_obj = json.loads(value)
                return json_obj, field_name, True
            except ValueError:
                return value, field_name, False
