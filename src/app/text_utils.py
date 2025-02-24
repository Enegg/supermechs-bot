import enum


class Char(str, enum.Enum):
    """Non-keyboard characters."""

    TRIPLE_DOT = "…"
    """Single character form of `...`."""
    BLANK = "\u2800"
    """Braille blank. Useful in places discord truncates normal space."""


class StringLimits(enum.IntEnum):
    """Arbitrary length limits of various kinds of strings."""

    names = 32
    description = 100


def sanitize_string(string: str, /, max_length: int = StringLimits.names) -> str:
    """Sanitize user-originating strings."""
    return "".join(char if char.isascii() else "_" for char in string)[:max_length]
