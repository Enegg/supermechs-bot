import random
import re
import typing as t
from collections import Counter
from string import ascii_letters

from typing_extensions import Self


class _MissingSentinel:
    def __eq__(self, _: t.Any) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."

    def __hash__(self) -> int:
        return hash((type(self),))

    def __copy__(self) -> Self:
        return self

    def __reduce__(self) -> str:
        return "MISSING"

    def __deepcopy__(self, _: t.Any) -> Self:
        return self


MISSING: t.Final[t.Any] = _MissingSentinel()


def search_for(
    phrase: str, iterable: t.Iterable[str], *, case_sensitive: bool = False
) -> t.Iterator[str]:
    """
    Helper func capable of finding a specific string(s) in iterable.
    It is considered a match if every word in phrase appears in the name
    and in the same order. For example, both `burn scop` & `half scop`
    would match name `Half Burn Scope`, but not `burn half scop`.

    Parameters
    ----------
    phrase:
        String of whitespace-separated words.
    iterable:
        Iterable of strings to match against.
    case_sensitive:
        Whether the search should be case sensitive.
    """
    parts = (phrase if case_sensitive else phrase.lower()).split()

    for name in iterable:
        words = iter((name if case_sensitive else name.lower()).split())

        if all(any(word.startswith(prefix) for word in words) for prefix in parts):
            yield name


def js_format(string: str, /, **kwargs: t.Any) -> str:
    """Format a JavaScript style string using given keys and values."""
    # XXX: this will do as many passes as there are kwargs, maybe concatenate the pattern?
    for key, value in kwargs.items():
        string = re.sub(rf"%{re.escape(key)}%", str(value), string)

    return string


def format_count(it: t.Iterable[t.Any], /) -> t.Iterator[str]:
    return (
        f'{item}{f" x{count}" * (count > 1)}' for item, count in Counter(filter(None, it)).items()
    )


def random_str(length: int, /) -> str:
    """Generates a random string of given length from ascii letters."""
    return "".join(random.sample(ascii_letters, length))


def truncate_name(input: str, length: int = 32) -> str:
    return input[:length]
