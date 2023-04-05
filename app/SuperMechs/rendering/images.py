from __future__ import annotations

import logging
import typing as t
import weakref
from collections import defaultdict
from functools import partial

from attrs import define, field
from typing_extensions import LiteralString, Self, TypeVar

from abstract.files import Resource
from typeshed import Coro, P, twotuple

from ..enums import Type
from ..typedefs import AnyRawAttachment, RawAttachment, RawAttachments, SpritePosition
from ..utils import MISSING

if t.TYPE_CHECKING:
    from PIL.Image import Image

    from ..item import Item


LOGGER = logging.getLogger(__name__)

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
AttachmentType = TypeVar(
    "AttachmentType", bound=AnyAttachment, default=AnyAttachment, infer_variance=True
)


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
        }:  # noqa: E999
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

    def adjust(self, image: HasWidthAndHeight, x: int, y: int) -> None:
        """Updates the canvas size in-place, if the new data extends beyond previous."""
        self.left = max(self.left, -x)
        self.above = max(self.above, -y)
        self.right = max(self.right, x + image.width)
        self.below = max(self.below, y + image.height)

    def final_size(self, base_image: HasWidthAndHeight) -> tuple[int, int]:
        """Return the final size of the canvas, given base image."""
        return (
            self.left + max(base_image.width, self.right),
            self.above + max(base_image.height, self.below),
        )


def create_synthetic_attachment(width: int, height: int, type: Type) -> AnyAttachment:
    """Create an attachment off given image size. Likely won't work well for scope-like items.
    Note: taken directly from WU, credits to Raul."""

    if type is Type.TORSO:
        return Attachments(
            leg1=Attachment(round(width * 0.40), round(height * 0.9)),
            leg2=Attachment(round(width * 0.80), round(height * 0.9)),
            side1=Attachment(round(width * 0.25), round(height * 0.6)),
            side2=Attachment(round(width * 0.75), round(height * 0.6)),
            side3=Attachment(round(width * 0.20), round(height * 0.3)),
            side4=Attachment(round(width * 0.80), round(height * 0.3)),
            top1=Attachment(round(width * 0.25), round(height * 0.1)),
            top2=Attachment(round(width * 0.75), round(height * 0.1)),
        )

    if type is Type.LEGS:
        return Attachment(round(width * 0.5), round(height * 0.1))

    if type is Type.SIDE_WEAPON:
        return Attachment(round(width * 0.3), round(height * 0.5))

    if type is Type.TOP_WEAPON:
        return Attachment(round(width * 0.3), round(height * 0.8))

    return None


RI_T = t.TypeVar("RI_T", bound="AttachedImage[t.Any]")


def delegate(
    func: t.Callable[t.Concatenate[RI_T, P], None]
) -> t.Callable[t.Concatenate[RI_T, P], None]:
    """Mark the method as a delegated call."""

    def deco(self: RI_T, *args: P.args, **kwargs: P.kwargs) -> None:
        self._postprocess[id(self)].append(partial(func, self, *args, **kwargs))

    return deco


async def loader(renderer: AttachedImage[t.Any], resource: Resource) -> None:
    from PIL.Image import open

    with await resource.open() as file:
        image = open(file)
        image.load()
    renderer.image = image


Loader = t.Callable[[Resource], Coro[None]]


@define
class AttachedImage(t.Generic[AttachmentType]):
    image: Image = MISSING
    attachment: AttachmentType = field(default=None)

    _postprocess: t.ClassVar[dict[int, list[t.Callable[[], None]]]] = defaultdict(list)
    _item_refs: t.ClassVar = weakref.WeakValueDictionary[int, "Item"]()
    _loaders: t.ClassVar = weakref.WeakKeyDictionary[Self, t.Any]()

    @property
    def size(self) -> twotuple[int]:
        return self.image.size

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    @property
    def item(self) -> Item:
        """The Item this image belongs to. The item is weak referenced."""
        return self._item_refs[id(self)]

    @item.setter
    def item(self, item: Item) -> None:
        self._item_refs[id(self)] = item

    @property
    def loader(self) -> t.Any:
        return self._loaders.pop(self)

    def get_loader(self) -> Loader:
        return partial(loader, self)

    async def load(self) -> None:
        await self.loader
        self.image.load()

    def __hash__(self) -> int:
        return hash((type(self), id(self)))

    def paste_onto(self, image: Image, dest: twotuple[int]) -> None:
        """Paste this image onto another."""
        image.alpha_composite(self.image, dest)

    @delegate
    def crop(self, size: SpritePosition) -> None:
        """Queue the image to be cropped."""
        x, y, w, h = size["x"], size["y"], size["width"], size["height"]
        self.image = self.image.crop((x, y, x + w, y + h))
        LOGGER.debug(f"Image {self!r} cropped")

    @delegate
    def convert(self, mode: ImageMode) -> None:
        """Queue the image to convert its mode."""
        if self.image.mode != mode:
            self.image = self.image.convert(mode)

    @delegate
    def resize(self, width: int = 0, height: int = 0) -> None:
        """Queue the image to be resized."""
        if not width == height == 0:
            self.image = self.image.resize((width or self.image.width, height or self.image.height))
            LOGGER.debug(f"Image {self!r} resized")

    @delegate
    def assert_attachment(self) -> None:
        """Queue creating synthetic attachment in case one isn't set."""
        item = self._item_refs[id(self)]

        if self.attachment is None and item.type.attachable:
            self.attachment = t.cast(
                AttachmentType, create_synthetic_attachment(*self.image.size, item.type)
            )
            LOGGER.info(f"Created attachment for item {item!r}")

    @classmethod
    def from_resource(
        cls, resource: Resource, attachment: AttachmentType
    ) -> tuple[Self, Coro[None]]:
        """Create the image from Resource object."""
        self = cls(attachment=attachment)
        return self, loader(self, resource)

    @classmethod
    def new(
        cls, mode: ImageMode, size: twotuple[int], attachment: AttachmentType | None = None
    ) -> Self:
        """Create a blank image of given size."""
        from PIL.Image import new

        return cls(new(mode, size), attachment)

    @classmethod
    def _clear_cache(cls) -> None:
        cls._postprocess.clear()