from __future__ import annotations

import random
import re
import typing as t
from collections import Counter
from string import ascii_letters
from typing_extensions import Self

SupportsSet = t.TypeVar("SupportsSet", bound=t.Hashable)
T = t.TypeVar("T")


class _MissingSentinel:
    def __eq__(self, other: t.Any) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."

    def __copy__(self: T) -> T:
        return self

    def __reduce__(self) -> str:
        return "MISSING"

    def __deepcopy__(self: T, _: t.Any) -> T:
        return self


MISSING: t.Final[t.Any] = _MissingSentinel()


class ProxyType(type):
    """Metaclass for creating false inheritance objects.
    The point of such action is to avoid repeating code and simply using `__getattr__`
    to do the hard work, while retaining all the static typing benefits."""

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        dict: dict[str, t.Any],
        /,
        **kwargs: t.Any,
    ) -> Self:
        if "__orig_bases__" in dict:
            bases = (t.Generic,)

        else:
            bases = ()

        if "var" in kwargs:
            attribute = kwargs.pop("var")

            def __getattr__(self: Self, name: t.Any) -> t.Any:
                try:
                    return getattr(getattr(self, attribute), name)

                except AttributeError:
                    raise AttributeError(
                        f'{type(self).__name__} object has no attribute "{name}"'
                    ) from None

            dict["__getattr__"] = __getattr__

        return super().__new__(cls, name, bases, dict, **kwargs)


async def no_op(*args: t.Any, **kwargs: t.Any) -> None:
    """Awaitable that does nothing."""
    return


def common_items(*items: t.Iterable[SupportsSet]) -> set[SupportsSet]:
    """Returns intersection of items in iterables"""
    if not items:
        return set()

    iterables = iter(items)
    result = set(next(iterables))

    for item in iterables:
        result.intersection_update(item)

    return result


def search_for(
    phrase: str, iterable: t.Iterable[str], *, case_sensitive: bool = False
) -> t.Iterator[str]:
    """Helper func capable of finding a specific string(s) in iterable.
    It is considered a match if every word in phrase appears in the name
    and in the same order. For example, both `burn scop` & `half scop`
    would match name `Half Burn Scope`, but not `burn half scop`.

    Parameters
    -----------
    phrase:
        String of whitespace-separated words.
    iterable:
        t.Iterable of strings to match against.
    case_sensitive:
        Whether the search should be case sensitive."""
    parts = (phrase if case_sensitive else phrase.lower()).split()

    for name in iterable:
        words = iter((name if case_sensitive else name.lower()).split())

        if all(any(word.startswith(prefix) for word in words) for prefix in parts):
            yield name


def js_format(string: str, /, **kwargs: t.Any) -> str:
    """Format a JavaScript style string using given keys and values."""
    for key, value in kwargs.items():
        string = re.sub(rf"%{re.escape(key)}%", str(value), string)

    return string


def format_count(it: t.Iterable[t.Any], /) -> t.Iterator[str]:
    return (
        f'{item}{f" x{count}" * (count > 1)}' for item, count in Counter(filter(None, it)).items()
    )


def random_str(length: int) -> str:
    """Generates a random string of given length from ascii letters"""
    return "".join(random.sample(ascii_letters, length))


def binary_find_near_index(container: t.Sequence[int], value: int, start: int, end: int) -> int:
    """Binary search for the index of the largest value in container, container[index] <= value"""
    index = (start + end) // 2

    if end - start <= 1:
        return index

    if container[index] > value:
        return binary_find_near_index(container, value, start, index)

    if container[index] < value:
        return binary_find_near_index(container, value, index, end)

    return index
