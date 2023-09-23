import io
import pathlib
import random
import typing as t

from disnake import Colour, Embed, File

from .text_utils import sanitize_filename

if t.TYPE_CHECKING:
    from PIL.Image import Image

__all__ = ("ColorType", "debug_footer", "embed_image", "sikrit_footer")

ColorType = Colour | int


def debug_footer(embed: Embed) -> None:
    """Utility/debug function useful for introspecting embed's content."""

    parts: list[str] = ["Debug:", f"Size: {len(embed)}"]

    if (url := embed.image.url) and url.startswith("attachment://"):
        parts.append(f"Image: {url}")

    if (url := embed.thumbnail.url) and url.startswith("attachment://"):
        parts.append(f"Thumb: {url}")

    embed.set_footer(text="\n".join(parts))


def embed_image(image: "Image", filename: str, format: str = "png") -> tuple[str, File]:
    """Creates a File and returns it with an attachment url."""

    filename = sanitize_filename(filename)
    filename = str(pathlib.PurePath(filename).with_suffix(f".{format}"))
    fp = io.BytesIO()
    try:
        image.save(fp, format=format)

    except KeyError:
        # PIL does not cleanly handle invalid formats and instead it just causes
        # a vague mapping lookup error when not found
        raise ValueError(f"Invalid file format: {format!r}") from None

    fp.seek(0)
    return f"attachment://{filename}", File(fp, filename)


footers = [
    "What are you cooking?",
    "Tip: this is like a chicken flying out of a grenade launcher",
    "Tip: <insert generic newbie tip here>",
    '"💀"',
    "BattleMechs reloaded when",
    "We do a little smurfing",
    "To the surprise of literally no one",
    "Raul is KilliN confirmed",
    "Asther is baller",
    "is alex, no me",
    "If something appears broken, notify Marija immediately",
    "oh Marija",
]


def sikrit_footer(embed: Embed, /) -> None:
    """Has 1% chance to set a random footer on an embed."""
    if random.random() * 100 > 99:
        embed.set_footer(text=random.choice(footers))
