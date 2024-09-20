import typing
from collections import abc
from contextlib import asynccontextmanager

import anyio
from attrs import define, field

from memo.typeshed import KT, VT, P
from memo.utils import callable_repr

__all__ = ("AsyncMemo",)


@define
class AsyncMemo(typing.Generic[P, VT, KT]):
    """Unbound cache of an async factory function.

    - to bypass caching, use the `.factory` callable directly.
    - to bypass computing a key, use the `.mapping` directly.
    - safe for async concurrency.

    Parameters
    ----------
    factory:
        async callable creating objects from arguments P.
    key:
        callable computing keys to store objects under.
    """

    factory: abc.Callable[P, abc.Awaitable[VT]] = field(repr=callable_repr)
    """The underlying cached function."""

    key: abc.Callable[P, KT] = field(repr=callable_repr)
    """Compute a key for a factory product."""

    mapping: dict[KT, VT] = field(factory=dict, init=False)
    _locks: dict[KT, anyio.Lock] = field(factory=dict, init=False)

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        return await self.get_or_create(*args, **kwargs)

    def get(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Return the object stored under `key(*args, **kwargs)`."""
        key = self.key(*args, **kwargs)
        return self.mapping[key]

    async def get_or_create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Return the object stored under `key(*args, **kwargs)`, or create & store a new one."""
        key = self.key(*args, **kwargs)

        # except for the very first caller, the lock ensures the value is inserted into the mapping
        async with self._acquire_lock(key):
            try:
                return self.mapping[key]

            except KeyError:
                obj = await self.factory(*args, **kwargs)
                self.mapping[key] = obj
                return obj

    async def create(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        """Create & store an object under `key(*args, **kwargs)`, then return it."""
        key = self.key(*args, **kwargs)
        obj = await self.factory(*args, **kwargs)
        self.mapping[key] = obj
        return obj

    @asynccontextmanager
    async def _acquire_lock(self, key: KT, /) -> abc.AsyncIterator[None]:
        """Acquire a lock under key, such that concurrent calls run the factory only once."""
        lock = self._locks.get(key)

        if owner := lock is None:
            lock = self._locks[key] = anyio.Lock()

        try:
            async with lock:
                yield

        finally:
            if owner:
                del self._locks[key]
