from __future__ import annotations

import typing as t
from io import BytesIO
from pathlib import Path

from attrs import define, field, validators
from typing_extensions import Self

from .enums import Type
from .game_types import AnyAttachment, Attachment, Attachments, AttachmentType
from .pack_versioning import SpritePosition
from .utils import MISSING

if t.TYPE_CHECKING:
    from aiohttp import ClientSession
    from aiohttp.typedefs import StrOrURL
    from PIL.Image import Image

    from .mech import Mech


class HasImage(t.Protocol[AttachmentType]):
    attachment: AttachmentType

    @property
    def image(self) -> Image:
        ...


class HasWidthAndHeight(t.Protocol):
    @property
    def width(self) -> int:
        ...

    @property
    def height(self) -> int:
        ...


ImageIOLike = str | Path | BytesIO | tuple["Image", SpritePosition]


async def fetch_image_bytes(link: StrOrURL, session: ClientSession) -> BytesIO:
    async with session.get(link) as response:
        response.raise_for_status()
        return BytesIO(await response.content.read())


def convert_and_resize(
    image: Image, /, width: int = 0, height: int = 0, mode: str = "RGBA"
) -> Image:
    if image.mode != mode:
        image = image.convert(mode)

    # value == 0 preserves the dimension
    width = width or image.width
    height = height or image.height

    if width != image.width or height != image.height:
        image = image.resize((width, height))

    return image


@define
class AttachedImage(t.Generic[AttachmentType]):
    """Object proxying PIL.Image.Image with attachment point(s)"""

    # XXX: this class may be redundant if we place attachments on item itself and make
    # loading methods simple functions

    _image: Image = MISSING
    attachment: AttachmentType = field(default=None)

    @property
    def loaded(self) -> bool:
        """Whether image has been loaded."""
        return self._image is not MISSING

    @property
    def image(self) -> Image:
        if not self.loaded:
            raise RuntimeError("Image accessed before it was loaded")

        return self._image

    @image.setter
    def image(self, img: Image) -> None:
        self._image = img

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    def load_image(self, data: ImageIOLike, /, *, force: bool = False, resize_to: tuple[int, int] = (0, 0)) -> None:
        """Do what it takes to actually load the image
        `force`: if true and an image is cached, it will be overwritten."""
        if self.loaded and not force:
            return

        match data:
            case str() | Path() | BytesIO():
                from PIL.Image import open

                raw = open(data)

            case (image, {"x": x1, "y": y1, "width": w, "height": h}):
                raw = image.crop((x1, y1, x1 + w, y1 + h))

            case _:
                raise TypeError("Unrecognized file-like type")

        self.image = convert_and_resize(raw, *resize_to)


class ImageRenderer:
    """Class responsible for creating mech image."""

    def __init__(self, base: HasImage[Attachments], layers: t.Sequence[str]) -> None:
        self.base_image = base.image
        self.base_attachments = base.attachment
        # how many pixels the complete image extends beyond torso image boundaries
        self.pixels_left = 0
        self.pixels_right = 0
        self.pixels_above = 0
        self.pixels_below = 0

        self.layers = layers
        self.images: list[tuple[int, int, Image] | None] = [None] * len(layers)

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
        attachment = item.attachment

        if attachment is None:
            if x_pos is None or y_pos is None:
                raise TypeError("For item without attachment both x_pos and y_pos are needed")

            item_x = x_pos
            item_y = y_pos

        elif attachment.keys() != {"x", "y"}:
            raise TypeError(f"Invalid attachment for layer {layer!r}: {attachment}")

        else:
            item_x = attachment["x"]
            item_y = attachment["y"]

        if layer in self.base_attachments:
            offset = self.base_attachments[layer]
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
        self.pixels_right = max(self.pixels_right, x + image.width - self.base_image.width)
        self.pixels_below = max(self.pixels_below, y + image.height - self.base_image.height)

    def put_image(self, image: Image, layer: str, x: int, y: int) -> None:
        """Place the image on the canvas."""
        self.images[self.layers.index(layer)] = (x, y, image)

    def merge(self) -> Image:
        """Merges all images into one and returns it."""
        self.put_image(self.base_image, "torso", 0, 0)

        from PIL.Image import new

        canvas = new(
            "RGBA",
            (
                self.base_image.width + self.pixels_left + self.pixels_right,
                self.base_image.height + self.pixels_above + self.pixels_below,
            ),
            (0, 0, 0, 0),
        )

        for x, y, image in filter(None, self.images):
            canvas.alpha_composite(image, (x + self.pixels_left, y + self.pixels_above))

        return canvas

    @classmethod
    def from_mech(cls, mech: Mech) -> Self:
        if mech.torso is None:
            raise RuntimeError("Cannot create image without torso set")

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

        self = cls(mech.torso.image, LAYER_ORDER)

        if mech.legs is not None:
            self.add_image(mech.legs.image, "leg1")
            self.add_image(mech.legs.image, "leg2")

        for item, layer in mech.iter_items(weapons=True, slots=True):
            if item is None:
                continue

            self.add_image(item.image, layer)

        if mech.drone is not None:
            self.add_image(
                mech.drone.image,
                "drone",
                self.pixels_left + mech.drone.image.width // 2,
                self.pixels_above + mech.drone.image.height + 25,
            )

        return self


def create_synthetic_attachment(image: HasWidthAndHeight, type: Type) -> AnyAttachment:
    """Create an attachment off item image. Likely won't work well for scope-like items."""
    # Yoinked from WU, credits to Raul
    x = image.width
    y = image.height

    match type:
        case Type.TORSO:
            # fmt: off
            return {
                "leg1":  {"x": round(x * 0.40), "y": round(y * 0.9)},
                "leg2":  {"x": round(x * 0.80), "y": round(y * 0.9)},
                "side1": {"x": round(x * 0.25), "y": round(y * 0.6)},
                "side2": {"x": round(x * 0.75), "y": round(y * 0.6)},
                "side3": {"x": round(x * 0.20), "y": round(y * 0.3)},
                "side4": {"x": round(x * 0.80), "y": round(y * 0.3)},
                "top1":  {"x": round(x * 0.25), "y": round(y * 0.1)},
                "top2":  {"x": round(x * 0.75), "y": round(y * 0.1)},
            }
            # fmt: on

        case Type.LEGS:
            return {"x": round(x * 0.5), "y": round(y * 0.1)}

        case Type.SIDE_WEAPON:
            return {"x": round(x * 0.3), "y": round(y * 0.5)}

        case Type.TOP_WEAPON:
            return {"x": round(x * 0.3), "y": round(y * 0.8)}

        case _:
            return None
