from disnake import File
import io

__all__ = ("text_to_file",)


def text_to_file(text: str, /, filename: str, *, spoiler: bool = False) -> File:
    """Turns a string into a discord text file."""

    bio = io.BytesIO(text.encode())
    return File(bio, filename, spoiler=spoiler)
