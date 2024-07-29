import typing
from collections import abc

from attrs import define, field
from typeshed import KT, VT, P
from utils import callable_repr

__all__ = ("Memo",)


@define
class Memo(typing.Generic[P, VT, KT]):
    """Proxy for creating objects via a callable.
    Memoizes results under computed key.

    Parameters
    ----------
    factory: callable creating objects from arguments P.
    key: callable computing keys to store objects under.
    """

    factory: abc.Callable[P, VT] = field(repr=callable_repr)
    """Creates an object from given value."""

    key: abc.Callable[P, KT] = field(repr=callable_repr)
    """Retrieves a key used to store a given object under."""

    mapping: dict[KT, VT] = field(factory=dict, init=False)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        return self.get_or_create(*args, **kwargs)

    def get(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve object stored under a key computed from arguments."""
        key = self.key(*args, **kwargs)
        return self.mapping[key]

    def get_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve or create an object under a key computed from arguments."""
        key = self.key(*args, **kwargs)
        try:
            return self.mapping[key]

        except KeyError:
            obj = self.factory(*args, **kwargs)
            self.mapping[key] = obj
            return obj

    def create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Create and store an object under a key computed from arguments."""
        key = self.key(*args, **kwargs)
        obj = self.factory(*args, **kwargs)
        self.mapping[key] = obj
        return obj
