import pathlib
import reprlib
from collections import ChainMap, abc
from typing import Any, NewType, Self

import attrs
import cattrs
import rtoml

from app.typeshed import Pathish
from app.utils import atoi_bin

_repr_obj = reprlib.Repr()
_repr_obj.maxdict = 20
limited_repr = _repr_obj.repr

ByteSize = NewType("ByteSize", int)


@cattrs.global_converter.register_structure_hook
def _structure_binary_int(value: Any, _: object) -> ByteSize:
    try:
        return ByteSize(int(value))

    except (ValueError, TypeError):
        pass

    if not isinstance(value, str):
        msg = f"Invalid type: {value!r}"
        raise TypeError(msg) from None

    return ByteSize(atoi_bin(value))


del _structure_binary_int


@attrs.define
class MappingParser:
    mappings: list[abc.Mapping[str, Any]]
    conv: cattrs.Converter = cattrs.global_converter

    def __init__(
        self, *mappings: abc.Mapping[str, Any], conv: cattrs.Converter = cattrs.global_converter
    ) -> None:
        self.mappings = list(mappings)
        self.conv = conv

    def structure[T](self, cls: type[T], *key_path: str) -> T:
        # ChainMap is mutable and expects MutableMappings, but we don't care about mutation
        config: abc.Mapping[str, Any] = ChainMap[str, Any](*self.mappings)  # pyright: ignore[reportArgumentType]

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
