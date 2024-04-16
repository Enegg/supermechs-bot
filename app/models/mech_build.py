import uuid
from datetime import datetime
from typing import Final

from attrs import define, field

from supermechs.mech import Mech

__all__ = ("MechBuild",)


@define
class MechBuild:
    mech: Final[Mech] = field(factory=Mech)
    name: str = field(default="Unnamed Mech")
    created: Final[datetime] = field(factory=datetime.now)
    id: Final[uuid.UUID] = field(factory=uuid.uuid4)

    def as_mech(self) -> tuple[str, Mech]:
        return (self.name, self.mech)
