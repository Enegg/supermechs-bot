from __future__ import annotations

import contextlib
import typing as t
from collections import OrderedDict

from attrs import define, field
from typing_extensions import Self

from typeshed import VT, P, T

__all__ = ("cached_slot_property", "lru_cache")


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


@define
class _Cache(t.Generic[P, VT]):
    func: t.Callable[P, VT]
    key_func: t.Callable[P, t.Hashable]
    hits: int = field(default=0, init=False)
    misses: int = field(default=0, init=False)
    _cache: t.MutableMapping[t.Hashable, VT] = field(factory=dict, init=False)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        key = self.key_func(*args, **kwargs)

        try:
            value = self._cache[key]

        except KeyError:
            self.misses += 1
            self._cache[key] = value = self.func(*args, **kwargs)

        else:
            self.hits += 1

        return value

    @property
    def current_size(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        """Clear the cache."""
        self.hits = self.misses = 0
        self._cache.clear()


@define
class _SizedCache(t.Generic[P, VT]):
    func: t.Callable[P, VT]
    key_func: t.Callable[P, t.Hashable]
    max_size: int = 128
    hits: int = field(default=0, init=False)
    misses: int = field(default=0, init=False)
    _cache: OrderedDict[t.Hashable, VT] = field(factory=OrderedDict, init=False)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> VT:
        key = self.key_func(*args, **kwargs)

        try:
            value = self._cache[key]

        except KeyError:
            self.misses += 1
            value = self.func(*args, **kwargs)

            if len(self._cache) >= self.max_size:
                self._cache.popitem(False)

            self._cache[key] = value

        else:
            self.hits += 1
            self._cache.move_to_end(key)

        return value

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
    *, maxsize: int = 128, hash_key: t.Callable[..., t.Hashable] = ...
) -> t.Callable[[t.Callable[P, T]], _SizedCache[P, T]]:
    ...


@t.overload
def lru_cache(
    *, maxsize: None, hash_key: t.Callable[..., t.Hashable] = ...
) -> t.Callable[[t.Callable[P, T]], _Cache[P, T]]:
    ...


def lru_cache(
    *, maxsize: int | None = 128, hash_key: t.Callable[P, t.Hashable] = default_key
) -> t.Callable[[t.Callable[P, T]], _Cache[P, T] | _SizedCache[P, T]]:
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

    def decorator(func: t.Callable[P, T]) -> _Cache[P, T] | _SizedCache[P, T]:
        if maxsize is None:
            return _Cache(func, hash_key)

        return _SizedCache(func, hash_key, maxsize)

    return decorator


@t.overload
@contextlib.contextmanager
def temporal_cache(
    func: t.Callable[P, T], *, maxsize: int = 128, hash_key: t.Callable[..., t.Hashable] = ...
) -> t.Iterator[_SizedCache[P, T]]:
    ...


@t.overload
@contextlib.contextmanager
def temporal_cache(
    func: t.Callable[P, T], *, maxsize: None, hash_key: t.Callable[..., t.Hashable] = ...
) -> t.Iterator[_Cache[P, T]]:
    ...


@contextlib.contextmanager
def temporal_cache(
    func: t.Callable[P, T],
    *,
    maxsize: int | None = 128,
    hash_key: t.Callable[P, t.Hashable] = default_key,
) -> t.Iterator[_Cache[P, T] | _SizedCache[P, T]]:
    """Context manager which caches function calls by keys computed from the arguments.
    The cache is cleared when leaving the manager's scope.
    """
    if maxsize is None:
        cache = _Cache(func, hash_key)

    else:
        cache = _SizedCache(func, hash_key, maxsize)

    try:
        yield cache

    finally:
        cache.clear()
