from datetime import datetime
from typing import Final

import attrs
from monads.option import Null, Option

from app import snowflake
from app.utils import utcnow

from .ids import BuildId
from .item import Item

import dupermechs.all as sm

__all__ = ("MechBuild",)


@attrs.define(kw_only=True)
class MechBuild:
    # read-only
    mech: sm.Mech[Item]
    id: Final[BuildId] = attrs.field(factory=snowflake.new[BuildId])
    created_at: Final[datetime] = attrs.field(factory=utcnow)
    # mutable
    name: Option[str] = Null.null
    modified_at: datetime = attrs.Factory(lambda self: self.created_at, True)

    def as_mech(self) -> tuple[Option[str], sm.Mech[Item]]:
        return (self.name, self.mech)
