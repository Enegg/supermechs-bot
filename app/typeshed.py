import typing as t

from typing_extensions import ParamSpec, TypeVar

T = TypeVar("T", default=t.Any, infer_variance=True)
T2 = TypeVar("T2", default=t.Any, infer_variance=True)
KT = TypeVar("KT")
"""Key-type of a mapping."""
VT = TypeVar("VT")
"""Value-type of a mapping."""
P = ParamSpec("P")
SupportsHash = TypeVar("SupportsHash", bound=t.Hashable)
"""Type supporting hashing."""

twotuple = tuple[T, T]
"""Tuple of two elements of same type."""
XOrTupleXY = T | tuple[T, T2]
"""Type or tuple of two types."""
Coro = t.Coroutine[t.Any, t.Any, T]
Factory = t.Callable[[], T]
"""0-argument callable returning an object of given type."""
LiteralURL: t.TypeAlias = str
"""String representing a URL."""


def dict_items_as(value_type: type[VT], obj: t.Mapping[KT, t.Any]) -> t.ItemsView[KT, VT]:
    """Helper function to aid iterating over TypedDict.items()."""
    return obj.items()
