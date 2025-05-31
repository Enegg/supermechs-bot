import io
import pathlib
import random
from typing import TYPE_CHECKING

import disnake
from discord import sanitize_filename

from app import i18n
from resources import FileResource

if TYPE_CHECKING:
    from PIL import Image

__all__ = ("embed_image", "sikrit_footer")

FORMAT = "png"


def embed_image(image: "Image.Image", filename: str) -> tuple[str, disnake.File]:
    """Create and return an image File with an attachment url."""
    filename = sanitize_filename(filename)
    filename = str(pathlib.PurePath(filename).with_suffix("." + FORMAT))
    fp = io.BytesIO()
    image.save(fp, format=FORMAT)
    fp.seek(0)
    return f"attachment://{filename}", disnake.File(fp, filename)


def embed_file_resource(resource: FileResource, /) -> tuple[str, disnake.File]:
    """Create and return a resource File with an attachment url."""
    filename = sanitize_filename(resource.path.name)
    return f"attachment://{filename}", disnake.File(resource.path, filename=filename)


def sikrit_footer(embed: disnake.Embed, /, locale: disnake.Locale) -> None:
    """Randomly set a "tip" footer on an embed."""
    tips = i18n.get_embed_tips(locale)
    embed.set_footer(text=random.choice(tips))
