import typing as t
from contextlib import asynccontextmanager
from types import MappingProxyType

import anyio
from attrs import define, field

from typeshed import KT, VT, Coro, P

from .manager import callable_repr, large_container_repr

__all__ = ("AsyncManager",)


@define
class AsyncManager(t.Generic[P, VT, KT]):
    """Provides means to asynchronously create, store and retrieve objects.

    Note: concurrent calls with same arguments will run the factory only once.

    Parameters
    ----------
    factory: async callable creating objects from arguments P.
    key: callable computing keys to store objects under.
    """
    factory: t.Callable[P, Coro[VT]] = field(repr=callable_repr)
    """Creates an object from given value."""

    key: t.Callable[P, KT] = field(repr=callable_repr)
    """Retrieves a key used to store a given object under."""

    _store: t.MutableMapping[KT, VT] = field(factory=dict, init=False, repr=large_container_repr)
    _locks: t.MutableMapping[KT, anyio.Lock] = field(factory=dict, init=False, repr=large_container_repr)

    @property
    def mapping(self) -> t.Mapping[KT, VT]:
        """Read-only proxy of the underlying mapping."""
        return MappingProxyType(self._store)

    def __contains__(self, key: KT, /) -> bool:
        return key in self._store

    async def lookup_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve stored or create an object from given value."""
        key = self.key(*args, **kwargs)

        # we use a lock so any concurrent calls with arguments that compute the same key
        # result in running the factory only once
        async with self._acquire_lock(key):
            try:
                return self._store[key]

            except KeyError:
                obj = await self.factory(*args, **kwargs)
                self._store[key] = obj
                return obj

    @asynccontextmanager
    async def _acquire_lock(self, key: KT, /) -> t.AsyncIterator[None]:
        lock = self._locks.get(key)

        if owner := lock is None:
            lock = self._locks[key] = anyio.Lock()

        try:
            async with lock:
                yield

        finally:
            if owner:
                del self._locks[key]
