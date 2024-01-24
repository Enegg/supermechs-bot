import inspect
import typing
from collections import abc
from types import MappingProxyType

from attrs import define, field

from typeshed import KT, VT, P

from supermechs.utils import large_mapping_repr

__all__ = ("Manager", "default_key")


def callable_repr(func: abc.Callable[..., object], /) -> str:
    """Returns the signature of a callable."""
    signature = inspect.signature(func)
    return f"{func.__name__}{signature}"


def default_key(*args: abc.Hashable, **kwargs: abc.Hashable) -> abc.Hashable:
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
class Manager(typing.Generic[P, VT, KT], abc.Mapping[KT, VT]):
    """Provides means to create, store and retrieve objects.

    Parameters
    ----------
    factory: callable creating objects from arguments P.
    key: callable computing keys to store objects under.
    """

    factory: abc.Callable[P, VT] = field(repr=callable_repr)
    """Creates an object from given value."""

    key: abc.Callable[P, KT] = field(repr=callable_repr)
    """Retrieves a key used to store a given object under."""

    _store: dict[KT, VT] = field(factory=dict, init=False, repr=large_mapping_repr)

    @property
    def mapping(self) -> abc.Mapping[KT, VT]:
        """Read-only proxy of the underlying mapping."""
        return MappingProxyType(self._store)

    def __getitem__(self, key: KT, /) -> VT:
        return self._store[key]

    def __len__(self) -> int:
        return len(self._store)

    def __iter__(self) -> abc.Iterator[KT]:
        return iter(self._store)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        return self.get_or_create(*args, **kwargs)

    def get_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve stored or create an object from given value."""
        key = self.key(*args, **kwargs)
        try:
            return self._store[key]

        except KeyError:
            obj = self.factory(*args, **kwargs)
            self._store[key] = obj
            return obj

    def create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Create and store an object from given value."""
        key = self.key(*args, **kwargs)
        obj = self.factory(*args, **kwargs)
        self._store[key] = obj
        return obj
