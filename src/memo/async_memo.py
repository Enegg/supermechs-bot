import typing
from collections import abc
from contextlib import asynccontextmanager

import anyio
from attrs import define, field
from typeshed import KT, VT, P
from utils import callable_repr

__all__ = ("AsyncMemo",)


@define
class AsyncMemo(typing.Generic[P, VT, KT]):
    """Proxy for asynchronously creating objects via a callable.
    Memoizes results under computed key.

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

    mapping: dict[KT, VT] = field(factory=dict, init=False)
    _locks: dict[KT, anyio.Lock] = field(factory=dict, init=False)

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        return await self.get_or_create(*args, **kwargs)

    def get(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve stored object by computing key from arguments."""
        key = self.key(*args, **kwargs)
        return self.mapping[key]

    async def get_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Retrieve or create an object under a key computed from arguments."""
        key = self.key(*args, **kwargs)

        # acquire a lock *before* accessing the value; if key not present
        # this ensures subsequent access will have the value available once
        # the lock is released
        # XXX: what if we don't acquire on first access?
        async with self._acquire_lock(key):
            try:
                return self.mapping[key]

            except KeyError:
                obj = await self.factory(*args, **kwargs)
                self.mapping[key] = obj
                return obj

    async def create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Create and store an object under a key computed from arguments."""
        key = self.key(*args, **kwargs)
        obj = await self.factory(*args, **kwargs)
        self.mapping[key] = obj
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
