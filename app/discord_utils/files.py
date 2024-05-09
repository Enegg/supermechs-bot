import io

import disnake

__all__ = ("text_to_file",)


def text_to_file(text: str, /, filename: str, *, spoiler: bool = False) -> disnake.File:
    """Turns a string into a discord text file."""

    bio = io.BytesIO(text.encode())
    return disnake.File(bio, filename, spoiler=spoiler)
