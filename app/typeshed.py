import typing as t

T = t.TypeVar("T")
T2 = t.TypeVar("T2")
KT = t.TypeVar("KT")
VT = t.TypeVar("VT")
P = t.ParamSpec("P")

twotuple = tuple[T, T]
XOrTupleXY = T | tuple[T, T2]
SupportsSet = t.TypeVar("SupportsSet", bound=t.Hashable)
Coro = t.Coroutine[t.Any, t.Any, T]


def dict_items_as(value_type: type[VT], obj: t.Mapping[KT, t.Any]) -> t.ItemsView[KT, VT]:
    """Helper function to aid iterating over TypedDict.items()."""
    return obj.items()
