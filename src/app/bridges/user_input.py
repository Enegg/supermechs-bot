from enum import Enum

from disnake.ext import commands

__all__ = ("StringLimits", "sanitize_string", "validate_string")


class StringLimits(int, Enum):
    """Arbitrary length limits of various kinds of strings."""

    names = 32
    description = 100


def validate_string(string: str, /, max_length: int = StringLimits.names) -> None:
    """Validate string length and whether it is all ASCII."""
    if len(string) > max_length:
        msg = "String is too long"
        raise commands.UserInputError(msg)

    if not string.isascii():
        msg = "Non-ASCII characters found"
        raise commands.UserInputError(msg)


def sanitize_string(string: str, /, max_length: int = StringLimits.names) -> str:
    """Sanitize user-originating strings."""
    return "".join(char if char.isascii() else "_" for char in string)[:max_length]
