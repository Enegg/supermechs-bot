"""Functions that can find use outside of discord.py scope"""
from __future__ import annotations

import random
from collections import deque
from string import ascii_letters
from typing import Any, AnyStr, Hashable, Iterable, Iterator, TypeVar

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


def search_for(phrase: str, iterable: Iterable[str], *, case_sensitive: bool=False) -> Iterator[str]:
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


def split_to_fields(all_items: Iterable[AnyStr], offset: int=1, field_limit: int | tuple[int, int]=2048) -> list[list[AnyStr]]:
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

    current_field: list[AnyStr] = []
    fields_list: list[list[AnyStr]] = [current_field]
    sub_len = 0

    for item in all_items:
        if fields_list and extra_limit:
            main_limit = extra_limit

        if sub_len + len(item) > main_limit:
            current_field = []
            fields_list.append(current_field)
            sub_len = 0

        current_field.append(item)
        sub_len += len(item) + offset

    return fields_list


def js_format(string: str, **kwargs: Any) -> str:
    for key, value in kwargs.items():
        string = string.replace(f'%{key}%', str(value))

    return string


def random_str(length: int) -> str:
    """Generates a random string of given length from ascii letters"""
    return ''.join(random.sample(ascii_letters, length))


class StringIterator(Iterator[str]):
    def __init__(self, string: str) -> None:
        self._unread: deque[str] = deque()
        self.iter = iter(string)
        self.last: str | None = None

    def __next__(self) -> str:
        if self._unread:
            self.last = self._unread.popleft()

        else:
            self.last = next(self.iter)

        return self.last

    def unread(self) -> None:
        if self.last is None:
            return

        self._unread.appendleft(self.last)
        self.last = None


def parse_kwargs(args: Iterable[str]):
    """Takes command arguments as an input and tries to match them as key item pairs"""
    # keyword <whitespace> (optional operator: ":" "=" "!=" "≠" "<=" "≤" ">=" "≥" "<" ">") <whitespace> (optional value), ...
    # keyword: TYPE, ELEMENT, TIER, NAME, STAT

    # start with finding operator - they restrict possible keywords, so it narrows searching
    chars = {'=', '<', '>', '!', ':', '≠', '≤', '≥'}

    parsed_args = []

    for arg in args:
        keyword = operator = value = ''
        str_parts = ['']

        space = False
        it = StringIterator(arg)

        for c in it:
            if c == ' ':
                space = True
                continue

            if c in chars:
                if not keyword:
                    keyword = ' '.join(str_parts)
                    str_parts = ['']

                if operator and operator != ':':
                    raise ValueError('Second operator found')

                n = next(it, None)

                if n is None:
                    raise ValueError('End of string while parsing operator')

                if n == '=':
                    try:
                        # !=, ==, <=, >=
                        # c = concat_op(c)
                        pass

                    except KeyError:
                        raise ValueError(f'Invalid operator: "{c}="')

                else:
                    it.unread()

                operator = c
                space = False  # whatever the value, set to False
                continue

            # either keyword or value
            if space:
                str_parts.append('')
                space = False

            str_parts[-1] += c

        if not keyword:
            keyword = ' '.join(str_parts).strip()

        else:
            value = ' '.join(str_parts).strip()

        parsed_args.append((keyword, operator, value))

    return parsed_args
