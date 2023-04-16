import typing as t

from disnake import Embed, File

from files import Bytes

if t.TYPE_CHECKING:
    from PIL.Image import Image

__all__ = ("embed_image", "embed_to_footer")


def embed_to_footer(embed: Embed) -> None:
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
