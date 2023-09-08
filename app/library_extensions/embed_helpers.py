import random
import typing as t

from disnake import Embed, File

from files import Bytes

if t.TYPE_CHECKING:
    from PIL.Image import Image

__all__ = ("embed_image", "debug_footer", "sikrit_footer")


def debug_footer(embed: Embed) -> None:
    """Utility/debug function useful for introspecting embed's content."""

    parts: list[str] = ["Debug:", f"Size: {len(embed)}"]

    if url := embed.image.url:
        parts.append(f"Image: {url}")

    if url := embed.thumbnail.url:
        parts.append(f"Thumb: {url}")

    embed.set_footer(text="\n".join(parts))


def embed_image(image: "Image", filename: str) -> tuple[str, File]:
    """Creates a File and returns it with an attachment url."""
    resource = Bytes.from_image(image, filename)
    return str(resource.url), File(resource.fp, filename)


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
