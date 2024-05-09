import re
import typing

import disnake

__all__ = ("EmbedColorType", "sanitize_filename")

EmbedColorType: typing.TypeAlias = disnake.Colour | int

_antipattern = re.compile(r"[^\w.-]")


def sanitize_filename(filename: str, /) -> str:
    """Ensure filename conforms to discord attachment restrictions."""
    return _antipattern.sub("_", filename).lower()
