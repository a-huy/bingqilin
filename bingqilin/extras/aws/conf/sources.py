import json
from typing import Any, Dict, Literal, Optional, Type, Union

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
from bingqilin.logger import bq_logger

logger = bq_logger.getChild("aws.conf.sources")


class BaseAWSSettingsSource(BingqilinSettingsSource):
    type: Literal["aws"]
    package_deps = ["boto3"]
    AWS_SERVICE = None
    DEFAULT_ALWAYS_FETCH = True

    def __init__(
        self,
        settings_cls: Type[BaseSettings],
        region=None,
        access_key_id=None,
        secret_access_key=None,
        always_fetch: Optional[bool] = None,
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
        self.always_fetch = (
            settings_cls.model_config.get("always_fetch") or always_fetch
        )

    def get_region_client(self, region=None):
        if not region:
            region = self.default_region
        if region not in self.clients_by_region:
            self.clients_by_region[region] = self.session.client(
                service_name=self.AWS_SERVICE, region_name=region
            )
        return self.clients_by_region[region]

    def get_aws_extra(self, field_info: FieldInfo) -> Dict:
        if not field_info.json_schema_extra:
            return {}
        aws_extra = field_info.json_schema_extra.get(AWS_FIELD_EXTRA_NAMESPACE) or {}
        assert isinstance(aws_extra, dict), (
            f"AWS extra must be a dict, got {type(aws_extra)}"
        )
        return aws_extra

    def do_always_fetch(self, field_info: FieldInfo) -> bool:
        _value = None
        # The setting on the field takes precedence over the source setting
        aws_extra = self.get_aws_extra(field_info)
        if "always_fetch" in aws_extra:
            _value = aws_extra["always_fetch"]

        # If the setting on the field is not set, use the source setting
        if _value is None:
            _value = self.always_fetch

        # If the source setting is not set, use the default value
        if _value is None:
            return self.DEFAULT_ALWAYS_FETCH

        assert isinstance(_value, bool)
        return _value

    def __call__(self) -> dict[str, Any]:
        values = {}

        def fields_walk(prefixes: list[str], model: type[BaseModel]):
            for field_name, field_info in model.model_fields.items():
                current_prefixes = prefixes + [field_name]

                # If the field is a submodel, recurse into it
                if field_info.annotation and isinstance(
                    field_info.annotation, type(BaseModel)
                ):
                    fields_walk(current_prefixes, field_info.annotation)
                    continue

                # If this isn't a submodel and the field does not have the proper metadata, skip it
                aws_extra = self.get_aws_extra(field_info)
                if aws_extra.get("service") != self.AWS_SERVICE:
                    continue

                # Check if already set in current_state
                current = self.current_state
                try:
                    for part in prefixes:
                        current = current.get(part, {})
                except Exception:
                    logger.exception(
                        "An error occurred while attempting to fetch a current value for %s",
                        field_name,
                    )

                has_current_value = (
                    field_name in current
                    and current[field_name] is not None
                    and current[field_name] != ""
                )
                if has_current_value and not self.do_always_fetch(field_info):
                    continue

                value, key, is_complex = self.get_field_value(field_info, field_name)
                if value is not None:
                    prepared_val = self.prepare_field_value(
                        key, field_info, value, is_complex
                    )
                    cursor = values
                    for part in current_prefixes[:-1]:
                        cursor = cursor.setdefault(part, {})
                    cursor[current_prefixes[-1]] = prepared_val

        fields_walk([], self.settings_cls)
        return values


class AWSSystemsManagerParamsSource(BaseAWSSettingsSource):
    type: Literal["aws_ssm"]

    AWS_SERVICE = AWS_SSM_SERVICE

    class SourceConfig(BaseSourceConfig):
        region: Optional[str]
        access_key_id: Optional[str]
        secret_access_key: Optional[str]
        # If False, only attempt to fetch the value if the field is not already set.
        always_fetch: bool = True

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
        assert isinstance(param_info, dict)

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
        assert isinstance(aws_extra, dict)

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
