import uuid
from datetime import datetime
from typing import Final, NewType

import attrs

from app.utils import utcnow

from supermechs.item import Item
from supermechs.mech import Mech

__all__ = ("BuildId", "MechBuild")

BuildId = NewType("BuildId", uuid.UUID)


def uuid4() -> BuildId:
    return BuildId(uuid.uuid4())


@attrs.define(kw_only=True)
class MechBuild:
    # read-only
    id: Final[BuildId] = attrs.field(factory=uuid4)
    mech: Final[Mech[Item]] = attrs.field(factory=Mech[Item])
    created_at: Final[datetime] = attrs.field(factory=utcnow)
    # mutable
    name: str = "Unnamed Mech"
    modified_at: datetime = attrs.field(factory=utcnow)

    def as_mech(self) -> tuple[str, Mech[Item]]:
        return (self.name, self.mech)
