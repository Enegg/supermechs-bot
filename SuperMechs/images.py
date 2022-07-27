from __future__ import annotations

import typing as t
from io import BytesIO

from .types import Attachment, Attachments, AttachmentType

if t.TYPE_CHECKING:
    from aiohttp import ClientSession
    from aiohttp.typedefs import StrOrURL
    from PIL.Image import Image


class HasImage(t.Protocol[AttachmentType]):
    attachment: AttachmentType

    @property
    def image(self) -> Image:
        ...


async def get_image(link: StrOrURL, session: ClientSession) -> Image:
    from PIL.Image import open

    async with session.get(link) as response:
        response.raise_for_status()
        return open(BytesIO(await response.content.read()))


class MechRenderer:
    """Class responsible for creating mech image."""

    LAYER_ORDER = (
        "drone",
        "side2",
        "side4",
        "top2",
        "leg2",
        "torso",
        "leg1",
        "top1",
        "side1",
        "side3",
    )

    def __init__(self, torso: HasImage[Attachments]) -> None:
        self.torso_image = torso.image
        # how many pixels the complete image extends beyond torso image boundaries
        self.pixels_left = 0
        self.pixels_right = 0
        self.pixels_above = 0
        self.pixels_below = 0
        self.torso_attachments = torso.attachment

        self.images: list[tuple[int, int, Image] | None] = [None] * 10

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} "
            f"offsets={(self.pixels_left, self.pixels_right, self.pixels_above, self.pixels_below)}"
            f" images={self.images} at 0x{id(self):016X}>"
        )

    @t.overload
    def add_image(self, item: HasImage[None], layer: str, x_pos: int, y_pos: int) -> None:
        ...

    @t.overload
    def add_image(
        self, item: HasImage[Attachment], layer: str, x_pos: int = ..., y_pos: int = ...
    ) -> None:
        ...

    def add_image(
        self,
        item: HasImage[Attachment] | HasImage[None],
        layer: str,
        x_pos: int | None = None,
        y_pos: int | None = None,
    ) -> None:
        """Adds the image of the item to the canvas."""
        if item.attachment is None:
            if x_pos is None or y_pos is None:
                raise TypeError("For item without attachment both x_pos and y_pos are needed")

            item_x = x_pos
            item_y = y_pos

        else:
            item_x = item.attachment["x"]
            item_y = item.attachment["y"]

        if layer in self.torso_attachments:
            offset = self.torso_attachments[layer]
            x = offset["x"] - item_x
            y = offset["y"] - item_y

        else:
            x, y = -item_x, -item_y

        self.adjust_offsets(item.image, x, y)
        self.put_image(item.image, layer, x, y)

    def adjust_offsets(self, image: Image, x: int, y: int) -> None:
        """Resizes the canvas if the image does not fit."""
        self.pixels_left = max(self.pixels_left, -x)
        self.pixels_above = max(self.pixels_above, -y)
        self.pixels_right = max(self.pixels_right, x + image.width - self.torso_image.width)
        self.pixels_below = max(self.pixels_below, y + image.height - self.torso_image.height)

    def put_image(self, image: Image, layer: str, x: int, y: int) -> None:
        """Place the image on the canvas."""
        self.images[self.LAYER_ORDER.index(layer)] = (x, y, image)

    def finalize(self) -> Image:
        """Merges all images into one and returns it."""
        self.put_image(self.torso_image, "torso", 0, 0)

        from PIL.Image import new

        canvas = new(
            "RGBA",
            (
                self.torso_image.width + self.pixels_left + self.pixels_right,
                self.torso_image.height + self.pixels_above + self.pixels_below,
            ),
            (0, 0, 0, 0),
        )

        for x, y, image in filter(None, self.images):
            canvas.alpha_composite(image, (x + self.pixels_left, y + self.pixels_above))

        return canvas
