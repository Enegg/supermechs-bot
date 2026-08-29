import os
import typing
from collections import abc

if typing.TYPE_CHECKING:
    import _typeshed

type Factory[RetT] = abc.Callable[[], RetT]
"""0-argument callable returning an object of given type."""
type Pathish = os.PathLike[str] | str
"""Path-like or a string representing a path."""
type AsyncFunc[**P, RetT] = abc.Callable[P, abc.Awaitable[RetT]]
"""Function yielding an awaitable."""

type ConvertibleToInt = _typeshed.ConvertibleToInt
"""Value acceptable as an argument to `int()`."""
type ConvertibleToFloat = _typeshed.ConvertibleToFloat
"""Value acceptable as an argument to `float()`."""

type SupportsLt[T] = _typeshed.SupportsDunderLT[T]
"""Type implementing `__lt__`."""
type SupportsGt[T] = _typeshed.SupportsDunderGT[T]
"""Type implementing `__gt__`."""
type SupportsLe[T] = _typeshed.SupportsDunderLE[T]
"""Type implementing `__le__`."""
type SupportsGe[T] = _typeshed.SupportsDunderGE[T]
"""Type implementing `__ge__`."""
