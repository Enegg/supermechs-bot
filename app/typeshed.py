import os
import typing as t
import typing_extensions as tex
from collections import abc

T = tex.TypeVar("T", infer_variance=True)
T2 = tex.TypeVar("T2", infer_variance=True)
RetT = tex.TypeVar("RetT", infer_variance=True)
KT = tex.TypeVar("KT", bound=abc.Hashable)
"""Key-type of a mapping."""
VT = tex.TypeVar("VT")
"""Value-type of a mapping."""
P = tex.ParamSpec("P")
"""Parameter specification of a callable."""

twotuple = tuple[T, T]
"""Tuple of two elements of same type."""
XOrTupleXY = T | tuple[T, T2]
"""Type or tuple of two types."""
Factory = abc.Callable[[], T]
"""0-argument callable returning an object of given type."""
LiteralURL: t.TypeAlias = str
"""String representing a URL."""
Pathish: t.TypeAlias = os.PathLike[str] | str
CoroFunc: t.TypeAlias = abc.Callable[..., abc.Coroutine[t.Any, t.Any, T]]
