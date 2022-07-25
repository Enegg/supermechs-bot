import os
import random
import re
import typing as t
from collections import Counter
from string import ascii_letters

from typing_extensions import Self

SupportsSet = t.TypeVar("SupportsSet", bound=t.Hashable)
T = t.TypeVar("T")
T_CO = t.TypeVar("T_CO", covariant=True)


class SupportsComparison(t.Protocol[T_CO]):
    def __gt__(self, other: t.Any, /) -> bool:
        ...

    def __lt__(self, other: t.Any, /) -> bool:
        ...


class _MissingSentinel:
    def __eq__(self, _: t.Any) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "..."

    def __hash__(self) -> int:
        return hash((None,))

    def __copy__(self) -> Self:
        return self

    def __reduce__(self) -> str:
        return "MISSING"

    def __deepcopy__(self, _: t.Any) -> Self:
        return self


MISSING: t.Final[t.Any] = _MissingSentinel()
Proxied = t.Annotated[T, MISSING]


def proxy(slot: str, /) -> t.Callable[[type[T]], type[T]]:
    """Creates a __getattr__ for given slot and removes Proxied fields from object"""

    def wrap(cls: type[T]) -> type[T]:
        for ann, tp in tuple(cls.__annotations__.items()):
            match t.get_origin(tp), t.get_args(tp):
                case t.Annotated, (_, _MissingSentinel()):
                    del cls.__annotations__[ann]
                    delattr(cls, ann)

                case t.ClassVar, (t.Annotated as tp,) if t.get_args(tp)[1] is MISSING:
                    del cls.__annotations__[ann]

                case _:
                    pass

        def __getattr__(self: T, name: str) -> t.Any:
            try:
                return getattr(getattr(self, slot), name)

            except AttributeError:
                raise AttributeError(
                    f'{type(self).__name__} object has no attribute "{name}"'
                ) from None

        cls.__getattr__ = __getattr__  # type: ignore
        return cls

    return wrap


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


def unique_id() -> str:
    """Creates an unique id"""
    return os.urandom(16).hex()


def find_near_index(
    container: t.Sequence[SupportsComparison[T_CO]],
    value: SupportsComparison[T_CO],
    start: int,
    end: int,
) -> int:
    """Binary search for the index of the largest value in a sequence, container[index] <= value

    Usable only on sorted sequences
    """
    index = (start + end) // 2

    if end - start <= 1:
        return index

    # tail recursion even though python does not optimize for it
    if container[index] > value:
        return find_near_index(container, value, start, index)

    if container[index] < value:
        return find_near_index(container, value, index, end)

    return index


KT = t.TypeVar("KT")
VT = t.TypeVar("VT")


def dict_items_as(value_type: type[VT], obj: t.Mapping[KT, t.Any]) -> t.ItemsView[KT, VT]:
    """Helper function to aid iterating over TypedDict.items()"""
    return obj.items()
