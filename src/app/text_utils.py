import enum


class Char(enum.StrEnum):
    """Non-keyboard characters."""

    TRIPLE_DOT = "…"
    """Single character form of `...`."""
    BLANK = "\u2800"
    """Braille blank. Useful in places discord truncates normal space."""


def acronym_of(name: str, /) -> str | None:
    """Return an acronym of a name, or None if one cannot be made.

    The acronym consists of capital letters in the name;
    there need to be at least two capital letters, and one lowercase.
    """
    if not name:
        return None
    if name[0].isupper() and name[1:].islower():
        # don't bother with single capital letters
        return None
    # filter out already-acronym names, like "EMP"
    if name.isupper():
        return None
    # names which are partially acronyms are fine
    return "".join(filter(str.isupper, name)).lower()
