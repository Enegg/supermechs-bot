import os
from collections import abc

type Factory[RetT] = abc.Callable[[], RetT]
"""0-argument callable returning an object of given type."""
type Pathish = os.PathLike[str] | str
"""Path-like or a string representing a path."""
type AsyncFunc[**P, RetT] = abc.Callable[P, abc.Awaitable[RetT]]
"""Function yielding an awaitable."""
