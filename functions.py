"""Functions that can find use outside of discord.py scope"""
from __future__ import annotations


import re
from typing import *  # type: ignore


SupportsSet = TypeVar('SupportsSet', bound=Hashable)

def common_items(*items: Iterable[SupportsSet]) -> set[SupportsSet]:
    """Returns intersection of items in iterables"""
    if not items:
        return set()

    iterables = iter(items)
    result = set(next(iterables))

    for item in iterables:
        result.intersection_update(item)

    return result


def search_for(phrase: str, iterable: Iterable[str]) -> list[str]:
    """Helper func capable of finding a specific string following a name rule,
    like "_burn_" in "Half Burnt Scope\""""
    if not iterable:
        return iterable

    phrase = r'\b' + re.sub('[^a-z ]+', '', phrase).replace(' ', '.* ')
    return [i for i in iterable if re.search(phrase, i.lower())]


def split_to_fields(all_items: list[AnyStr], offset: int=1, field_limit: int | tuple[int, int]=2048) -> list[list[AnyStr]]:
    """Splits a list of strings into multiple lists (to-be embed fields) so that they stay under character limit.
    Field_limit should be an int or a tuple of two ints;
    in the latter case the first int will be applied to the first field, and the second to any following field."""
    if isinstance(field_limit, tuple):
        if len(field_limit) != 2:
            raise ValueError(f'Expected 2 integers, got {len(field_limit)}')

        main_limit, extra_limit = field_limit

        if not type(main_limit) is type(extra_limit) is int:
            raise TypeError(f'Expected 2 integers, got {type(main_limit)}, {type(extra_limit)}')

    else:
        main_limit, extra_limit = field_limit, 0

    slices_list: list[list[AnyStr]] = []
    last = 0
    sub_len = 0

    for i, item in enumerate(all_items):
        if slices_list and extra_limit:
            main_limit = extra_limit

        if sub_len + len(item) > main_limit:
            slices_list.append(all_items[last:i])
            sub_len, last = 0, i

        sub_len += len(item) + offset

    else:
        slices_list.append(all_items[last:])

    return slices_list


def filter_flags(flag_set: set[SupportsSet], items: Iterable[SupportsSet]) -> tuple[set[SupportsSet], list[SupportsSet]]:
    _flags = flag_set.intersection(items)
    return _flags, [s for s in items if s not in _flags]
