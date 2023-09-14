import re
import typing as t

from typeshed import twotuple

_pattern = re.compile(r"\.(\d+)")


def truncate_float(num: float, digits: int) -> tuple[float, int]:
    num = round(num, digits)
    if num.is_integer():
        return num, 0
    return num, digits


def fmt_float(value: float, spec: str) -> str:
    """Formats a float to at most n digits after decimal point."""

    if (match := _pattern.search(spec)) is not None:
        value, prec = truncate_float(value, int(match[1]))
        start, end = match.span()

        return format(value, f"{spec[:start]}.{prec}{spec[end:]}")

    return format(value, spec)


def try_shorten(name: str) -> str:
    if len(name) < 16:
        return name

    return "".join(s for s in name if s.isupper())


@t.overload
def compare_numbers(x: int, y: int, lower_is_better: bool = False) -> twotuple[int]:
    ...


@t.overload
def compare_numbers(x: float, y: float, lower_is_better: bool = False) -> twotuple[float]:
    ...


def compare_numbers(x: float, y: float, lower_is_better: bool = False) -> twotuple[float]:
    return (x - y, 0) if lower_is_better ^ (x > y) else (0, y - x)


def wrap_nicely(size: int, max: int) -> int:
    """Returns the size for a slice of a sequence of given size,
    distributed evenly according to max.
    """
    if size < max:
        return max
    for n in range(max, 2, -1):
        rem = size % n
        if rem == 0 or rem >= n - 1:
            return n
    return max
