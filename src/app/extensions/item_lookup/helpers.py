import math

from app.text_utils import Char, acronym_of


def format_float(num: float, decimals: int) -> str:
    num = round(float(num), decimals)

    if num.is_integer():
        return f"{num:.0f}"

    return f"{num:.{decimals}f}"


def try_shorten(name: str, limit: int = 16) -> str:
    if len(name) <= limit:
        return name

    if (acronym := acronym_of(name)) is not None and len(acronym) <= limit:
        return acronym

    return name[: limit - 1] + Char.TRIPLE_DOT


def format_damage(lo: int, hi: int, /) -> str:
    if hi and lo != hi:
        return f"{lo}-{hi}"

    return str(lo)


def mean_and_deviation(a: int | float, b: int | float, /) -> tuple[float, float]:
    mean = (a + b) / 2
    deviation = math.sqrt(((a - mean) ** 2 + (b - mean) ** 2) / 2)
    return mean, deviation


def format_damage_average(lo: int | float, hi: int | float, /, *, decimals: int = 1) -> str:
    mean, deviation = mean_and_deviation(lo, hi)
    dev = deviation / mean * 100.0
    str_mean = format_float(mean, 1)
    str_dev = format_float(dev, decimals)
    return f"{str_mean} ±{str_dev}%"


def format_range(lo: int, hi: int, /) -> str:
    if hi <= 0:
        return f"{lo}+"

    if lo == hi:
        return str(lo)

    return f"{lo}-{hi}"
