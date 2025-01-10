import io
import pathlib
import random
from typing import TYPE_CHECKING

import disnake
from discord import sanitize_filename

from app import i18n
from resources import FileResource, HttpResource, Resource

if TYPE_CHECKING:
    from PIL import Image

__all__ = ("embed_image", "embed_resource", "sikrit_footer")

FORMAT = "png"


def embed_image(image: "Image.Image", filename: str) -> tuple[str, disnake.File]:
    """Create and return a File with an attachment url."""
    filename = sanitize_filename(filename)
    filename = str(pathlib.PurePath(filename).with_suffix("." + FORMAT))
    fp = io.BytesIO()
    image.save(fp, format=FORMAT)
    fp.seek(0)
    return f"attachment://{filename}", disnake.File(fp, filename)


def embed_resource(resource: Resource, filename: str) -> tuple[str, disnake.File]:
    match resource:
        case FileResource(path):
            filename = sanitize_filename(filename)
            url = f"attachment://{filename}"
            file = disnake.File(path, filename=filename)
            return url, file

        case HttpResource(url):
            return str(url), disnake.utils.MISSING

        case _:
            msg = "Unknown resource type"
            raise NotImplementedError(msg)


def sikrit_footer(embed: disnake.Embed, /, locale: disnake.Locale, chance: float = 0.01) -> None:
    """Randomly set a "tip" footer on an embed."""
    if random.random() < chance:
        tips = i18n.get_embed_tips(locale)
        embed.set_footer(text=random.choice(tips))
