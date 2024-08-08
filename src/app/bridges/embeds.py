import io
import pathlib
import random
from typing import TYPE_CHECKING

from discord import sanitize_filename

from app import i18n

import disnake

if TYPE_CHECKING:
    from PIL.Image import Image

__all__ = ("embed_image", "sikrit_footer")


def embed_image(image: "Image", filename: str, format: str = "png") -> tuple[str, disnake.File]:
    """Creates a File and returns it with an attachment url."""

    filename = sanitize_filename(filename)
    filename = str(pathlib.PurePath(filename).with_suffix(f".{format}"))
    fp = io.BytesIO()
    try:
        image.save(fp, format=format)

    except KeyError:
        # thrown by PIL's format lookup table
        msg = f"Invalid image format: {format!r}"
        raise ValueError(msg) from None

    fp.seek(0)
    return f"attachment://{filename}", disnake.File(fp, filename)


def sikrit_footer(embed: disnake.Embed, /, locale: disnake.Locale, chance: float = 0.01) -> None:
    """Randomly set a "tip" footer on an embed."""
    if random.random() < chance:
        tips = i18n.get_embed_tips(locale)
        embed.set_footer(text=random.choice(tips))
