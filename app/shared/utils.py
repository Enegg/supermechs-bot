from __future__ import annotations

import typing as t

from typing_extensions import Self, TypeVar

T = TypeVar("T")


class cached_slot_property(t.Generic[T]):
    """Descriptor similar to functools.cached_property, but designed for slotted classes.
    It works by caching the value to an attribute of the same name as the descriptor
    is assigned to, prepended with _.
    """
    __slots__ = ("func", "slot")

    def __init__(self, func: t.Callable[[t.Any], T]) -> None:
        self.func = func

    def __set_name__(self, owner: t.Any, name: str) -> None:
        self.slot = "_" + name

    def __repr__(self) -> str:
        return f"<{type(self).__name__} of slot {getattr(self, 'attr', '<unassigned>')}>"

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
