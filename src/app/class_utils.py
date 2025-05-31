import pathlib
import reprlib
from collections import ChainMap, abc
from typing import Any, Self

import attrs
import cattrs
import rtoml

from app.cattrs_utils import CONVERTER
from app.typeshed import Pathish

_repr_obj = reprlib.Repr()
_repr_obj.maxdict = 20
limited_repr = _repr_obj.repr


def chain_maps[KT, VT](*maps: abc.Mapping[KT, VT]) -> abc.Mapping[KT, VT]:
    # ChainMap expects MutableMappings, but we only care about its immutable API
    return ChainMap(*maps)  # pyright: ignore[reportArgumentType]


@attrs.define
class MappingParser:
    mappings: list[abc.Mapping[str, Any]]
    conv: cattrs.Converter

    def __init__(
        self, *mappings: abc.Mapping[str, Any], conv: cattrs.Converter = CONVERTER
    ) -> None:
        self.mappings = list(mappings)
        self.conv = conv

    def structure[T](self, cls: type[T], *key_path: str) -> T:
        config: abc.Mapping[str, Any] = chain_maps(*self.mappings)

        for key in key_path:
            config = config[key]

        return self.conv.structure(config, cls)

    @classmethod
    def from_path(
        cls,
        path: Pathish,
        loader: abc.Callable[[str], abc.Mapping[str, Any]] = rtoml.loads,
    ) -> Self:
        path = pathlib.Path(path)
        config = loader(path.read_text(encoding="utf-8"))
        return cls(config)


@attrs.define
class default[T]:  # noqa: N801
    """Class property initializing a default instance on access."""

    f: abc.Callable[[], T]
    name: str = attrs.field(init=False)

    def __set_name__(self, cls: type[T], name: str) -> None:
        self.name = name

    def __get__(self, _: None, cls: type[T], /) -> T:
        inst = self.f()
        setattr(cls, self.name, inst)
        return inst

    @staticmethod
    def mutable[U](f: abc.Callable[[], U], /) -> "default[U] | U":
        """Mark the type of decorated name as `default[T] | T`, allowing for direct write."""
        return default(f)
