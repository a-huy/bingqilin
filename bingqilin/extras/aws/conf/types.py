from typing import Any, Callable, Optional, Union

from pydantic import Field, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, PydanticCustomError, core_schema

PARTITIONS = ("aws", "aws-us-gov", "aws-cn")


AWS_FIELD_EXTRA_NAMESPACE = "aws"
AWS_SSM_SERVICE = "ssm"
AWS_SECRETS_MANAGER_SERVICE = "secretsmanager"


ARNType = Union[str, "ARN"]


class ARN:
    PART_DELIMITER = ":"
    PATH_DELIMITER = "/"

    partition: str
    service: str
    resource_id: str
    account_id: Optional[str] = None
    region: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id_is_path: bool = False

    def __init__(self, value: ARNType) -> None:
        super().__init__()
        if isinstance(value, str):
            self.init_from_str(value)
        elif isinstance(value, "ARN"):
            self.partition = value.partition
            self.service = value.service
            self.region = value.region
            self.account_id = value.account_id
            self.resource_id = value.resource_id
            self.resource_type = value.resource_type
            self.resource_id_is_path = value.resource_id_is_path

    def __str__(self) -> str:
        base_str = f"arn:{self.partition}:{self.service}:{self.region or ''}:{self.account_id or ''}"
        if self.resource_type:
            delimiter = (
                self.PATH_DELIMITER if self.resource_id_is_path else self.PART_DELIMITER
            )
            return f"{base_str}:{self.resource_type or ''}{delimiter}{self.resource_id}"
        else:
            return f"{base_str}:{self.resource_id}"

    def init_from_str(self, value):
        parts = value.split(self.PART_DELIMITER)
        if parts[0] != "arn":
            raise PydanticCustomError(
                "arn_error",
                'value is not a valid ARN: values must start with "arn:"',
            )
        if len(parts) < 6:
            raise PydanticCustomError(
                "arn_error",
                "value is not a valid ARN: not enough information provided",
            )

        partition = parts[1]
        if partition not in PARTITIONS:
            raise PydanticCustomError(
                "arn_error",
                "value is not a valid ARN: not a valid partition",
            )

        service = parts[2]
        region = parts[3] or None
        account_id = parts[4] or None
        resource_id_is_path = False

        if len(parts) == 6:
            _resource = parts[5]
            if self.PATH_DELIMITER not in _resource:
                resource_id = parts[5]
                resource_type = None
            else:
                path_parts = _resource.split(self.PATH_DELIMITER)
                resource_type = path_parts[0]
                resource_id = self.PATH_DELIMITER.join(path_parts[1:])
                resource_id_is_path = True
        else:
            resource_type = parts[5]
            resource_id = self.PART_DELIMITER.join(parts[6:])

        self.partition = partition
        self.service = service
        self.region = region
        self.account_id = account_id
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.resource_id_is_path = resource_id_is_path

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema: dict[str, Any] = {}
        field_schema.update(type="string", format="arn")
        return field_schema

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: Callable[[Any], CoreSchema]
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_plain_validator_function(
            cls._validate, serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def _validate(cls, __input_value: Any, _: Any) -> "ARN":
        return cls(__input_value)


def SSMParameterField(
    arn: Optional[str] = None,
    param_name: Optional[str] = None,
    env_var_format: bool = True,
    region: Optional[str] = None,
    account_id: Optional[str] = None,
    *args,
    **kwargs,
):
    # If no ARN is specified, then the name of the field is used.
    return Field(
        json_schema_extra={
            AWS_FIELD_EXTRA_NAMESPACE: {
                "service": AWS_SSM_SERVICE,
                "arn": arn,
                "param_name": param_name,
                "env_var_format": env_var_format,
                "region": region,
                "account_id": account_id,
            }
        },
        *args,
        **kwargs,
    )


def SecretsManagerField(
    arn: Optional[str] = None,
    secret_name: Optional[str] = None,
    env_var_format: bool = True,
    region: Optional[str] = None,
    account_id: Optional[str] = None,
    *args,
    **kwargs,
):
    # If no ARN nor secret_name is specified, then the name of the field is used.
    return Field(
        json_schema_extra={
            AWS_FIELD_EXTRA_NAMESPACE: {
                "service": AWS_SECRETS_MANAGER_SERVICE,
                "arn": arn,
                "secret_name": secret_name,
                "env_var_format": env_var_format,
                "region": region,
                "account_id": account_id,
            }
        },
        *args,
        **kwargs,
    )
