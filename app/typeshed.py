import typing as t
import typing_extensions as tex

T = tex.TypeVar("T", infer_variance=True)
T2 = tex.TypeVar("T2", infer_variance=True)
KT = t.TypeVar("KT", bound=t.Hashable)
"""Key-type of a mapping."""
VT = t.TypeVar("VT")
"""Value-type of a mapping."""
P = t.ParamSpec("P")
"""Parameter specification of a callable."""

twotuple = tuple[T, T]
"""Tuple of two elements of same type."""
XOrTupleXY = T | tuple[T, T2]
"""Type or tuple of two types."""
Factory = t.Callable[[], T]
"""0-argument callable returning an object of given type."""
LiteralURL: t.TypeAlias = str
"""String representing a URL."""


def dict_items_as(value_type: type[VT], obj: t.Mapping[KT, t.Any]) -> t.ItemsView[KT, VT]:
    """Helper function to aid iterating over TypedDict.items()."""
    return obj.items()
