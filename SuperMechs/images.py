from __future__ import annotations

import typing as t
from collections import defaultdict
from functools import partial

from attrs import define, field
from typing_extensions import LiteralString, Self

from abstract.files import Resource

from .enums import Type
from .typedefs.game_types import AnyRawAttachment, RawAttachment, RawAttachments
from .typedefs.pack_versioning import SpritePosition
from .typeshed import P, twotuple
from .utils import MISSING

if t.TYPE_CHECKING:
    from PIL.Image import Image

    from .mech import Mech


ImageMode = (
    t.Literal["1", "L", "P", "RGB", "RGBA", "CMYK", "YCbCr", "LAB", "HSV", "I", "F"] | LiteralString
)


class Attachment(t.NamedTuple):
    x: int
    y: int

    @classmethod
    def from_dict(cls, mapping: RawAttachment) -> Self:
        return cls(mapping["x"], mapping["y"])


def raw_attachments_to_tupled(mapping: RawAttachments) -> Attachments:
    return {key: Attachment.from_dict(mapping) for key, mapping in mapping.items()}


Attachments = dict[str, Attachment]
AnyAttachment = Attachment | Attachments | None
AttachmentType = t.TypeVar("AttachmentType", bound=AnyAttachment)


def parse_raw_attachment(raw_attachment: AnyRawAttachment) -> AnyAttachment:
    match raw_attachment:
        case {
            "leg1": {},
            "leg2": {},
            "side1": {},
            "side2": {},
            "side3": {},
            "side4": {},
            "top1": {},
            "top2": {},
        }:
            return raw_attachments_to_tupled(raw_attachment)

        case {"x": int(), "y": int()}:
            return Attachment.from_dict(raw_attachment)

        case None:
            return None

        case _:
            TypeError(f"Invalid attachment type: {raw_attachment!r}")


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


@define
class Offsets:
    """Dataclass describing how many pixels the complete image extends beyond canvas."""

    left: int = 0
    right: int = 0
    above: int = 0
    below: int = 0


@define
class ImageRenderer:
    """Class responsible for creating mech image."""

    base: HasImage[Attachments]
    layers: t.Sequence[str]
    offsets: Offsets = field(factory=Offsets)
    images: list[tuple[int, int, Image] | None] = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.images = [None] * len(self.layers)

    @t.overload
    def add_image(self, item: HasImage[None], layer: str, attach_at: tuple[int, int]) -> None:
        ...

    @t.overload
    def add_image(
        self, item: HasImage[Attachment], layer: str, attach_at: tuple[int, int] = ...
    ) -> None:
        ...

    def add_image(
        self,
        item: HasImage[Attachment] | HasImage[None],
        layer: str,
        attach_at: tuple[int, int] | None = None,
    ) -> None:
        """Adds the image of the item to the canvas."""
        attachment = item.attachment or attach_at

        if attachment is None:
            raise TypeError("Item without attachment needs the attachment parameter provided")

        elif len(attachment) != 2:
            raise TypeError(f"Invalid attachment for layer {layer!r}: {attachment!r}")

        else:
            item_x, item_y = attachment

        if layer in self.base.attachment:
            offset = self.base.attachment[layer]
            x = offset.x - item_x
            y = offset.y - item_y

        else:
            x, y = -item_x, -item_y

        self.adjust_offsets(item.image, x, y)
        self.put_image(item.image, layer, x, y)

    def adjust_offsets(self, image: HasWidthAndHeight, x: int, y: int) -> None:
        """Resizes the canvas if the image does not fit."""
        offsets = self.offsets
        offsets.left = max(offsets.left, -x)
        offsets.above = max(offsets.above, -y)
        offsets.right = max(offsets.right, x + image.width - self.base.image.width)
        offsets.below = max(offsets.below, y + image.height - self.base.image.height)

    def put_image(self, image: Image, layer: str, x: int, y: int) -> None:
        """Place the image on the canvas."""
        self.images[self.layers.index(layer)] = (x, y, image)

    def merge(self) -> Image:
        """Merges all images into one and returns it."""
        self.put_image(self.base.image, "torso", 0, 0)

        from PIL.Image import new

        canvas = new(
            "RGBA",
            (
                self.base.image.width + self.offsets.left + self.offsets.right,
                self.base.image.height + self.offsets.above + self.offsets.below,
            ),
            (0, 0, 0, 0),
        )

        for x, y, image in filter(None, self.images):
            canvas.alpha_composite(image, (x + self.offsets.left, y + self.offsets.above))

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
                (
                    self.offsets.left + mech.drone.image.width // 2,
                    self.offsets.above + mech.drone.image.height + 25,
                ),
            )

        return self


def create_synthetic_attachment(width: int, height: int, type: Type) -> AnyAttachment:
    """Create an attachment off given image size. Likely won't work well for scope-like items.
    Note: taken directly from WU, credits to Raul."""

    if type is Type.TORSO:
        return Attachments(
            leg1=Attachment(round(width * 0.40), round(width * 0.9)),
            leg2=Attachment(round(width * 0.80), round(width * 0.9)),
            side1=Attachment(round(width * 0.25), round(width * 0.6)),
            side2=Attachment(round(width * 0.75), round(width * 0.6)),
            side3=Attachment(round(width * 0.20), round(width * 0.3)),
            side4=Attachment(round(width * 0.80), round(width * 0.3)),
            top1=Attachment(round(width * 0.25), round(width * 0.1)),
            top2=Attachment(round(width * 0.75), round(width * 0.1)),
        )

    if type is Type.LEGS:
        return Attachment(round(width * 0.5), round(height * 0.1))

    if type is Type.SIDE_WEAPON:
        return Attachment(round(width * 0.3), round(height * 0.5))

    if type is Type.TOP_WEAPON:
        return Attachment(round(width * 0.3), round(height * 0.8))

    return None


# Image if t.TYPE_CHECKING else object
#    def __getattr__(self, name: str) -> t.NoReturn:
#        return getattr(self._underlying, name)  # type: ignore


RI_T = t.TypeVar("RI_T", bound="AttachedImage[t.Any]")


def delegate(
    func: t.Callable[t.Concatenate[RI_T, P], None]
) -> t.Callable[t.Concatenate[RI_T, P], None]:
    """Mark the method as a delegated call."""

    def deco(self: RI_T, *args: P.args, **kwargs: P.kwargs) -> None:
        self._postprocess[id(self)].append(partial(func, *args, **kwargs))

    return deco


@define
class AttachedImage(t.Generic[AttachmentType]):
    image: Image = MISSING
    attachment: AttachmentType = field(default=None)

    _resource_cache: t.ClassVar[dict[Resource[t.Any], Image]] = {}
    _postprocess: t.ClassVar[dict[int, list[t.Callable[[], None]]]] = defaultdict(list)

    @property
    def size(self) -> twotuple[int]:
        return self.image.size

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    @delegate
    def crop(self, size: SpritePosition) -> None:
        """Queue the image to be cropped."""
        x, y, w, h = size["x"], size["y"], size["width"], size["height"]
        self.image = self.image.crop((x, y, x + w, y + h))

    @delegate
    def convert(self, mode: ImageMode) -> None:
        """Queue the image to convert its mode."""
        self.image = self.image.convert(mode)

    @delegate
    def resize(self, width: int = 0, height: int = 0) -> None:
        """Queue the image to be resized."""
        self.image = self.image.resize((width or self.image.width, height or self.image.height))

    @delegate
    def assert_attachment(self, type: Type) -> None:
        """Queue creating synthetic attachment in case one isn't set."""
        if self.attachment is None and type.attachable:
            self.attachment = t.cast(
                AttachmentType, create_synthetic_attachment(*self.image.size, type)
            )

    async def with_resource(self, resource: Resource[t.Any], is_partial: bool = False) -> None:
        """Load the image from Resource object."""
        if resource in self._resource_cache:
            image = self._resource_cache[resource]

        else:
            from PIL.Image import open

            with await resource.open() as file:
                image = open(file)
                image.load()

            if is_partial:
                self._resource_cache[resource] = image

        self.image = image

    @classmethod
    def new(
        cls, mode: ImageMode, size: twotuple[int], attachment: AttachmentType | None = None
    ) -> Self:
        """Create a blank image of given size."""
        from PIL.Image import new

        return cls(new(mode, size), attachment)

    @classmethod
    def clear_cache(cls) -> None:
        cls._resource_cache.clear()
        cls._postprocess.clear()
