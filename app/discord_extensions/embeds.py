import re
import typing

import disnake

__all__ = ("EmbedColorType", "debug_footer", "sanitize_filename")

EmbedColorType: typing.TypeAlias = disnake.Colour | int


def debug_footer(embed: disnake.Embed, /, *, replace: bool = False) -> None:
    """Adds a footer with raw urls of various embed fields, and total characters."""

    if replace:
        embed.remove_footer()

    parts: list[str] = ["Debug:", f"Size: {len(embed)}"]

    if existing_footer := embed.footer.text:
        parts.insert(0, existing_footer)

    if (url := embed.image.url) is not None and url.startswith("attachment://"):
        parts.append(f"Image: {url}")

    if (url := embed.thumbnail.url) is not None and url.startswith("attachment://"):
        parts.append(f"Thumb: {url}")

    embed.set_footer(text="\n".join(parts))


_antipattern = re.compile(r"[^\w.-]")


def sanitize_filename(filename: str, /) -> str:
    """Ensure filename conforms to discord attachment restrictions."""
    return _antipattern.sub("_", filename).lower()
