import uuid
from datetime import datetime
from typing import Final

from attrs import define, field
from disnake.utils import utcnow

from supermechs.mech import Mech

__all__ = ("MechBuild",)


@define
class MechBuild:
    mech: Final[Mech] = field(factory=Mech)
    name: str = field(default="Unnamed Mech")
    created_at: Final[datetime] = field(factory=utcnow)
    modified_at: datetime = field(factory=utcnow)
    id: Final[uuid.UUID] = field(factory=uuid.uuid4)

    def as_mech(self) -> tuple[str, Mech]:
        return (self.name, self.mech)
