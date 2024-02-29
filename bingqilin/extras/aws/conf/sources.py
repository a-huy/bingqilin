import json
from typing import Any, Literal, Optional, Type, Union

from botocore.exceptions import ClientError
from pydantic import BaseModel, ConfigDict
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

    def get_param_value(
        self, field_info: FieldInfo, field_name: str
    ) -> Union[str, None]:
        if not (
            isinstance(field_info.json_schema_extra, dict)
            and AWS_FIELD_EXTRA_NAMESPACE in field_info.json_schema_extra
        ):
            return None

        param_info = field_info.json_schema_extra[AWS_FIELD_EXTRA_NAMESPACE]

        if param_info.get("service") != self.AWS_SERVICE:
            return None

        if arn := param_info.get("arn"):
            _param_id = arn
        elif param_name := param_info.get("param_name"):
            _param_id = param_name
        elif param_info.get("env_var_format"):
            _param_id = field_name.upper()
        else:
            _param_id = field_name

        try:
            client = self.get_region_client(param_info.get("region"))
            result = client.get_parameter(Name=_param_id, WithDecryption=True)
        except ClientError:
            return None
        else:
            return result["Parameter"]["Value"]

    def get_params_from_model(self, model_cls: Type[BaseModel]) -> Union[dict, None]:
        values = {}
        for field_name in model_cls.model_fields:
            info = model_cls.model_fields[field_name]

            if info.annotation and isinstance(info.annotation, type(BaseModel)):
                values[field_name] = self.get_params_from_model(info.annotation)

            param_value = self.get_param_value(info, field_name)
            if param_value is not None:
                values[field_name] = param_value

        if not values:
            values = None

        return values

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        if field.annotation and isinstance(field.annotation, type(BaseModel)):
            return self.get_params_from_model(field.annotation), field_name, False

        return self.get_param_value(field, field_name), field_name, False


class AWSSecretsManagerSource(BaseAWSSettingsSource):
    type: Literal["aws_secretsmanager"]

    AWS_SERVICE = AWS_SECRETS_MANAGER_SERVICE

    class SourceConfig(BaseSourceConfig):
        region: Optional[str]
        access_key_id: Optional[str]
        secret_access_key: Optional[str]

        model_config = ConfigDict(title="AWSSecretsManagerSourceConfig")

    def get_secret_value(self, field_info: FieldInfo, field_name: str):
        if not (
            isinstance(field_info.json_schema_extra, dict)
            and AWS_FIELD_EXTRA_NAMESPACE in field_info.json_schema_extra
        ):
            return None

        aws_extra = field_info.json_schema_extra[AWS_FIELD_EXTRA_NAMESPACE]
        if aws_extra.get("service") != self.AWS_SERVICE:
            return None

        if arn := aws_extra.get("arn"):
            _secret_id = arn
        elif secret_name := aws_extra.get("secret_name"):
            _secret_id = secret_name
        elif aws_extra.get("env_var_format"):
            _secret_id = field_name.upper()
        else:
            _secret_id = field_name

        try:
            client = self.get_region_client(aws_extra.get("region"))
            result = client.get_secret_value(SecretId=_secret_id)
        except ClientError:
            return None
        else:
            value = result["SecretString"]
            try:
                return json.loads(value)
            except ValueError:
                return value

    def get_secrets_from_model(self, model_cls: Type[BaseModel]) -> Union[dict, None]:
        values = {}
        for field_name in model_cls.model_fields:
            info = model_cls.model_fields[field_name]

            if info.annotation and isinstance(info.annotation, type(BaseModel)):
                values[field_name] = self.get_secrets_from_model(info.annotation)

            secret_value = self.get_secret_value(info, field_name)
            if secret_value is not None:
                values[field_name] = secret_value

        if not values:
            values = None

        return values

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        if field.annotation and isinstance(field.annotation, type(BaseModel)):
            return self.get_secrets_from_model(field.annotation), field_name, False

        return self.get_secret_value(field, field_name), field_name, False
