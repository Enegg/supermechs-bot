import inspect
import typing as t
from collections.abc import Mapping
from types import MappingProxyType

from attrs import define, field

from typeshed import KT, VT, P

from supermechs.utils import large_mapping_repr

__all__ = ("Manager", "default_key")


# P: parameter specification of callable creating objects VT
# VT: type of stored values
# KT: type of keys values are stored under


def callable_repr(func: t.Callable[..., t.Any], /) -> str:
    """Returns a signature of a callable."""
    signature = inspect.signature(func)
    return f"{func.__name__}{signature}"


def default_key(*args: t.Hashable, **kwargs: t.Hashable) -> t.Hashable:
    """Computes a key from all args and kwargs by creating a single large tuple.
    Requires all members to be hashable.
    """
    if not kwargs:
        return args

    args_list = list(args)

    for key_val_tuple in kwargs.items():
        args_list += key_val_tuple

    return tuple(args_list)


@define
class Manager(t.Generic[P, VT, KT], Mapping[KT, VT]):
    """Provides means to create, store and retrieve objects.

    Parameters
    ----------
    factory: callable creating objects from arguments P.
    key: callable computing keys to store objects under.
    """
    factory: t.Callable[P, VT] = field(repr=callable_repr)
    """Creates an object from given value."""

    key: t.Callable[P, KT] = field(repr=callable_repr)
    """Retrieves a key used to store a given object under."""

    _store: t.MutableMapping[KT, VT] = field(factory=dict, init=False, repr=large_mapping_repr)

    @property
    def mapping(self) -> t.Mapping[KT, VT]:
        """Read-only proxy of the underlying mapping."""
        return MappingProxyType(self._store)

    def __getitem__(self, key: KT, /) -> VT:
        return self._store[key]

    def __len__(self) -> int:
        return len(self._store)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        return self.lookup_or_create(*args, **kwargs)

    def lookup_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve stored or create an object from given value."""
        key = self.key(*args, **kwargs)
        try:
            return self._store[key]

        except KeyError:
            obj = self.factory(*args, **kwargs)
            self._store[key] = obj
            return obj
