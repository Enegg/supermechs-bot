import io
import re

import disnake

__all__ = ("sanitize_filename", "text_to_file")


def text_to_file(text: str, /, filename: str, *, spoiler: bool = False) -> disnake.File:
    """Turns a string into a discord text file."""

    bio = io.BytesIO(text.encode())
    return disnake.File(bio, filename, spoiler=spoiler)


_antipattern = re.compile(r"[^\w.-]")


def sanitize_filename(filename: str, /) -> str:
    """Ensure filename conforms to discord attachment restrictions."""
    return _antipattern.sub("_", filename).lower()
