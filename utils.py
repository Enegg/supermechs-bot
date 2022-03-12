"""
General use python functions
"""
from __future__ import annotations

import random
import re
from collections import Counter
from string import ascii_letters
from typing import Any, Final, Hashable, Iterable, Iterator, TypeVar

SupportsSet = TypeVar("SupportsSet", bound=Hashable)
T = TypeVar("T")


class _MissingSentinel:
    def __eq__(self, other: Any) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."

    def __copy__(self: T) -> T:
        return self

    def __reduce__(self) -> str:
        return "MISSING"

    def __deepcopy__(self: T, _: Any) -> T:
        return self


MISSING: Final[Any] = _MissingSentinel()

def common_items(*items: Iterable[SupportsSet]) -> set[SupportsSet]:
    """Returns intersection of items in iterables"""
    if not items:
        return set()

    iterables = iter(items)
    result = set(next(iterables))

    for item in iterables:
        result.intersection_update(item)

    return result


def search_for(phrase: str, iterable: Iterable[str], *, case_sensitive: bool = False) -> Iterator[str]:
    """Helper func capable of finding a specific string(s) in iterable.
    It is considered a match if every word in phrase appears in the name
    and in the same order. For example, both `burn scop` & `half scop`
    would match name `Half Burn Scope`, but not `burn half scop`.

    Parameters
    -----------
    phrase:
        String of whitespace-separated words.
    iterable:
        Iterable of strings to match against.
    case_sensitive:
        Whether the search should be case sensitive."""
    parts = (phrase if case_sensitive else phrase.lower()).split()

    for name in iterable:
        words = iter((name if case_sensitive else name.lower()).split())

        if all(any(word.startswith(prefix) for word in words) for prefix in parts):
            yield name


def js_format(string: str, /, **kwargs: Any) -> str:
    """Format a JavaScript style string using given keys and values."""
    for key, value in kwargs.items():
        string = re.sub(rf"%{re.escape(key)}%", str(value), string)

    return string


def format_count(it: Iterable[Any], /) -> Iterator[str]:
    return (f'{item}{f" x{count}" * (count > 1)}' for item, count in Counter(filter(None, it)).items())


def random_str(length: int) -> str:
    """Generates a random string of given length from ascii letters"""
    return "".join(random.sample(ascii_letters, length))
