import inspect
import typing as t
from types import MappingProxyType

from attrs import define, field

from typeshed import KT, VT, P

__all__ = ("Manager",)


# VT: the actual value
# KT: value VT is stored under
# P: arguments VT is created from


def func_repr(func: t.Callable[..., t.Any]) -> str:
    """Returns a signature of a function."""
    signature = inspect.signature(func)
    return f"{func.__name__}{signature}"


def large_container_repr(container: t.Sized, /, *, threshold: int = 20) -> str:
    """Repr returning the number of elements for large collections."""

    if len(container) > threshold:
        return f"<{type(container).__name__} of {len(container)} elements>"

    return repr(container)


@define
class Manager(t.Generic[KT, VT, P]):
    """Provides means to create, retrieve and cache objects.

    Parameters
    ----------
    factory: callable creating objects from arguments P.
    key: callable creating keys to store objects under.
    """

    factory: t.Callable[P, VT] = field(repr=func_repr)
    """Creates an object from given value."""

    key: t.Callable[P, KT] = field(repr=func_repr)
    """Retrieves a key used to store a given object under."""

    _store: dict[KT, VT] = field(factory=dict, init=False, repr=large_container_repr)

    @property
    def mapping(self) -> t.Mapping[KT, VT]:
        """Read-only proxy of the underlying mapping."""
        return MappingProxyType(self._store)

    def __contains__(self, key: KT, /) -> bool:
        return key in self._store

    def lookup_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve stored or create an object from given value."""
        key = self.key(*args, **kwargs)
        try:
            return self._store[key]

        except KeyError:
            obj = self.factory(*args, **kwargs)
            self._store[key] = obj
            return obj
