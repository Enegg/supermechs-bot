from __future__ import annotations

import asyncio
import contextlib
import typing as t
from collections import OrderedDict

from attrs import define, field
from typing_extensions import Self, TypeVar

from typeshed import KT, VT, Coro, P, T

__all__ = ("cached_slot_property", "lru_cache")


MappingT = TypeVar("MappingT", bound=t.MutableMapping[t.Hashable, t.Any])


async def async_on_hit(value: VT) -> VT:
    return value


async def async_on_miss(value: Coro[VT], key: KT, callback: t.Callable[[KT, VT], None]) -> VT:
    result = await value
    callback(key, result)
    return result


def sync_on_hit(value: VT) -> VT:
    return value


def sync_on_miss(value: VT, key: KT, callback: t.Callable[[KT, VT], None]) -> VT:
    callback(key, value)
    return value


class cached_slot_property(t.Generic[T]):
    """Descriptor similar to functools.cached_property, but designed for slotted classes.
    Caches the value to an attribute of the same name as the decorated function, prepended with _.
    """

    __slots__ = ("func",)

    def __init__(self, func: t.Callable[[t.Any], T]) -> None:
        self.func = func

    @property
    def slot(self) -> str:
        return "_" + self.func.__name__

    def __repr__(self) -> str:
        return f"<{type(self).__name__} of slot {self.slot!r}>"

    @t.overload
    def __get__(self, obj: None, obj_type: t.Any) -> Self:
        ...

    @t.overload
    def __get__(self, obj: t.Any, obj_type: t.Any) -> T:
        ...

    def __get__(self, obj: t.Any | None, obj_type: t.Any) -> T | Self:
        if obj is None:
            return self

        try:
            return getattr(obj, self.slot)

        except AttributeError:
            value = self.func(obj)
            setattr(obj, self.slot, value)
            return value

    def __delete__(self, obj: t.Any) -> None:
        """Deletes the cached value."""
        try:
            delattr(obj, self.slot)

        except AttributeError:
            pass


class _OrderedSizedDict(OrderedDict[KT, VT]):
    maxsize: int

    def __init__(self, maxsize: int = 128) -> None:
        super().__init__()
        self.maxsize = maxsize

    def __getitem__(self, key: KT, /) -> VT:
        self.move_to_end(key)
        return super().__getitem__(key)

    def __setitem__(self, __key: KT, __value: VT) -> None:
        # precondition: key not in self
        if len(self) >= self.maxsize:
            self.popitem(False)
        return super().__setitem__(__key, __value)


# P is the ParamSpec of the function, VT the type of stored value, and T is the return type
@define
class _Cache(t.Generic[P, VT, T]):
    func: t.Callable[P, VT]
    key_func: t.Callable[P, t.Hashable]
    on_hit: t.Callable[[VT], T] = field(repr=False)
    on_miss: t.Callable[[VT, t.Hashable, t.Callable[[t.Hashable, VT], None]], T] = field(repr=False)
    _cache: t.MutableMapping[t.Hashable, VT] = field()
    hits: int = field(default=0, init=False)
    misses: int = field(default=0, init=False)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        key = self.key_func(*args, **kwargs)

        try:
            value = self._cache[key]

        except KeyError:
            self.misses += 1
            ret = self.on_miss(self.func(*args, **kwargs), key, self._cache.__setitem__)

        else:
            self.hits += 1
            ret = self.on_hit(value)

        return ret

    @property
    def current_size(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        """Clear the cache."""
        self.hits = self.misses = 0
        self._cache.clear()


def default_key(*args: t.Hashable, **kwargs: t.Hashable) -> tuple[t.Hashable, ...]:
    """Takes all arguments and flattens them into a tuple; assumes all arguments are hashable."""
    if not kwargs:
        return args

    flattened = list(args)

    for key_value in kwargs.items():
        flattened += key_value

    return tuple(flattened)


# the overloads do not have the hash_key typed as Callable[P, Hashable]
# as this would prematurely bind P to default_key signature instead of
# the decorated function's signature (in the default hash_key case)
@t.overload
def lru_cache(
    *, maxsize: int | None = 128, hash_key: t.Callable[..., t.Hashable] = ...
) -> t.Callable[[t.Callable[P, Coro[T]]], _Cache[P, T, Coro[T]]]:
    ...


@t.overload
def lru_cache(
    *, maxsize: int | None = 128, hash_key: t.Callable[..., t.Hashable] = ...
) -> t.Callable[[t.Callable[P, T]], _Cache[P, T, T]]:
    ...


def lru_cache(
    *, maxsize: int | None = 128, hash_key: t.Callable[P, t.Hashable] = default_key
) -> t.Callable[[t.Callable[P, T]], _Cache[P, T, T]]:
    """Least-recently-used cache decorator.

    Parameters
    ----------
    maxsize:
        Controls how large the cache can get before entries start getting discarded.
        If None, the size is unlimited.
    hash_key:
        A function used to create a hashable object from arguments the decorated function
        receives. Useful in case not all arguments are hashable.
        The default behavior creates a tuple of positional and keyword arguments.
    """

    def decorator(func: t.Callable[P, T]) -> _Cache[P, T, T]:
        if maxsize is None:
            cache_mapping = dict[t.Hashable, T]()

        else:
            cache_mapping = _OrderedSizedDict(maxsize)

        if asyncio.iscoroutinefunction(func):
            return _Cache(func, hash_key, async_on_hit, async_on_miss, cache_mapping)

        else:
            return _Cache(func, hash_key, sync_on_hit, sync_on_miss, cache_mapping)

    return decorator


@t.overload
@contextlib.contextmanager
def temporal_cache(
    func: t.Callable[P, Coro[T]],
    *,
    maxsize: int | None = 128,
    hash_key: t.Callable[..., t.Hashable] = ...,
) -> t.Iterator[_Cache[P, T, Coro[T]]]:
    ...


@t.overload
@contextlib.contextmanager
def temporal_cache(
    func: t.Callable[P, T],
    *,
    maxsize: int | None = 128,
    hash_key: t.Callable[..., t.Hashable] = ...,
) -> t.Iterator[_Cache[P, T, T]]:
    ...


@contextlib.contextmanager
def temporal_cache(
    func: t.Callable[P, T] | t.Callable[P, Coro[T]],
    *,
    maxsize: int | None = 128,
    hash_key: t.Callable[P, t.Hashable] = default_key,
) -> t.Iterator[_Cache[P, T, Coro[T]]] | t.Iterator[_Cache[P, T, T]]:
    """Context manager which caches function calls by keys computed from the arguments.
    The cache is cleared when leaving the manager's scope.
    """
    if maxsize is None:
        cache_mapping = dict[t.Hashable, t.Any]()

    else:
        cache_mapping = _OrderedSizedDict(maxsize)

    if asyncio.iscoroutinefunction(func):
        cache = _Cache(func, hash_key, async_on_hit, async_on_miss, cache_mapping)

    else:
        cache = _Cache(func, hash_key, sync_on_hit, sync_on_miss, cache_mapping)

    try:
        yield cache

    finally:
        cache.clear()
