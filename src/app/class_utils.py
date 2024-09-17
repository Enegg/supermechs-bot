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
    cls: type[T], path: Pathish, conv: cattrs.Converter = cattrs.global_converter
) -> T:
    """Read a .toml file under given path and parse it into a dataclass instance."""
    path = pathlib.Path(path)
    return conv.structure(rtoml.load(path), cls)


def callable_repr(func: abc.Callable[..., object], /) -> str:
    """Return the signature of a callable."""
    signature = inspect.signature(func)
    return f"{func.__name__}{signature}"
