import inspect
import pathlib
import reprlib
from collections import abc

import cattrs
import rtoml

from app.typeshed import Pathish, T

limited_repr = reprlib.Repr()
limited_repr.maxdict = 20


def attrs_from_path(
    path: Pathish, cls: type[T], conv: cattrs.Converter = cattrs.global_converter
) -> T:
    path = pathlib.Path(path)
    return conv.structure_attrs_fromdict(rtoml.load(path), cls)


def callable_repr(func: abc.Callable[..., object], /) -> str:
    """Returns the signature of a callable."""
    signature = inspect.signature(func)
    return f"{func.__name__}{signature}"
