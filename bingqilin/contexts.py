import uuid
from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Dict, Generic, Optional, Self, Type, Union, get_origin

from pydantic import BaseModel
from pydantic._internal._decorators import ReturnType, is_instance_method_from_sig

from bingqilin.conf import SettingsManager
from bingqilin.conf.models import ConfigModel
from bingqilin.db.models import DBConfig, RedisDBConfig, SQLAlchemyDBConfig
from bingqilin.logger import bq_logger
from bingqilin.signal import RECONFIGURE_SIGNAL, dispatcher

logger = bq_logger.getChild("contexts")

context_classes: OrderedDict[str, "LifespanContextMeta"] = OrderedDict()


class ContextFieldTypes(StrEnum):
    DATABASES = "databases"
    THIRD_PARTIES = "third_parties"


class ContextFieldInfo:
    namespace: str = ""
    UNKNOWN = "_unknown"

    config_model: Optional[Type[BaseModel]]
    init_from_config: bool
    initialize_func: Optional[Callable]
    terminate_func: Optional[Callable]
    config_getter_func: Optional[Callable[[BaseModel], Any]]
    is_default: bool

    def __init__(
        self,
        namespace: str,
        config_model: Optional[Type[BaseModel]] = None,
        initialize_func: Optional[Callable] = None,
        terminate_func: Optional[Callable] = None,
        config_getter_func: Optional[Callable[[BaseModel], Any]] = None,
        is_default: bool = False,
    ) -> None:
        self.namespace = namespace
        self.config_model = config_model
        self.initialize_func = initialize_func
        self.terminate_func = terminate_func
        self.config_getter_func = config_getter_func
        self.is_default = is_default


def ContextField(
    namespace: Optional[str] = None,
    config_model: Optional[Type[BaseModel]] = None,
    initialize_func: Optional[Callable] = None,
    terminate_func: Optional[Callable] = None,
    config_getter_func: Optional[Callable[[BaseModel], Any]] = None,
    is_default: bool = False,
) -> Any:
    return ContextFieldInfo(
        namespace or ContextFieldInfo.UNKNOWN,
        config_model=config_model,
        initialize_func=initialize_func,
        terminate_func=terminate_func,
        config_getter_func=config_getter_func,
        is_default=is_default,
    )


def DatabaseField(
    config_model: Optional[Type[DBConfig]] = None,
    initialize_func: Optional[Callable] = None,
    terminate_func: Optional[Callable] = None,
    config_getter_func: Optional[Callable[[BaseModel], Any]] = None,
    is_default: bool = False,
) -> Any:
    def init_from_db_config(config: Union[DBConfig, Dict]) -> Any:
        if not isinstance(config, DBConfig):
            raise ValueError(
                "No initialize function or initializer method specified, "
                "and database config is passed in is not a DBConfig model."
            )
        return config.initialize_client()

    if not initialize_func:
        initialize_func = init_from_db_config

    return ContextFieldInfo(
        ContextFieldTypes.DATABASES,
        config_model=config_model,
        initialize_func=initialize_func,
        terminate_func=terminate_func,
        config_getter_func=config_getter_func,
        is_default=is_default,
    )


def ThirdPartyField(
    config_model: Optional[Type[BaseModel]] = None,
    initialize_func: Optional[Callable] = None,
    terminate_func: Optional[Callable] = None,
    config_getter_func: Optional[Callable] = None,
    is_default: bool = False,
) -> Any:
    return ContextFieldInfo(
        ContextFieldTypes.THIRD_PARTIES,
        config_model=config_model,
        initialize_func=initialize_func,
        terminate_func=terminate_func,
        config_getter_func=config_getter_func,
        is_default=is_default,
    )


@dataclass
class ContextDecoratorInfo:
    field: str


@dataclass
class ContextDescriptorProxy(Generic[ReturnType]):
    """This is taken from Pydantic's `PydanticDescriptorProxy` and adapted for use
    here to collect initializer methods during context class creation.

    Args:
        Generic (_type_): The proxy will wrap a classmethod.

    Returns:
        Self: Wrapped function
    """

    wrapped: Callable[..., ReturnType]
    decorator_info: ContextDecoratorInfo

    def _call_wrapped_attr(
        self, func: Callable[[Any], None], *, name: str
    ) -> "ContextDescriptorProxy[ReturnType]":
        self.wrapped = getattr(self.wrapped, name)(func)
        return self

    def __get__(
        self, obj: object | None, obj_type: type[object] | None = None
    ) -> "ContextDescriptorProxy[ReturnType]":
        try:
            return self.wrapped.__get__(obj, obj_type)
        except AttributeError:
            # not a descriptor, e.g. a partial object
            return self.wrapped  # type: ignore[return-value]

    def __set_name__(self, instance: Any, name: str) -> None:
        if hasattr(self.wrapped, "__set_name__"):
            self.wrapped.__set_name__(instance, name)

    def __getattr__(self, __name: str) -> Any:
        """Forward checks for __isabstractmethod__ and such."""
        return getattr(self.wrapped, __name)


class InitializerDescriptorProxy(ContextDescriptorProxy):
    pass


class TerminatorDescriptorProxy(ContextDescriptorProxy):
    pass


def initializer(field: str):
    def inner(func):
        if is_instance_method_from_sig(func):
            raise RuntimeError(
                f"@initializer() applied to {func} cannot be an instance method."
            )
        dec_info = ContextDecoratorInfo(field=field)
        return InitializerDescriptorProxy(func, dec_info)

    return inner


def terminator(field: str):
    def inner(func):
        if is_instance_method_from_sig(func):
            raise RuntimeError(
                f"@terminator() applied to {func} cannot be an instance method."
            )
        dec_info = ContextDecoratorInfo(field=field)
        return TerminatorDescriptorProxy(func, dec_info)

    return inner


class LifespanContextMeta(type):
    name: str = ""

    def __new__(
        __mcls: type[Self],
        __name: str,
        __bases: tuple[type, ...],
        __namespace: dict[str, Any],
        **kwargs: Any,
    ) -> Self:
        if __name == "LifespanContext":
            return super().__new__(__mcls, __name, __bases, __namespace, **kwargs)

        __namespace["__context_fields__"] = {}
        __namespace["__default_fields__"] = {}
        __namespace["__field_initializers__"] = {}
        __namespace["__field_terminators__"] = {}

        for field, field_type in __namespace.items():
            if isinstance(field_type, ContextFieldInfo):
                __namespace["__context_fields__"][field] = field_type
                if field_type.is_default:
                    if field_type.namespace in __namespace["__default_fields__"]:
                        raise ValueError(
                            f"Multiple attributes for context {__name} are marked as "
                            f'default for their ctx type "{field_type.namespace}". '
                            "Only one can be default."
                        )
                    __namespace["__default_fields__"][field_type.namespace] = field

            elif isinstance(field_type, InitializerDescriptorProxy):
                _field_name = field_type.decorator_info.field
                __namespace["__field_initializers__"][_field_name] = field_type.wrapped

            elif isinstance(field_type, TerminatorDescriptorProxy):
                _field_name = field_type.decorator_info.field
                __namespace["__field_terminators__"][_field_name] = field_type.wrapped

        for field in __namespace["__context_fields__"].keys():
            __namespace.pop(field, None)

        if not __namespace.get("name"):
            __namespace["name"] = f"context_{uuid.uuid4()}"

        if __namespace["name"] in context_classes:
            raise ValueError(
                f"Context manager with name {__namespace['name']} is already defined."
            )

        newcls = super().__new__(__mcls, __name, __bases, __namespace, **kwargs)
        context_classes[newcls.name] = newcls

        return newcls


class LifespanContext(metaclass=LifespanContextMeta):
    name: Optional[str] = None
    allow_reconfigure = True

    __context_fields__: Dict[str, ContextFieldInfo] = {}
    __default_fields__: Dict[str, str] = {}
    __field_initializers__: Dict[str, Callable] = {}
    __field_terminators__: Dict[str, Callable] = {}

    def __init__(
        self,
        settings_manager: Optional[SettingsManager] = None,
        allow_reconfigure: bool = True,
    ) -> None:
        if not self.name:
            self.name = f"context_{uuid.uuid4()}"
        self.settings = settings_manager

        # This takes the highest precedence. If it is disabled in config, then
        # it is _absolutely_ disabled.
        if (
            self.settings
            and isinstance(self.settings.data, ConfigModel)
            and not self.settings.data.allow_reconfigure
        ):
            self.allow_reconfigure = False
        else:
            self.allow_reconfigure = allow_reconfigure

        if self.allow_reconfigure:
            self.register_reconfigure()

    def register_reconfigure(self):
        if not self.settings:
            logger.warning(
                "No settings manager was passed into the constructor for the %s "
                "context instance. It is highly recommended that you do, since the "
                "reconfigure handler will only have access to the context instance.",
                self.name,
            )
        dispatcher.add_handler(RECONFIGURE_SIGNAL, self.configure)

    def _initialize_field(
        self, field: str, field_info: ContextFieldInfo, init_values: Any
    ) -> bool:
        """Initialize a field with the given config/values.
        Functions for initializing this field can come from different places, listed in
        order of decreasing precedence:

        * Use the `initialize_func` specified on the field
        * Use the decorated `@initializer` classmethod on the context class
        * As a last resort, attempt to get the field's annotated type and create an
        instance from that class

        Args:
            field (_type_): Name of the field to initialize
            (as an attribute in the context)
            field_info (_type_): Field metadata declared on the context's attribute
            init_values (_type_): A Pydantic `BaseModel` or dict to initialize the
            attribute with

        Returns:
            bool: The initialization was successful
        """
        result = None
        if field_info.initialize_func:
            result = field_info.initialize_func(init_values)
        elif _f_init := self.__field_initializers__.get(field):
            result = _f_init(init_values)
        elif annotation := self.__annotations__.get(field):
            if not get_origin(annotation):
                # The origin of the annotated type is an Annotation, Generic, or Union
                # type. If this check passed, it means that it was annotated with a type
                # we can't use to create our context field instance from without any way
                # to disambiguate it.
                result = annotation(init_values)

        if result:
            setattr(self, field, result)
            return True

        return False

    def _get_config_from_settings_data(self, field, field_info, settings_data):
        if context_config := getattr(settings_data, field_info.namespace, None):
            if field_config := getattr(context_config, field):
                return field_config

    def _get_field_config(
        self,
        field: str,
        field_info: ContextFieldInfo,
        settings_data: Optional[BaseModel],
        field_init_kwargs: dict,
    ) -> Any:
        """This will attempt to get the config values from different places
        (in order of decreasing precedence):

        * Keyword args passed in when calling `context.configure()`
        * From the field's `config_getter_func`, if it exists and a settings instance
        is specified
        * As a last resort, it will attempt to get the model from the settings instance
        using the attribute path "settings.<context_name>.<field_name>"
        * If all else fails, use an empty dict

        Then, if a config_model is specified on the field, and the config values are not
        an instance of config_model, then an attempt is made to coerce it to that type.

        Args:
            field (str): Name of the field to initialize
            (as an attribute in the context)
            field_info (ContextFieldInfo): Field metadata declared on the context's
            attribute
            settings_data (Optional[BaseModel]): _description_
            field_init_kwargs (dict): _description_

        Returns:
            Any: An instance of the field's config_model, if specified.
            Otherwise, it's a dict of containing the config values to pass into the
            annotated type of the field.
        """
        _config = field_init_kwargs

        if not _config:
            _ctx_settings = self.settings.data if self.settings else None
            if _settings := settings_data or _ctx_settings:
                if field_info.config_getter_func:
                    _config = field_info.config_getter_func(_settings)
                else:
                    _config = self._get_config_from_settings_data(
                        field, field_info, _settings
                    )

        if not _config:
            _config = {}

        if field_info.config_model and not isinstance(_config, field_info.config_model):
            _config = field_info.config_model(**_config)

        return _config

    def configure(
        self,
        settings_data: Optional[BaseModel] = None,
        raise_on_unconfigured=True,
        **all_field_kwargs,
    ) -> Self:
        _ctx_settings = self.settings.data if self.settings else None
        _settings = settings_data or _ctx_settings
        configured_fields = {}
        for field, field_info in self.__context_fields__.items():
            _config = self._get_field_config(
                field, field_info, _settings, all_field_kwargs.get(field) or {}
            )
            configured_fields[field] = self._initialize_field(
                field, field_info, _config
            )

        if raise_on_unconfigured:
            uninitialized = set(self.__context_fields__.keys()) - set(
                [k for k in configured_fields.keys() if k]
            )
            if uninitialized:
                raise RuntimeError(
                    f'The attributes on context "{self.name}" were '
                    f"uninitialized: {uninitialized}"
                )
        return self

    def terminate(self):
        for field, field_info in self.__context_fields__.items():
            attr_value = getattr(self, field)
            if field_info.terminate_func:
                field_info.terminate_func(attr_value)
            elif _f_term := self.__field_terminators__.get(field):
                _f_term(attr_value)

    def get_default(self, namespace: Optional[str] = None) -> Any:
        if not namespace and len(self.__default_fields__) == 1:
            namespace = tuple(self.__default_fields__.keys())[0]

        if not namespace or namespace not in self.__default_fields__:
            return None

        return getattr(self, self.__default_fields__[namespace], None)


# Convenience context field types


def SQLAlchemyField(**kwargs):
    return DatabaseField(config_model=SQLAlchemyDBConfig, **kwargs)


def RedisField(**kwargs):
    return DatabaseField(config_model=RedisDBConfig, **kwargs)
