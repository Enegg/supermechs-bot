import typing
from collections import abc
from contextlib import asynccontextmanager
from types import MappingProxyType

import anyio
from attrs import define, field

from typeshed import KT, VT, P

from .manager import callable_repr

from supermechs.utils import large_mapping_repr

__all__ = ("AsyncManager",)


@define
class AsyncManager(typing.Generic[P, VT, KT], abc.Mapping[KT, VT]):
    """Provides means to asynchronously create, store and retrieve objects.

    Note: concurrent calls with same arguments will run the factory only once.

    Parameters
    ----------
    factory: async callable creating objects from arguments P.
    key: callable computing keys to store objects under.
    """

    factory: abc.Callable[P, abc.Awaitable[VT]] = field(repr=callable_repr)
    """Creates an object from given value."""

    key: abc.Callable[P, KT] = field(repr=callable_repr)
    """Retrieves a key used to store a given object under."""

    _store: dict[KT, VT] = field(factory=dict, init=False, repr=large_mapping_repr)
    _locks: dict[KT, anyio.Lock] = field(factory=dict, init=False, repr=large_mapping_repr)

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

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        return await self.get_or_create(*args, **kwargs)

    async def get_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve stored or create an object from given value."""
        key = self.key(*args, **kwargs)

        # acquire a lock *before* accessing the value; if key not present
        # this ensures subsequent access will have the value available once
        # the lock is released
        # XXX: what if we don't acquire on first access?
        async with self._acquire_lock(key):
            try:
                return self._store[key]

            except KeyError:
                obj = await self.factory(*args, **kwargs)
                self._store[key] = obj
                return obj

    async def create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Create and store an object from given value."""
        key = self.key(*args, **kwargs)
        obj = await self.factory(*args, **kwargs)
        self._store[key] = obj
        return obj

    @asynccontextmanager
    async def _acquire_lock(self, key: KT, /) -> abc.AsyncIterator[None]:
        lock = self._locks.get(key)

        if owner := lock is None:
            lock = self._locks[key] = anyio.Lock()

        try:
            async with lock:
                yield

        finally:
            if owner:
                del self._locks[key]
