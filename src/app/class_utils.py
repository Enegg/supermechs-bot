import pathlib
import reprlib
from collections import ChainMap, abc
from typing import Any, Self

import attrs
import cattrs
import msgspec
import rtoml
from monads.option import Null, Option, Some

from app.cattrs_utils import CONVERTER
from app.typeshed import Pathish

_repr_obj = reprlib.Repr()
_repr_obj.maxdict = 20
limited_repr = _repr_obj.repr


def chain_maps[KT, VT](maps: abc.Sequence[abc.Mapping[KT, VT]], /) -> abc.Mapping[KT, VT]:
    if len(maps) == 0:
        return {}
    if len(maps) == 1:
        return maps[0]
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
        config: abc.Mapping[str, Any] = chain_maps(self.mappings)

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


def unset_to_option[T](v: T | msgspec.UnsetType, /) -> Option[T]:
    """Return `Null.null` for `msgspec.UNSET`, `Some(T)` otherwise."""
    return Null.null if v is msgspec.UNSET else Some(v)
