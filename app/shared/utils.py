from __future__ import annotations

import typing as t

from typing_extensions import Self

from typeshed import T

__all__ = ("proxied", "mutable_proxy", "wrap_bytes", "ReprMixin")


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


def wrap_bytes(bytes: int) -> tuple[int, str]:
    """Convert absolute byte size to suffixed unit."""
    units = ("B", "KiB", "MiB", "GiB", "TiB")

    if bytes == 0:
        return 0, "B"

    exp = (bytes.bit_length() - 1) // 10
    bytes >>= 10 * exp

    try:
        return bytes, units[exp]

    except IndexError:
        return bytes, "?iB"


class ReprMixin:
    """Class for programmatic __repr__ creation."""

    __repr_attributes__: t.Iterable[str]
    __slots__ = ()

    def __repr__(self) -> str:
        attrs = " ".join(f"{key}={getattr(self, key)!r}" for key in self.__repr_attributes__)
        return f"<{type(self).__name__} {attrs} at 0x{id(self):016X}>"
