from __future__ import annotations

import typing as t
from dataclasses import KW_ONLY, InitVar, dataclass, field

from typing_extensions import Self

from utils import MISSING, js_format

from .core import ArenaBuffs
from .enums import Element, Rarity, RarityRange, Type
from .game_types import (AnyStats, Attachment, Attachments, AttachmentType, ItemDict, ItemPackv2,
                         ItemSerialized, PackConfig, TagsDict)
from .images import get_image

if t.TYPE_CHECKING:
    from aiohttp import ClientSession
    from PIL.Image import Image


@dataclass(slots=True)
class Tags:
    premium: bool = False
    sword: bool = False
    melee: bool = False
    roller: bool = False
    legacy: bool = False
    require_jump: bool = False
    custom: bool = False

    def to_dict(self) -> TagsDict:
        return TagsDict(
            premium=self.premium,
            sword=self.sword,
            melee=self.melee,
            roller=self.roller,
            legacy=self.legacy,
            require_jump=self.require_jump,
            custom=self.custom,
        )


@dataclass(slots=True)
class Item(t.Generic[AttachmentType]):
    """Represents a single item."""

    _: KW_ONLY
    id: int
    name: str
    type: Type
    rarity: RarityRange
    pack_key: str = field(compare=False)
    element: Element = Element.OMNI
    stats: AnyStats = field(hash=False)
    image_url: str = field(default=MISSING, hash=False)
    attachment: AttachmentType = field(default=t.cast(AttachmentType, None), hash=False)

    width: InitVar[int] = 0
    height: InitVar[int] = 0
    tags: Tags = field(default_factory=Tags, hash=False)
    _image: Image | None = field(default=None, init=False, repr=False, hash=False)
    _image_resize: tuple[int, int] = field(init=False, repr=False, hash=False)

    def __post_init__(self, width: int, height: int) -> None:
        self._image_resize = (width, height)
        self.tags.premium = self.rarity.min > Rarity.EPIC
        self.tags.require_jump = "advance" in self.stats or "retreat" in self.stats

    def __str__(self) -> str:
        return self.name

    @property
    def displayable(self) -> bool:
        """Returns True if the item can be rendered on the mech, False otherwise"""
        return self.type not in {Type.TELE, Type.CHARGE, Type.HOOK, Type.MODULE}

    @property
    def image(self) -> Image:
        """Returns the `PIL.Image.Image` object for this item.
        Before this property is ever retrieved, `load_image` must be called."""
        if self._image is None:
            raise RuntimeError("load_image was never called")

        return self._image

    @property
    def has_image(self) -> bool:
        """Whether item has image cached."""
        return self._image is not None

    async def load_image(self, session: ClientSession, /, *, force: bool = False) -> None:
        """Loads the image from web

        Parameters
        -----------
        session:
            the session to perform the image request with.
        force:
            if true and item has an image cached, it will be overwritten."""
        if self.has_image and not force:
            return

        raw = await get_image(self.image_url, session)

        new_width, new_height = self._image_resize

        if new_width or new_height:
            width = new_width or raw.width
            height = new_height or raw.height

            self._image = raw.convert("RGBA").resize((width, height))

        else:
            self._image = raw.convert("RGBA")

    @classmethod
    def from_json_v1(cls, json: ItemDict, pack: PackConfig) -> Self:
        self = cls(
            id=json["id"],
            name=json["name"],
            pack_key=pack["key"],
            image_url=js_format(json.pop("image"), url=pack["base_url"]),
            type=Type[json["type"].upper()],
            rarity=RarityRange.from_string(json["transform_range"]),
            stats=json["stats"],
            element=Element[json["element"].upper()],
            attachment=json.get("attachment", None),  # type: ignore
        )
        tags = json.get("tags", [])
        self.tags.melee = "melee" in tags
        return self

    @classmethod
    def from_json_v2(cls, json: ItemDict, pack: ItemPackv2) -> Self:
        self = cls(
            id=json["id"],
            name=json["name"],
            pack_key=pack["key"],
            type=Type[json["type"].upper()],
            rarity=RarityRange.from_string(json["transform_range"]),
            stats=json["stats"],
            element=Element[json["element"].upper()],
            attachment=json.get("attachment", None),  # type: ignore
        )
        tags = json.get("tags", [])
        self.tags.melee = "melee" in tags
        self.tags.roller = "roller" in tags
        self.tags.sword = "sword" in tags
        return self

    def wu_serialize(self, slot_name: str) -> ItemSerialized:
        return {
            "slotName": slot_name,
            "id": self.id,
            "name": self.name,
            "type": self.type.name,
            "stats": ArenaBuffs.maxed().buff_stats(self.stats),
            "tags": self.tags.to_dict(),
            "element": self.element.name,
            "timesUsed": 0,
        }


AnyItem = Item[Attachment] | Item[Attachments] | Item[None]
