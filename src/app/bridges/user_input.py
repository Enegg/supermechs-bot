from enum import Enum

__all__ = ("StringLimits", "sanitize_string")


class StringLimits(int, Enum):
    """Arbitrary length limits of various kinds of strings."""

    names = 32
    description = 100


def sanitize_string(string: str, /, max_length: int = StringLimits.names) -> str:
    """Sanitize user-originating strings."""
    return "".join(char if char.isascii() else "_" for char in string)[:max_length]
