from typing import (
    Any,
    Union,  # pyright: ignore[reportDeprecated]
    get_args as get_type_args,
    get_origin as get_type_origin,
)

import cattrs
from cattrs import strategies
from monads.option import Null, Option, Some
from monads.tools import from_none

converter = cattrs.Converter()
strategies.configure_union_passthrough(bool | int | float | str | None, converter)


def wrap_option[T](obj: object, type_: type[Option[T]]) -> Option[T]:
    parametrized_some = get_type_args(type_)[0]
    wrapped_type = get_type_args(parametrized_some)[0]
    return from_none(converter.structure(obj, wrapped_type))


def check_is_option(cls: Any) -> bool:
    if get_type_origin(cls) is not Union:  # pyright: ignore[reportDeprecated]
        return False

    args = get_type_args(cls)

    if len(args) != 2:  # noqa: PLR2004
        return False

    if args[1] is not Null:
        return False

    return get_type_origin(args[0]) is Some


converter.register_structure_hook_func(check_is_option, wrap_option)
