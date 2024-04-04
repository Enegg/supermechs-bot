from enum import Enum

from disnake.ext import commands


class StringLimits(int, Enum):
    """Arbitrary length limits of various kinds of strings."""

    names = 32
    description = 100


def sanitize_string(
    string: str, /, max_length: int = StringLimits.names, *, strict: bool = False
) -> str:
    """Utility to sanitize user-originating string data."""

    if strict:
        if len(string) > max_length:
            msg = "String is too long"
            raise commands.UserInputError(msg)

        if any(not char.isascii() for char in string):
            msg = "Non-ASCII characters found"
            raise commands.UserInputError(msg)

    chars = (char if char.isascii() else "_" for char in string)

    return "".join(chars)[:max_length]
