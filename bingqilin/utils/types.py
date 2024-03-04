from abc import ABCMeta, abstractmethod
from functools import reduce
from typing import Any, Callable, Dict, List, MutableMapping, Optional

from pydantic import SerializerFunctionWrapHandler
from pydantic._internal._validators import import_string
from pydantic.functional_serializers import WrapSerializer
from pydantic.functional_validators import AfterValidator
from pydantic_core import core_schema
from typing_extensions import Annotated, get_args


def get_annotation_literal_value(obj, attr_name):
    annotations = obj.__annotations__
    if attr_annotation := annotations.get(attr_name):
        if attr_annotation.__args__:
            return attr_annotation.__args__[0]

    raise ValueError(
        f'The "{attr_name}" attribute must exist on {obj} and be annotated with a '
        "literal string."
    )


class RegistryMixin:
    @classmethod
    def get_registry_type(cls, registry_field):
        registry_field_value = get_annotation_literal_value(cls, registry_field)
        if not registry_field_value:
            raise ValueError(
                f'Class {cls} does not have a required field "{registry_field}". '
                "This field must be a literal string that serves as an identifier in its "
                "registry."
            )
        return registry_field_value


class RegistryMeta(ABCMeta):
    registry_field: str
    root_class: str

    def __new__(
        __mcls: type["RegistryMeta"],
        __name: str,
        __bases: tuple[type, ...],
        __namespace: dict[str, Any],
        **kwargs: Any,
    ) -> "RegistryMeta":
        if not __mcls._get_root_class_literal():
            raise ValueError(
                'This registry metaclass must have a "root_class" class attribute that is '
                "annotated with a Literal string representing the import path of a base "
                "class for registry values."
            )

        registry_field_value = __mcls.get_registry_field_literal()
        if not registry_field_value:
            raise ValueError(
                'This registry metaclass must have a "registry_field" class attribute that '
                "is annotated with a Literal string representing the attribute value to get "
                "from its created classes. This value will be used as an identifier for "
                "the registry."
            )

        root_class_name = __mcls.get_root_class_name()
        all_bases = reduce(lambda x, y: x | y, [set(b.__mro__) for b in __bases])

        # If the registry mixin is not in any of the MRO classes, then add it to bases
        if __name != root_class_name and RegistryMixin not in all_bases:
            __bases = tuple(list(__bases) + [RegistryMixin])

        cls = super().__new__(__mcls, __name, __bases, __namespace, **kwargs)

        if __name != root_class_name:
            root_class = __mcls.import_root_class()
            if root_class in all_bases:
                __mcls.add_to_registry(cls, registry_field_value)

        return cls

    @classmethod
    def get_registry_field_literal(cls) -> Optional[str]:
        return get_annotation_literal_value(cls, "registry_field")

    @classmethod
    def _get_root_class_literal(cls) -> str:
        return get_annotation_literal_value(cls, "root_class")

    @classmethod
    def get_root_class_name(cls) -> str:
        root_class_string = cls._get_root_class_literal()
        delimiter = ":" if ":" in root_class_string else "."
        return root_class_string.split(delimiter)[-1]

    @classmethod
    def import_root_class(cls) -> type:
        root_class_string = cls._get_root_class_literal()
        return import_string(root_class_string)

    @classmethod
    def add_to_registry(cls, new_class, registry_field) -> None:
        registry = cls.get_registry()
        registry[new_class.get_registry_type(registry_field)] = new_class

    @classmethod
    @abstractmethod
    def get_registry(cls) -> MutableMapping:
        raise RuntimeError("This method must return a mapping object.")


class AttrKeysDict(dict):
    """This is a Pydantic type based on a dict that enables accessing keys as attributes."""

    def __getattribute__(self, __name: str) -> Any:
        try:
            return super().__getattribute__(__name)
        except AttributeError as exn:
            if __name in self:
                return self[__name]
            raise exn

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: Callable[[Any], core_schema.CoreSchema]
    ) -> core_schema.CoreSchema:
        instance_schema = core_schema.is_instance_schema(cls)

        args = get_args(source)
        if args:
            # replace the type and rely on Pydantic to generate the right schema
            # for `Dict`
            dict_t_schema = handler.generate_schema(Dict[args[0], args[1]])  # type: ignore
        else:
            dict_t_schema = handler.generate_schema(Dict)

        non_instance_schema = core_schema.with_info_after_validator_function(
            lambda v, i: AttrKeysDict(v), dict_t_schema
        )
        return core_schema.union_schema([instance_schema, non_instance_schema])

    def items(self):
        return dict(self).items()


def validate_csv_line(value: str) -> List[str]:
    return [v.strip() for v in value.split(",")]


def serialize_csv_line(value: List[str], next: SerializerFunctionWrapHandler) -> str:
    return next(",".join(value))


CSVLine = Annotated[
    str,
    AfterValidator(validate_csv_line),
    WrapSerializer(func=serialize_csv_line),
]
