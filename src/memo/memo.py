from collections import abc
from typing import Generic

from attrs import define, field

from memo.typeshed import KT, VT, P
from memo.utils import callable_repr, default_key

__all__ = ("Memo",)


@define
class Memo(Generic[P, VT, KT]):
    """Unbound cache of a factory function.

    - bypass caching via `.factory(...)`.
    - bypass computing a key via `.mapping[...]`.

    Parameters
    ----------
    factory:
        callable creating objects from arguments P.
    key:
        callable computing keys to store objects under.
    """

    factory: abc.Callable[P, VT] = field(repr=callable_repr)
    """The underlying cached function."""

    key: abc.Callable[P, KT] = field(default=default_key, repr=callable_repr)
    """Compute a key for a factory product."""

    mapping: dict[KT, VT] = field(factory=dict, init=False)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        return self.get_or_create(*args, **kwargs)

    def get(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Return the object stored under `key(*args, **kwargs)`."""
        key = self.key(*args, **kwargs)
        return self.mapping[key]

    def get_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Return the object stored under `key(*args, **kwargs)`, or create, store & return a new one."""
        key = self.key(*args, **kwargs)
        try:
            return self.mapping[key]

        except KeyError:
            obj = self.factory(*args, **kwargs)
            self.mapping[key] = obj
            return obj

    def create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Create, store & return an object under `key(*args, **kwargs)`."""
        key = self.key(*args, **kwargs)
        obj = self.factory(*args, **kwargs)
        self.mapping[key] = obj
        return obj
