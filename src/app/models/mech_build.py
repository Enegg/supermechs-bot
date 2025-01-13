import uuid
from collections import abc
from datetime import datetime
from typing import Final, NewType

import attrs
from monads.option import Null, Option

from app.utils import utcnow

from .item_pack import ItemPack

from supermechs.abc import ItemID, MechSlot
from supermechs.item import Item
from supermechs.mech import Mech

__all__ = ("BuildId", "MechBuild")

BuildId = NewType("BuildId", uuid.UUID)


@attrs.define(kw_only=True, frozen=True)
class PartialMechBuild:
    id: BuildId
    mech: abc.Mapping[MechSlot, ItemID]
    created_at: datetime
    name: Option[str]
    modified_at: datetime

    def as_complete(self, pack: ItemPack, /) -> "MechBuild":
        setup = {slot: Item.maxed(pack.get_item(id)) for slot, id in self.mech.items()}
        return MechBuild(
            id=self.id,
            mech=Mech(setup),
            created_at=self.created_at,
            name=self.name,
            modified_at=self.modified_at,
        )


@attrs.define(kw_only=True)
class MechBuild:
    # read-only
    id: Final[BuildId] = attrs.field(factory=lambda: BuildId(uuid.uuid4()))
    mech: Final[Mech[Item]]
    created_at: Final[datetime] = attrs.field(factory=utcnow)
    # mutable
    name: Option[str] = Null.null
    modified_at: datetime = attrs.Factory(lambda self: self.created_at, True)

    def as_mech(self) -> tuple[Option[str], Mech[Item]]:
        return (self.name, self.mech)

    def as_partial(self) -> PartialMechBuild:
        return PartialMechBuild(
            id=self.id,
            mech={slot: item.id for slot, item in self.mech.setup.items()},
            created_at=self.created_at,
            name=self.name,
            modified_at=self.modified_at,
        )
