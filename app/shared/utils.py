from __future__ import annotations

import typing as t

from typing_extensions import Self

from typeshed import T


class cached_slot_property(t.Generic[T]):
    """Descriptor similar to functools.cached_property, but designed for slotted classes.
    It works by caching the value to an attribute of the same name as the descriptor
    is assigned to, prepended with _.
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


class proxied(t.Generic[T]):
    """Property proxying an attribute of another slot."""
    def __init__(self, proxied: str, /) -> None:
        self.proxied = proxied

    def __set_name__(self, obj: t.Any, name: str) -> None:
        self.name = name

    @t.overload
    def __get__(self, obj: None, obj_type: t.Any) -> Self:
        ...

    @t.overload
    def __get__(self, obj: t.Any, obj_type: t.Any) -> T:
        ...

    def __get__(self, obj: t.Any | None, obj_type: t.Any) -> T | Self:
        if obj is None:
            return self

        return getattr(getattr(obj, self.proxied), self.name)


class mutable_proxy(proxied[T]):
    """Property proxying getting and setting an attribute of another slot."""
    def __set__(self, obj: t.Any, value: T) -> None:
        setattr(getattr(obj, self.proxied), self.name, value)
